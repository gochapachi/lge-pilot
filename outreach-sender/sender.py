#!/usr/bin/env python3
"""
WA Outreach Sender — Odoo leads -> WhatsApp via Evolution API.

  python3 sender.py --dry-run            # show EXACT messages for next N leads, send nothing
  python3 sender.py --test +919XXXXXXXXX # send one preview to your own number, no CRM writes
  python3 sender.py --limit 5            # LIVE: send to max 5 leads, log to Odoo chatter
  python3 sender.py --limit 40           # full daily batch

Safety rails: connection-state check, daily cap, random delays between sends,
dedupe via sent_state.csv (never sends twice), chatter note + tag on every lead sent.
"""
import argparse, csv, json, os, random, re, sys, time
import urllib.request, urllib.error
import xmlrpc.client
from datetime import datetime, date

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
STATE_PATH = os.path.join(BASE, "sent_state.csv")
LOG_PATH = os.path.join(BASE, "send_log.csv")


def cfg():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def check_placeholders(c):
    blob = json.dumps(c.get("evolution", {})) + json.dumps(c.get("odoo", {}))
    if "PASTE_" in blob:
        sys.exit("❌ config.json still has PASTE_ placeholders — fill every field first.")


def append_row(path, header, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def all_sent_keys(path):
    """{(model, lead_id)} ever sent — permanent dedupe."""
    if not os.path.exists(path):
        return set()
    with open(path, newline="") as f:
        return {(r["model"], r["lead_id"]) for r in csv.DictReader(f)}


def sent_today_count(path):
    if not os.path.exists(path):
        return 0
    today = date.today().isoformat()
    with open(path, newline="") as f:
        return sum(1 for r in csv.DictReader(f) if r.get("date") == today)


def norm_phone(raw):
    """-> 91XXXXXXXXXX or None. Indian-first heuristic."""
    if not raw:
        return None
    d = re.sub(r"\D", "", str(raw))
    if d.startswith("00"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = "91" + d[1:]
    if len(d) == 10 and d[0] in "123456789":
        d = "91" + d
    if len(d) == 13 and d.startswith("091"):
        d = d[3:]
    if len(d) == 12 and d.startswith("91") and d[2] != "0":
        return d
    return None


# ---------------- Evolution API ----------------

def evo_state(c):
    e = c["evolution"]
    url = f"{e['base_url'].rstrip('/')}/instance/connectionState/{e['instance']}"
    try:
        req = urllib.request.Request(url, headers={"apikey": e["api_key"]})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode() or "{}"
    except urllib.error.HTTPError as ex:
        return f"❓ HTTP {ex.code} (check base_url/apikey/instance)"
    return "open ✅" if '"open"' in body.lower() else body[:200]


def evo_send(c, number, text):
    e = c["evolution"]
    url = f"{e['base_url'].rstrip('/')}/message/sendText/{e['instance']}"
    h = {"Content-Type": "application/json", "apikey": e["api_key"]}
    for body in ({"number": number, "textMessage": {"text": text}},   # Evolution v2
                 {"number": number, "text": text}):                    # older builds
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers=h, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                return True, f"sent ({r.status})"
        except urllib.error.HTTPError as ex:
            try:
                detail = ex.read().decode()[:180]
            except Exception:
                detail = ""
            last = f"HTTP {ex.code} {detail}"
            if ex.code in (400, 404, 422):
                continue  # try legacy payload format
        except Exception as ex:
            last = str(ex)
    return False, last


# ---------------- Odoo ----------------

def odoo_connect(c):
    o = c["odoo"]
    url = o["url"].rstrip("/")
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(o["db"], o["email"], o["api_key"], {})
    if not uid:
        sys.exit("❌ Odoo auth failed — check url/db/email/api_key (API key: Settings ▸ Users ▸ API Keys)")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return (o["db"], uid, o["api_key"], models)


def kw(o, model, method, args, kwargs=None):
    db, uid, key, models = o
    return models.execute_kw(db, uid, key, model, method, args, kwargs or {})


def fetch_leads(o, c, limit):
    want = ["name", "contact_name", "partner_name", "phone", "mobile",
            "email_from", "description"]
    odcfg = c["odoo"]
    fields = want
    try:
        have = kw(o, odcfg["model"], "fields_get", [], {"attributes": []})
        picked = [f for f in want if f in have]
        if len(picked) >= 4:
            fields = picked
        if "x_wa_line1" in have:  # optional custom field for per-lead line 1
            fields.append("x_wa_line1")
    except Exception:
        pass
    return kw(o, odcfg["model"], "search_read", [odcfg.get("domain", [])],
              {"fields": fields, "limit": limit, "order": odcfg.get("order", "id desc")})


def mark_sent(o, c, rec_id, number):
    ts = datetime.now().strftime("%d-%b %H:%M")
    model = c["odoo"]["model"]
    try:
        kw(o, model, "message_post", [[rec_id]],
           {"body": f"📱 WA outreach sent {ts} → +{number} (auto)",
            "message_type": "comment", "subtype_xmlid": "mail.mt_note"})
    except Exception as e:
        print(f"  ⚠️ chatter note failed: {e}")
    try:
        tags = kw(o, "crm.tag", "search_read", [["name", "=", "WA-Outreach"]], {"fields": ["id"]})
        tid = tags[0]["id"] if tags else kw(o, "crm.tag", "create", [{"name": "WA-Outreach"}])
        kw(o, model, "write", [[rec_id], {"tag_ids": [(4, tid)]}])
    except Exception as e:
        print(f"  ⚠️ tag failed: {e}")


# ---------------- template ----------------

def render(c, rec):
    out = c["outreach"]
    biz = (rec.get("partner_name") or rec.get("name") or "aapke business").strip()
    person = (rec.get("contact_name") or "").strip()
    name = person.split()[0] if person else (biz.split()[0] if biz else "ji")
    num_raw = rec.get("mobile") or rec.get("phone")
    num = norm_phone(num_raw)
    line1 = ""
    overrides = out.get("line1_overrides") or {}
    for key in (num_raw, num, rec.get("email_from")):
        if key and str(key) in overrides:
            line1 = overrides[str(key)].strip()
            break
    if not line1 and rec.get("x_wa_line1"):
        line1 = str(rec["x_wa_line1"]).strip()
    if not line1:
        line1 = out.get("default_line1", "").strip()
    templates = out.get("message_templates") or [out["message_template"]]
    text = random.choice(templates).format(
        business=biz, name=name, line1=line1,
        demo_link=out.get("demo_link", ""), my_name=out.get("my_name", ""))
    return num, text


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="print messages, send nothing")
    p.add_argument("--limit", type=int, default=10, help="max leads this run")
    p.add_argument("--test", metavar="NUMBER", help="send 1 preview to your own number")
    a = p.parse_args()

    c = cfg()
    check_placeholders(c)
    outcfg = c["outreach"]

    # ---- test mode: no CRM touched
    if a.test:
        to = norm_phone(a.test) or sys.exit(f"❌ can't normalize {a.test} to E.164")
        print(f"Evolution state: {evo_state(c)}")
        num, text = render(c, {"partner_name": "Sharma Dental Care",
                               "contact_name": "Dr. Sharma", "name": "Demo lead"})
        ok, detail = evo_send(c, to, text)
        print(("✅ " if ok else "❌ ") + detail)
        print("--- message preview ---\n" + text)
        return

    o = odoo_connect(c)
    print(f"✅ Odoo connected as {c['odoo']['email']} ({c['odoo']['model']})")
    print(f"Evolution state: {evo_state(c)}")

    cap_left = outcfg.get("daily_cap", 40) - sent_today_count(STATE_PATH)
    eff = max(0, min(a.limit, cap_left))
    if eff == 0:
        sys.exit(f"🛑 Daily cap reached ({outcfg.get('daily_cap', 40)}) — nothing more today. Good discipline.")

    sent_keys = all_sent_keys(STATE_PATH)
    model_name = c["odoo"]["model"]
    recs = [r for r in fetch_leads(o, c, (eff + 20) * 3)
            if (model_name, str(r["id"])) not in sent_keys][:eff + 20]

    if a.dry_run:
        print(f"\n===== DRY RUN — next {eff} messages (nothing sent) =====")
        shown = 0
        for r in recs:
            num, text = render(c, r)
            label = (r.get("partner_name") or r.get("name") or r["id"])
            print(f"\n──── {label} | id={r['id']} | to={'+' + num if num else '❌ NO VALID NUMBER'}")
            print(text)
            shown += 1
            if shown >= eff:
                break
        print("\n===== end dry run. Happy? →  python3 sender.py --test <your number>")
        return

    print(f"\n🚀 LIVE: sending to up to {eff} leads, {outcfg.get('delay_min_s', 45)}–{outcfg.get('delay_max_s', 90)}s apart\n")
    ok_n = skip_n = err_n = 0
    consecutive_errors = 0
    for i, r in enumerate(recs[:eff]):
        num, text = render(c, r)
        label = (r.get("partner_name") or r.get("name") or r["id"])
        if not num:
            print(f"[{i+1}/{eff}] ⏭️  {label}: no valid number, skipped")
            append_row(LOG_PATH, ["ts", "mode", "lead_id", "number", "status", "detail"],
                       [datetime.now().isoformat(timespec="seconds"), "live", r["id"], "", "skipped", "bad number"])
            skip_n += 1
            continue
        ok, detail = evo_send(c, num, text)
        ts = datetime.now().isoformat(timespec="seconds")
        if ok:
            append_row(STATE_PATH, ["date", "ts", "model", "lead_id", "number"],
                       [date.today().isoformat(), ts, model_name, r["id"], num])
            append_row(LOG_PATH, ["ts", "mode", "lead_id", "number", "status", "detail"],
                       [ts, "live", r["id"], num, "sent", detail])
            mark_sent(o, c, r["id"], num)
            print(f"[{i+1}/{eff}] ✅ {label} → +{num}")
            ok_n += 1
            consecutive_errors = 0
        else:
            append_row(LOG_PATH, ["ts", "mode", "lead_id", "number", "status", "detail"],
                       [ts, "live", r["id"], num, "error", detail])
            print(f"[{i+1}/{eff}] ❌ {label}: {detail}")
            err_n += 1
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print("🛑 3 consecutive errors — aborting. Check Evolution instance connection.")
                break
        if i < eff - 1:
            time.sleep(random.uniform(outcfg.get("delay_min_s", 45), outcfg.get("delay_max_s", 90)))

    print(f"\nDone. sent={ok_n} skipped={skip_n} errors={err_n} | state: {STATE_PATH} | odoo: tagged+chattered")


if __name__ == "__main__":
    main()