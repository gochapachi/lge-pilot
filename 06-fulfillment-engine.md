# Fulfillment Engine — who does what (Hermes vs n8n vs you)

## The split (except website generation, per your note)

| Service | Who delivers | What's needed | Notes |
|---|---|---|---|
| SEO blog (keyword + competitor research + writing + publishing) | **Hermes — FULL** | Client's WordPress: admin URL + **application password** (REST API) → I publish directly, or deliver as Google Doc | I do the research via web search; no paid SEO tools needed for tier-2 keywords |
| Google Posts (from each blog, AI image) | **Hermes — 90%** | GBP API access is restricted by Google; I generate copy + image ready-to-post → owner or you paste (2 min), OR we sort GBP API later | Semi-auto until API access |
| AI review replies | **Hermes — 90%** | Same GBP constraint: I read reviews + draft same-day replies → paste, or API if approved | Can go FULL once GBP API path is sorted |
| Carousel sets (from blogs) | **Hermes — FULL** | Brand logo + colors once | Image generation included in my toolset |
| Infographic lead magnets (PDF/PNG) | **Hermes — FULL** | Same brand kit | HTML→PDF/PNG, print-quality |
| AI animation videos (short) | **Hermes — 80%** | — | Simple animated posts (text/shapes/pan-zoom, ≤30s). Hero 3D stuff stays with your n8n pipeline |
| Review placard images (founder + placard) | **Hermes — FULL** | Founder photo(s) + business name | Sent via WhatsApp to customers, on demand or batched |
| Lead capture routing (form → CRM/WhatsApp/email) | **n8n (yours) — Hermes manages/fixes** | n8n API key | I monitor executions, debug failures, add destinations when clients ask |
| Review-gate page | Website builder (n8n) | — | Out of scope per your note |
| Client reporting (month-end: reviews, posts, traffic) | **Hermes — FULL** | Google Analytics key (later) | Included in retainers, zero extra work for you |

## Monthly production run per Growth-tier client (I run this on cron)
- Week 1: keyword + competitor research → 4 blog briefs approved by client (1 WhatsApp message)
- Weeks 1–4: 1 SEO blog published + 1 Google post pack + 1 carousel set + 1 lead-magnet infographic
- 4 × ≤30s animation videos across the month
- Reviews: replies drafted/logged same-day (owner pastes until API sorted)
- Placards: batch of 4 on day 1
- Month-end: results report WhatsApp'd to client

## What it means for you
- Your capacity ≈ unlimited content ops. You only: sell, onboard (30-min call), approve drafts, paste Google posts.
- Client-facing promise stays identical: "done-for-you." Fulfillment risk ≈ zero.
- Start with 1 trial client as the pilot. Confirm quality bar → onboard all new clients this way.

## First-time setup checklist (per client, once)
- [ ] WordPress: admin login + application password (Tools ▸ Application passwords)
- [ ] GBP: access (owner adds you as manager) — for now: screenshots of reviews OR review notification emails forwarded to our inbox
- [ ] Brand kit: logo files, 2–3 founder photos, brand colors, service list
- [ ] WhatsApp of owner (for approvals + placard sending)
- [ ] n8n: which webhooks/wire the client's lead capture uses