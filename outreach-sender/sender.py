#!/usr/bin/env python3
"""
WA Outreach Sender v2 — OUR Postgres (crm_lead) -> WhatsApp via Evolution API.
Zero Odoo dependency.

  python3 sender.py                 # dry-run: shows exactly what would go out, sends nothing
  python3 sender.py --test          # send ONE preview to owner WhatsApp (917705871046), no CRM writes
  python3 sender.py --send --limit 5   # LIVE batch, capped
  python3 sender.py --send --limit 40  # full daily batch

Safety rails:
  - dry-run is the default; --send is explicit
  - daily cap (outreach.daily_cap, default 15) enforced from outreach_log
  - permanent dedupe: a lead with any D1 outreach_log row is never re-sent
  - random 45-90s delay between sends
  - steering-aware: crm_lead.steering is stored in the log meta for the AI layer
"""
import argparse, json, os, random, re, sys, time
import urllib.request, urllib.error
from datetime import date, datetime

import pg8000.native

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CONFIG_PATH = os.path.join(BASE, "config.json")
CREDS_PATH = os.path.join(ROOT, "secrets", "credentials.json")

DB = dict(user="root", host="213.199.62.248", port=5434, database="lge", password="Itachi933641")


def load_config():
    c = json.load(open(CONFIG_PATH))
    creds = json.load(open(CREDS_PATH))
    evo = creds.get("evolution", {})
    c.setdefault("evolution", {})
    for k in ("base_url", "api_key", "instance"):
        c["evolution"].setdefault(k, evo.get(k, ""))
    if "PASTE_" in json.dumps(c["evolution"]):
        sys.exit("evolution creds missing in secrets/credentials.json")
    return c


def norm_phone(raw):
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


def evo_state(c):
    e = c["evolution"]
    url = f"{e['base_url'].rstrip('/')}/instance/connectionState/{e['instance']}"
    try:
        req = urllib.request.Request(url, headers={"apikey": e["api_key"]})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode() or "{}"
    except urllib.error.HTTPError as ex:
        return f"HTTP {ex.code}"
    return "open OK" if '"open"' in body.lower() else body[:200]


def evo_send(c, number, text):
    e = c["evolution"]
    url = f"{e['base_url'].rstrip('/')}/message/sendText/{e['instance']}"
    h = {"Content-Type": "application/json", "apikey": e["api_key"]}
    last = "?"
    for body in ({"number": number, "textMessage": {"text": text}},  # Evolution v2
                 {"number": number, "text": text}):                   # legacy builds
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
                continue
        except Exception as ex:
            last = str(ex)
    return False, last


# ---------------- lead sourcing (our DB) ----------------

def due_leads(con, limit):
    """autopilot on, still 'new', reachable, never D1-messaged. Steering-aware."""
    rows = con.run(
        """select l.id, l.name, coalesce(l.business, l.name) as business,
                  coalesce(l.contact_name, '') as contact_name,
                  l.phone, l.mobile, l.steering, l.odoo_id
           from crm_lead l
           where l.autopilot = true
             and l.stage = 'new'
             and coalesce(l.phone, l.mobile) is not null
             and not exists (select 1 from crm_activity a
                             where a.lead_id = l.id and a.kind = 'wa_msg')
           order by l.is_test desc, l.id
           limit :lim""", lim=limit)
    return [dict(id=r[0], name=r[1], business=r[2], contact_name=r[3],
                 phone=r[4], mobile=r[5], steering=r[6], odoo_id=r[7]) for r in rows]


def sent_today(con):
    n = con.run("select count(*) from crm_activity where kind='wa_msg' and created_at::date = current_date")[0][0]
    return n


def render(c, rec):
    out = c["outreach"]
    biz = (rec.get("business") or rec.get("name") or "aapke business").strip()
    person = (rec.get("contact_name") or "").strip()
    name = person.split()[0] if person else (biz.split()[0] if biz else "ji")
    num = norm_phone(rec.get("mobile") or rec.get("phone"))
    line1 = out.get("default_line1", "").strip()
    if rec.get("steering"):
        # steering hint reserved for the AI layer; template stays standard in v2
        line1 = line1
    templates = out.get("message_templates") or []
    text = random.choice(templates).format(
        business=biz, name=name, line1=line1,
        demo_link=out.get("demo_link", ""), my_name=out.get("my_name", ""))
    return num, text


def log_sent(con, lead_id, variant, status, steering, odoo_id):
    if status == "sent":
        con.run("insert into crm_activity (lead_id, kind, detail, meta)"
                " values (:lid, 'wa_msg', :d, :m)",
                lid=lead_id, d="D1 intro sent (variant %s)" % variant,
                m=json.dumps({"variant": variant, "steering": steering or None,
                              "odoo_id": odoo_id}))
        con.run("""update crm_lead set stage='contacted',
                     next_action='D1 sent — check for reply tomorrow',
                     next_action_at = now() + interval '1 day',
                     ai_note = 'Sent D1 intro on WhatsApp. Waiting for reply — will follow up in 24h.'
                     where id = :lid""", lid=lead_id)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--send", action="store_true", help="LIVE: actually send (default is dry-run)")
    p.add_argument("--test", action="store_true", help="send one preview to owner WhatsApp")
    p.add_argument("--limit", type=int, default=10, help="max leads this run")
    a = p.parse_args()

    c = load_config()
    cap = c["outreach"].get("daily_cap", 15)
    con = pg8000.native.Connection(**DB)

    print(f"Evolution instance state: {evo_state(c)}")
    already = sent_today(con)
    print(f"sent today (all channels): {already}/{cap}")

    if a.test:
        num = c["outreach"].get("owner_number") or "917705871046"
        sample = {"name": "Sanjeev", "business": "Dental Wellness",
                  "contact_name": "Sanjeev", "steering": None}
        _, text = render(c, sample)
        ok, info = evo_send(c, num, text)
        print(f"TEST -> {num}: {info}\n---\n{text}")
        return

    leads = due_leads(con, limit=min(a.limit, max(cap - already, 0)))
    print(f"due leads pulled: {len(leads)} (limit {a.limit}, remaining cap {max(cap-already,0)})")
    if not leads:
        print("nothing due — cap reached or no eligible leads")
        return

    for i, rec in enumerate(leads, 1):
        num, text = render(c, rec)
        print(f"\n[{i}/{len(leads)}] {rec['business']} (crm#{rec['id']} odoo#{rec['odoo_id']}) -> +{num}")
        print("  " + text.replace("\n", "\n  ")[:400])
        if rec.get("steering"):
            print(f"  🎯 steering: {rec['steering'][:120]}")
        if not a.send:
            continue
        ok, info = evo_send(c, num, text)
        variant = "v?"  # derived from which template matched is lost; log success only
        log_sent(con, rec["id"], variant if ok else "fail", "sent" if ok else "failed",
                 rec.get("steering"), rec["odoo_id"])
        print(f"  -> {info}")
        if i < len(leads):
            time.sleep(random.randint(c["outreach"].get("delay_min_s", 45),
                                      c["outreach"].get("delay_max_s", 90)))
    con.close()
    print("\nDONE" + (" (LIVE SEND)" if a.send else " (dry-run — nothing sent)"))


if __name__ == "__main__":
    main()
