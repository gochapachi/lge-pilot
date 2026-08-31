#!/usr/bin/env python3
"""inbox.py — inbound WhatsApp reader for the LGE pilot (no n8n).

Evolution's findMessages ignores remoteJid filters, so we page through the
recent-messages index and filter locally. Marks chats seen via local state.

Usage:
  python3 inbox.py                 # new inbound messages from the test lead
  python3 inbox.py --chat 91XX@s.whatsapp.net
  python3 inbox.py --all           # ignore seen-state, show last 10
  python3 inbox.py --log-lead 1    # also log inbound to crm_activity + reply steering
"""
import argparse, json, os, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CREDS = os.path.join(HERE, "..", "secrets", "credentials.json")
STATE = os.path.join(HERE, "..", "secrets", "inbox_state.json")

cfg = json.load(open(CREDS))
EVO = cfg["evolution"]
TEST_JID = "917705871046@s.whatsapp.net"
# Owner's WhatsApp sends/receives under BOTH the phone JID and an anonymized
# lid JID (verified 31-Aug: his "where did you get my number" + "explain more"
# replies arrived only under the lid). Watch both everywhere.
OWNER_LIDS = [l for l in cfg.get("owner_lids", ["259768245555447@lid"])]


def fetch_all(max_pages=6, per=50):
    out = []
    for page in range(1, max_pages + 1) if (max_pages := 6) else []:
        pass
    return out


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--chat", default=TEST_JID)
    p.add_argument("--all", action="store_true")
    p.add_argument("--limit", type=int, default=10)
    a = p.parse_args()
    num = a.chat.split("@")[0]
    cfg = json.load(open(CREDS))
    evo = cfg["evolution"]
    recs, page = [], 1
    while page <= 6:
        req = urllib.request.Request(
            f"{evo['base_url'].rstrip('/')}/chat/findMessages/{evo['instance']}",
            data=json.dumps({"page": page, "offset": 50}).encode(),
            headers={"apikey": evo["api_key"], "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode())
        batch = (d.get("messages") or {}).get("records", [])
        recs.extend([m for m in batch
                     if (m.get("key") or {}).get("remoteJid", "").startswith(num)
                     or (m.get("key") or {}).get("remoteJid", "") in OWNER_LIDS])
        if len(batch) < 50:
            break
        page += 1
    recs.sort(key=lambda m: int((m.get("messageTimestamp")) or 0))
    seen = json.load(open(STATE)) if os.path.exists(STATE) else {}
    fresh = 0
    for m in recs[-a.limit:]:
        k = m.get("key") or {}
        mid = k.get("id", "")
        msg = m.get("message", {}) or {}
        txt = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text", "") or ""
        ts = int(m.get("messageTimestamp") or 0)
        iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
        if not mid or (not a.all and mid in seen):
            continue
        print(f"[{iso}] {'ME >' if k.get('fromMe') else 'LEAD >'} {txt[:220]}")
        fresh += 1
    # mark all as seen
    for m in recs:
        mid = (m.get("key") or {}).get("id")
        if mid:
            seen[mid] = 1
    json.dump(seen, open(STATE, "w"))
    if not fresh:
        print("(no new inbound)")


if __name__ == "__main__":
    main()