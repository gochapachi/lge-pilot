# WA Outreach Sender (Odoo → Evolution API → WhatsApp)

## One-time setup (2 min)
```bash
chmod 600 config.json          # keep secrets private
pip3 install -r nothing        # stdlib only, nothing to install
```

## Run order — never skip steps 1–2
```bash
python3 sender.py --dry-run              # 1. read the exact messages it will send
python3 sender.py --test +91XXXXXXXXXX   # 2. preview lands on YOUR whatsapp
python3 sender.py --limit 5              # 3. first live batch of 5
python3 sender.py --limit 40             # 4. full day (auto-stops at daily cap)
```

## What it does automatically
- Dedupes forever: a lead is never messaged twice (`sent_state.csv`)
- Marks every sent lead in Odoo: chatter note + `WA-Outreach` tag
- Logs every attempt to `send_log.csv`
- Random 45–90s delays + daily cap 40 = human-like pace, protects the number

## Config knobs (config.json)
- `daily_cap` — max sends/day (leave 40 for first 2 weeks)
- `line1_overrides` — `{"9198xxxxxxx": "custom first line for this lead"}`
- `domain` — which Odoo leads qualify (default: type=lead; change to
  `[["type","=","opportunity"]]` or `[]` for all, or switch `model` to `res.partner`)

## Where to find your credentials
| Field | Where |
|---|---|
| Evolution `base_url` | e.g. `http://127.0.0.1:8080` on the VPS or `https://evo.yourdomain.com` |
| Evolution `api_key` | server's `.env` → `AUTHENTICATION_API_KEY` (or instance token) |
| Evolution `instance` | instance name in Evolution Manager |
| Odoo `db` | login page URL `?db=...` or `/web/database/manager` |
| Odoo `api_key` | Odoo → Settings ▸ Users ▸ Preferences ▸ **API Keys** (Odoo 15+) |
| Odoo `model` | `crm.lead` (pipeline) or `res.partner` (contacts) |

## Ban-safety rules (read once)
Cold messages from a personal-number instance get Meta-banned if you blast.
Daily cap + delays + personalization = the whole defense. When revenue allows,
move to official WhatsApp Business API (WABA) — then caps stop mattering.

## Warm-up ramp (cold sends per day, raise only if block rate < 1%)
Week 1: 15  (cap in config.json now) → Week 2: 30 → Week 3+: 40–50 hard max.
Rules that matter more than volume:
- NO link in the first cold message; send the demo link only after any reply (or in 2nd follow-up)
- Rotate 3+ message wording variants — never send identical text to many numbers
- Sends only 10am–8pm IST, spread out (sender already randomizes 45–90s)
- Keep the number human: profile photo + about + 2FA PIN, real chats with friends/clients
- Stop same-day if: many single-grey-tick sends, in-app warning banner, block rate >2%
- Watch weekly: (blocks+reports)/delivered. >2% = halve the cap for 3 days.
Warm leads (they messaged first) never count against the cap — chat and close freely.