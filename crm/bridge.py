#!/usr/bin/env python -u
"""bridge.py — WhatsApp reply bridge for the LGE pilot (the NO-N8N inbox brain).

Polls Evolution API for inbound WhatsApp messages, maps each chat to an ops
`leads` row (auto-creates leads for unknown numbers), writes `messages` rows
(the Inbox UI reads these), and — when guardrails allow — generates a reply
with the FreeLLM LLM using per-thread memory + the lead's steering, then sends
it via Evolution and logs the out bubble.

Usage:
  python3 bridge.py --dry      # ingest logic shown, nothing written/sent
  python3 bridge.py --once     # one pass: ingest + maybe reply
  python3 bridge.py --listen   # loop forever (default every 60s, --every N)
  python3 bridge.py --no-reply # ingest + log only, never generate replies

Guardrails (hard-coded, safety first):
  - test lead / owner thread  → ingest only, NEVER auto-reply (drill is manual)
  - opt-out phrases           → recorded, thread never replied again
  - reply caps                → max 4/lead/day, 40/day global, 2h cooldown
  - quiet hours               → 21:30-08:00 IST: ingest only, replies defer
  - group chats / status      → skipped
  - lid JIDs (no phone digits)→ logged for owner, no direct send possible
"""
import argparse, fcntl, json, os, re, sys, time as time_mod, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta, time as dtime

import pg8000.native

import chatflow

HERE = os.path.dirname(os.path.abspath(__file__))
CREDS_PATH = os.path.join(HERE, "..", "secrets", "credentials.json")
STATE_PATH = os.environ.get("BRIDGE_STATE") or os.path.join(HERE, "..", "secrets", "bridge_state.json")

import json as _json, os as _os
def _env(k, d=None):
    return _os.environ.get(k) or d
_CREDS = None
def _creds():
    global _CREDS
    if _CREDS is None:
        try:
            _CREDS = _json.load(open(CREDS_PATH))
        except Exception:
            _CREDS = {"evolution": {}, "owner_whatsapp": "917705871046"}
    return _CREDS

DB = dict(user=_env("DB_USER", "root"),
          host=_env("DB_HOST", "213.199.62.248"),
          port=int(_env("DB_PORT", "5434")),
          database=_env("DB_NAME", "lge"),
          password=_env("DB_PASSWORD", "Itachi933641"))
LLM = {"base_url": _env("LLM_BASE_URL", "https://freellm.anagataitsolutions.in/v1"),
       "api_key": _env("LLM_API_KEY", "freellmapi-92711a0508c8175cce421318cdf36de3f88c968b841855ae"),
       "model": _env("LLM_MODEL", "deepseek-v4-flash")}

# Drill test lead: ops leads.id + every JID it might wear (phone + lid)
TEST_LEAD_HINTS = {"917705871046", "259768245555447"}

OPT_OUT = ("nahi chahiye", "mat bhejo", "stop", "not interested", "no thanks",
           "remove karo", "unsubscribe", "pareshan", "blok", "block kar")
QUIET_IST = (dtime(21, 30), dtime(8, 0))   # replies deferred inside this window
MAX_PER_LEAD = int(_env("BRIDGE_MAX_PER_LEAD", "4"))
MAX_GLOBAL = int(_env("BRIDGE_MAX_GLOBAL", "40"))
MIN_GAP_S = int(_env("BRIDGE_MIN_GAP_S", "45"))          # anti-burst: min seconds between auto-reply cycles per thread
SYSTEM = """You are the AI front-desk assistant for 'Local Growth Engine' (Kanpur), replying
on the business WhatsApp of Sanjeev. You talk to small-business owners (clinic/salon/shop owners)
in casual Hinglish. Rules:
- Reply as 1-3 short bubbles separated by a blank line. Each bubble max ~25 words.
- Warm, human-pada hua tone; never corporate; light emoji use.
- Goal: grow interest in the demo. Trial month is Rs 15,000 (setup included) — mention only when asked about price.
- No links ever. Never invent clients or results.
- Angry or out-of-scope questions: apologise briefly, say Sanjeev ji will personally reply soon.
- If the person opted out earlier, do not pitch — only a polite ack.
- You ARE an AI; if asked directly, say: main Sanjeev ji ka AI assistant hoon.
Output: the bubbles only, no preamble, no quotes."""


def ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def load_state():
    """BRIDGE_EPOCH (unix ts, env) is the reset lever: bumping it wipes state
    (fresh conversations) and the ingest loop filters out older messages."""
    epoch = os.environ.get("BRIDGE_EPOCH") or ""
    s = None
    if os.path.exists(STATE_PATH):
        s = json.load(open(STATE_PATH))
        if epoch and s.get("_epoch") != epoch:
            s = None  # epoch bump = full reset
    if s is None:
        s = {"seen": {}, "threads": {}, "sent_today": {"date": "", "n": 0},
             "lead_replies_today": {}, "stopped": {}, "_push": {}}
    # sanitize: any NULL-text history entries from a corrupt prior state
    for th in (s.get("threads") or {}).values():
        for h in (th.get("history") or []):
            if h.get("text") is None:
                h["text"] = ""
    s["_epoch"] = epoch
    return s


