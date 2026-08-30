# Local Growth Engine — pilot stack

Private monorepo for the LGE pilot (owner: gochapachi / Anagata IT Solutions).

## What lives here
- `dashboard/` — GTM Control Tower + client portal (vanilla SPA, zero-config, mobile-first). **Deploy state & recovery runbook: `dashboard/DEPLOY-STATE.md`**
- `outreach-sender/` — WhatsApp sender v2: sources leads from **our Postgres** (`crm_lead`, Odoo-free), dry-run default, daily cap 15, 45–90s delays
- `crm/` — CRM schema + migrations (`v3-agentic.sql` = steering/autopilot/ai_note, `enrich_details.py`, `harden-api.sql`, `safety-autopilot.sql`)
- `infra/` — Traefik dynamic config (`traefik/lge-api.yml` = the `/api` route), dashboard compose history, `lge-stack.yml` (legacy reference — live stack is direct docker-run)
- GTM playbooks: `01-…07-` docs · `SOP.md` = git rules · `NEXT-UP.md` = remaining work

## Environments
- `main` = production · `staging` = integration · every change = feature PR → staging → (owner) → main
- **Deploy staging:** merge PR → `POST /api/v1/deploy?uuid=<staging_app_uuid>&force=true` → verify `curl -s https://pilot-staging.anagataitsolutions.in/ | grep v0.4`

## Live endpoints
- Staging dashboard v0.4.1: https://pilot-staging.anagataitsolutions.in (+ `/api`)
- Prod dashboard (frozen at old UI until first e2e sale): https://pilot.anagataitsolutions.in
- Coolify panel: https://server.anagataitsolutions.in (4.3.14)

## Safety rails
- Autopilot ON only for test lead (odoo_id 10421) until the drill passes
- Sender never sends without `--send`; dedupe via `crm_activity` wa_msg rows
- Credentials table revoked from anon role (401 verified)
