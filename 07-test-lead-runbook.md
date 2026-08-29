# Test-Lead Runbook — full lifecycle drill (Dental Wellness, lead id in Odoo)

**Purpose:** rehearse outreach → probing → demo → close → payment → onboarding → delivery → upsell with YOUR own number as the lead. Find every break BEFORE a real lead touches the machine.

**Golden rule (never forget):** we are a **helpful human operation, never a sales agent**. Anyone reading the chat should think "ye kaise kar lete hain, kitna helpful hai" — not "koi bech raha hai".

## The Conversation Constitution — how every WhatsApp message is written
1. **Human pacing:** messages go in small chunks as separate bubbles — "hi dr. sharma :)" then bubble 2 "kaise hain aap?" then *wait for their reply*. Never a wall of text. Never 3 questions in one message.
2. **Reply length:** default 1 line, max 2 short lines. If a full answer needs a paragraph → send the key line + "detail bhej doon?" and follow with 2–3 short bubbles.
3. **No pitch vocabulary, ever:** no "offer", "package", "limited time", "discount", "opportunity", "dear sir". We *talk about their problem*, not our product.
4. **Help before sell:** every reply must give them something useful — an observation about their Google listing, a free suggestion, a sample. The demo IS the pitch.
5. **Match their language**: they write Hinglish → we write Hinglish; formal English → formal English. Mirror their typing style (emojis only if they use them).
6. **Ask one thing at a time** and end with easy questions they can answer in 5 words ("aapka khud sambhalta hai ye sab?" beats "would you be interested in a comprehensive discussion about...").
7. **Never push twice in a row.** If they went quiet after a demo: helpful ping once ("demo dekha? koi part confusing thi?"), then wait 2 days.
8. **Their pace wins.** Closing = when THEY ask "iske liye kya karna padega". If they don't ask, we keep being useful in small doses.
9. **Memory is the relationship:** before every reply, re-read this lead's notes — their kid's exam, their clinic timings, what annoyed them. Reference one small real thing occasionally, never robotically.
10. **Honesty beats closing:** if our system isn't right for them, say it. One "aapke liye ye zaroori nahi" buys ten referrals.

## Stage playbook (same for test lead & real leads)
| Stage | What happens | Who |
|---|---|---|
| new → contacted | D1 message, variant rotation, NO link | sender / Hermes |
| contacted → replied | They reply → instant ack from n8n, real reply ≤15 min | n8n + Hermes |
| replied → probing | 2–4 human bubbles: their pain, who does their reviews now, timings. Log EVERY fact to lead notes | Hermes |
| probing → demo_sent | Build custom sample (blog about THEIR keyword / mock site header / placard with THEIR name). Send in chunks: "banaya hai aapke liye" → asset → "dekhiye, pasand aaye to batayein" | Hermes + n8n |
| demo_sent → negotiating | Their feedback → adjust → mention trial ₹15,000 ONLY when they ask price/next steps. Price objection → annual ₹40,000 framing; never beg | Hermes (escalate if >10% discount demanded) |
| negotiating → closed_won | Payment link (Cashfree) → receipt → send onboarding checklist | Hermes → boss confirms |
| closed_won → onboarding | Create client row + access code · collect credentials via portal vault link · WordPress app password · GBP manager access · brand kit photos · n8n webhooks live | Hermes + client |
| onboarding → active delivery | Weekly cycle: 1 blog published + Google post pack + carousel + infographic + video + review replies + placards + month-end report | Hermes (fulfillment engine) |
| active → upsell | Natural moments: "reviews badh rahe hain, placard campaign bhi chalu karein ₹1,999?" — suggest, never push | Hermes (escalate if custom dev) |

## Test drill checklist (run against your own WhatsApp)
- [ ] Outreach D1 arrives as 2–3 human chunks, no link, correct template
- [ ] You reply → ack within 1 min, real reply < 15 min
- [ ] Probing feels like a conversation (recheck constitution list above)
- [ ] Custom demo generated with YOUR business details
- [ ] Trial ₹15,000 raised naturally, one objection handled
- [ ] Payment link → paid → onboarding msg sequence
- [ ] Client row created, access code works on ?#/portal
- [ ] Vault: save WordPress creds → reveal works → decrypt on another browser with passphrase
- [ ] Sample blog + placard + carousel appear in portal "Delivered"
- [ ] Ticket created from portal → escalation appears on Today tab
- [ ] Hourly report reaches your WhatsApp (once bridge live)
Fix anything that fails → rerun → hand over to real lead #1.

## Bridge contract (n8n webhook → Evolution API)
The dashboard "Send as chunks" posts to bridge URL: {type:'send_chunks', lead_id, messages:[{text,delay_s}], message_id}. n8n: for each chunk — WAIT(delay_s) → Evolution sendText → PATCH message status→sent → append chunked bubbles. Inbound: Evolution messages.minus webhook → POST /rest/v1/messages {direction:'in', status:'received'} + PATCH lead.stage='replied' if new + insert event.