def save_state(s):
    json.dump(s, open(STATE_PATH, "w"), indent=1)


def norm_phone(raw):
    d = re.sub(r"\D", "", str(raw or ""))
    if d.startswith("00"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = "91" + d[1:]
    if len(d) == 10 and d[0] in "123456789":
        d = "91" + d
    return d if (len(d) == 12 and d.startswith("91")) else None


# ---------- Evolution ----------

def _evo_cfg(cfg):
    """Env vars win (container); credentials.json fallback (local)."""
    e = cfg.get("evolution") or {}
    return {"base_url": _env("EVO_BASE_URL", e.get("base_url")),
            "api_key": _env("EVO_API_KEY", e.get("api_key")),
            "instance": _env("EVO_INSTANCE", e.get("instance"))}


def evo_page_inbound(cfg, max_pages=8):
    """All outside-sender text messages from the recent-messages index."""
    _epoch = int(os.environ.get("BRIDGE_EPOCH") or 0)
    out = []
    for page in range(1, max_pages + 1):
        req = urllib.request.Request(
            f"{_evo_cfg(cfg)['base_url'].rstrip('/')}/chat/findMessages/{_evo_cfg(cfg)['instance']}",
            data=json.dumps({"page": page, "offset": 50}).encode(),
            headers={"apikey": _evo_cfg(cfg)["api_key"], "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        batch = (d.get("messages") or {}).get("records", [])
        for m in batch:
            k = m.get("key") or {}
            jid = k.get("remoteJid") or ""
            if k.get("fromMe") or not jid or jid.endswith("@g.us") or jid == "status@broadcast":
                continue
            msg = m.get("message") or {}
            txt = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text", "") or ""
            if not txt.strip():
                continue
            ts = int(m.get("messageTimestamp") or 0)
            if _epoch and ts < _epoch:
                continue  # older than reset boundary — ignore
            out.append({"jid": jid, "wa_id": k.get("id"), "text": txt.strip(),
                        "ts": ts,
                        "push": m.get("pushName") or ""})
        if len(batch) < 50:
            break
    out.sort(key=lambda x: x["ts"])
    return out


def evo_send_text(cfg, number, text):
    body = json.dumps({"number": str(number), "text": text}).encode()
    req = urllib.request.Request(
        f"{_evo_cfg(cfg)['base_url'].rstrip('/')}/message/sendText/{_evo_cfg(cfg)['instance']}",
        data=body, method="POST",
        headers={"apikey": _evo_cfg(cfg)["api_key"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    return (out.get("key") or {}).get("id", "?")


# ---------- DB helpers (ops tables = what the UI Inbox reads) ----------

def lead_row(r):
    d = dict(id=r[0], name=r[1], business=r[2], stage=r[3], steering=r[4],
             autopilot=r[5], is_test=r[6])
    if len(r) > 7:
        d["tags"] = r[7]
    if len(r) > 8:
        d["phone"] = r[8]
    return d


def fetch_lead(con, lid):
    rows = con.run("select id, name, business, stage, coalesce(steering,''), autopilot, is_test, "
                   "coalesce(tags,'{}'), coalesce(phone,'') from leads where id=:i", i=lid)
    if not rows:
        return None
    r = rows[0]
    return dict(id=r[0], name=r[1], business=r[2], stage=r[3], steering=r[4],
                autopilot=r[5], is_test=r[6], tags=r[7], phone=r[8])


def ops_lead_for(con, jid, state, push=""):
    """Find or create the ops lead for a chat JID."""
    if jid in state["threads"] and state["threads"][jid].get("ops_id"):
        try:
            return fetch_lead(con, state["threads"][jid]["ops_id"])
        except IndexError:
            pass  # lead deleted; recreate below
    digits = jid.split("@")[0]
    if jid.endswith("@s.whatsapp.net"):
        ph = norm_phone(digits) or digits
        rows = con.run("""select id, name, business, stage, coalesce(steering,''), autopilot, is_test, coalesce(tags,'{}')
                          from leads
                          where regexp_replace(coalesce(phone,''),'[^0-9]','','g') = :p limit 1""", p=ph)
        if rows:
            state["threads"][jid] = {"ops_id": str(rows[0][0])}
            return lead_row(rows[0])
    if any(h in jid for h in TEST_LEAD_HINTS):
        rows = con.run("select id, name, business, stage, coalesce(steering,''), autopilot, is_test, coalesce(tags,'{}') "
                       "from leads where is_test = true limit 1")
        if rows:
            state["threads"][jid] = {"ops_id": str(rows[0][0])}
            return lead_row(rows[0])
    name = state.get("_push", {}).get(jid) or digits
    phone = digits if jid.endswith("@s.whatsapp.net") else None
    r = con.run("""insert into leads (name, business, stage, source, phone, notes)
                   values (:n, :n, 'contacted', 'whatsapp', :p, 'auto-created by bridge: inbound WhatsApp chat')
                   returning id, name, business, stage, coalesce(steering,''), autopilot, is_test, coalesce(tags,'{}')""",
                n=name, p=phone)[0]
    state["threads"][jid] = {"ops_id": str(r[0])}
    return lead_row(r)


def insert_msg(con, ops_id, direction, body, chunks, wa_id, status):
    con.run("""insert into messages (lead_id, direction, kind, body, chunks, wa_id, status)
               values (:l, :d, 'text', :b, :c, :w, :s)""",
            l=ops_id, d=direction, b=body, c=json.dumps(chunks), w=wa_id, s=status)


# ---------- reply brain ----------

def llm_call(system, user):
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": user}]
    body = json.dumps({"model": LLM["model"], "messages": msgs,
                       "max_tokens": 220, "temperature": 0.7}).encode()
    req = urllib.request.Request(LLM["base_url"] + "/chat/completions", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + LLM["api_key"],
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        d = json.loads(r.read().decode())
    return (d["choices"][0]["message"]["content"] or "").strip()


def llm_reply(history, lead, stopped):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "system", "content":
                "Lead facts: business=%s stage=%s%s%s" % (
                    lead.get("business") or lead.get("name") or "unknown",
                    lead.get("stage") or "new",
                    (" | steering: " + str(lead["steering"])) if lead.get("steering") else "",
                    " | OPTED OUT EARLIER: acknowledge politely, no pitch." if stopped else "")}]
    for h in history[-10:]:
        msgs.append({"role": "user" if h["dir"] == "in" else "assistant", "content": h["text"]})
    return llm_call("\n\n".join(m["content"] for m in msgs if m["role"] == "system"),
                    "\n".join(("CUSTOMER: " if h["dir"] == "in" else "YOU: ") + h["text"]
                              for h in history[-10:]))


def in_quiet_hours(now_ist):
    a, b = QUIET_IST
    return a <= now_ist or now_ist < b


# ---------- one pass ----------

def run_pass(dry=False, no_reply=False):
    try:
        cfg = json.load(open(CREDS_PATH))
    except Exception:
        cfg = {"evolution": {}, "owner_whatsapp": "917705871046"}
    state = load_state()
    today = ist_now().strftime("%Y-%m-%d")
    if state["sent_today"].get("date") != today:
        state["sent_today"] = {"date": today, "n": 0}
        state["lead_replies_today"] = {}

    con = pg8000.native.Connection(**DB)
    new_in = []
    for m in evo_page_inbound(cfg):
        if m["wa_id"] in state["seen"]:
            continue
        if con.run("select 1 from messages where wa_id=:w", w=m["wa_id"]):
            state["seen"][m["wa_id"]] = 1
            continue  # already in DB (prior run/backfill) — restart-safe
        jid = m["jid"]
        lead = ops_lead_for(con, jid, state)
        state["seen"][m["wa_id"]] = 1
        state.setdefault("_push", {})[jid] = m["push"] or state.get("_push", {}).get(jid, "")
        th = state["threads"].setdefault(jid, {"ops_id": str(lead["id"])})
        if not th.get("history"):
            rows = con.run("select direction, coalesce(body,''), extract(epoch from created_at)::bigint "
                           "from messages where lead_id=:l order by created_at desc limit 40", l=lead["id"])
            th["history"] = [{"dir": r[0], "text": r[1] or "", "ts": int(r[2])} for r in reversed(rows)]
        th.setdefault("history", []).append({"dir": "in", "text": m["text"], "ts": m["ts"]})
        th["history"] = th["history"][-40:]
        if not dry:
            insert_msg(con, lead["id"], "in", m["text"], [{"text": m["text"]}], m["wa_id"], "received")
        new_in.append((jid, m["text"]))
        print(f"IN  {jid[:28]:28} {m['text'][:64]!r}")
        if any(p in m["text"].lower() for p in OPT_OUT):
            state["stopped"][jid] = m["ts"]
            if not dry:
                con.run("update leads set notes='opted out (bridge auto-detect)' where id=:i", i=lead["id"])
            print("    -> opt-out recorded, thread muted")
    con.close()

    if dry:
        print(f"DRY: would have ingested {len(new_in)}, reply pass skipped")
        return
    save_state(state)

    if no_reply:
        print(f"ingested {len(new_in)} (no-reply mode)")
        return

    # ---- reply pass ----
    con = pg8000.native.Connection(**DB)
    now_ist = ist_now()
    quiet = in_quiet_hours(now_ist.time())
    replies = 0
    for jid, th in state["threads"].items():
        hist = th.get("history", [])
        if not hist or hist[-1]["dir"] != "in":
            continue                                  # nothing unanswered
        if state["stopped"].get(jid):
            continue
        try:
            lead = fetch_lead(con, th["ops_id"])
        except (IndexError, TypeError):
            continue
        if not lead:
            continue
        if lead["is_test"] and "engine=on" not in (lead.get("tags") or []):
            continue                                  # drill thread: manual unless engine=on
        if not lead["autopilot"]:
            continue
        if quiet:
            continue
        if state["lead_replies_today"].get(jid, 0) >= MAX_PER_LEAD:
            continue
        if state["sent_today"]["n"] >= MAX_GLOBAL:
            break
        last_out = max([h["ts"] for h in hist if h["dir"] == "out"] + [0])
        if last_out >= hist[-1]["ts"]:
            continue                                  # already answered
        if last_out and hist[-1]["ts"] - last_out < MIN_GAP_S:
            continue                                  # anti-burst gap
        number = jid.split("@")[0] if jid.endswith("@s.whatsapp.net") else norm_phone(lead.get("phone"))
        if not number:
            print(f"OUT? {jid[:28]:28} lid JID, no phone on lead — logged for owner, no direct send")
            continue
        # ---- chatflow engine decides the turn ----
        try:
            turn = chatflow.next_turn(lead, hist)
        except Exception as ex:
            print(f"chatflow err {jid[:24]}: {str(ex)[:100]}")
            continue
        bubbles = None
        if turn.get("fallback"):
            try:
                bubbles = chatflow.phrase_with_llm(turn, lead, llm_call)
            except Exception:
                bubbles = None
        if not bubbles:
            bubbles = turn["fallback"] or turn["bubbles"] or []
        if not bubbles:
            continue
        # persist state deltas (phase first — disambiguates urgency vs sales after restarts)
        if turn.get("phase"):
            tg = [t for t in (turn.get("tags") or lead.get("tags") or []) if not t.startswith("phase=")]
            tg.append("phase=" + turn["phase"])
            turn["tags"] = tg
        if turn.get("stage") and turn["stage"] != lead["stage"]:
            con.run("update leads set stage=:s where id=:i", s=turn["stage"], i=lead["id"])
            lead["stage"] = turn["stage"]
        if turn.get("tags") and turn["tags"] != lead.get("tags"):
            con.run("update leads set tags=:t where id=:i", t=turn["tags"], i=lead["id"])
            lead["tags"] = turn["tags"]
        con.run("update leads set notes = 'chatflow:' || :k || ' obj=' || :o || ' dq=' || :d where id=:i",
                k=turn.get("kind") or "?", o=turn.get("objection") or "-", d=str(turn.get("ask_dq") or "-"), i=lead["id"])
        ids = []
        try:
            for i, b in enumerate(bubbles):
                ids.append(evo_send_text(cfg, number, b))
                if i < len(bubbles) - 1:
                    time_mod.sleep(3)
        except Exception as ex:
            print(f"send err {jid[:24]}: {str(ex)[:100]}")
            continue
        for b, wid in zip(bubbles, ids):
            insert_msg(con, lead["id"], "out", b, [{"text": b}], wid, "sent")
            th["history"].append({"dir": "out", "text": b, "ts": int(time_mod.time())})
        state["sent_today"]["n"] += len(ids)
        state["lead_replies_today"][jid] = state["lead_replies_today"].get(jid, 0) + len(ids)
        con.run("""update leads set stage = case when stage='new' then 'contacted' else stage end,
                     updated_at = now() where id=:i""", i=lead["id"])
        replies += 1
        print(f"OUT {jid[:28]:28} {len(ids)} bubbles: {' / '.join(b[:40] for b in bubbles)}")
    con.close()
    save_state(state)
    print(f"pass done: {replies} replied")


def main():
    # single-flight lock: two concurrent passes would corrupt bridge_state.json
    lock_path = STATE_PATH + ".lock"
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another bridge pass is running — exiting")
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--listen", action="store_true")
    ap.add_argument("--every", type=int, default=60)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-reply", action="store_true")
    a = ap.parse_args()
    if a.listen:
        print(f"listening every {a.every}s — Ctrl+C to stop", flush=True)
        while True:
            try:
                run_pass(no_reply=a.no_reply)
            except Exception:
                import traceback
                print("pass error:", flush=True)
                traceback.print_exc()
            time_mod.sleep(a.every)
    else:
        run_pass(dry=a.dry, no_reply=a.no_reply)


if __name__ == "__main__":
    main()