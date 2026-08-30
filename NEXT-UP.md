# NEXT UP — single source of truth for remaining work

## Now (this week)
- [ ] **Owner: open staging on phone** → try Sales → lead → 🤖 AI cockpit (steering + autopilot)
- [ ] **D1 send**: `python3 outreach-sender/sender.py --send --limit 1` (goes to owner's own WhatsApp = test lead 10421)
- [ ] Pilot drill e2e on 10421: reply → demo → Cashfree link → closed_won → **exit gate**
- [ ] Vision QA round 2 on live staging after v0.4.1 deploy
- [ ] n8n reply bridge (webhook → messages table) so replies land in Inbox automatically

## Next (after exit gate)
- [ ] Prod release: PR staging→main (**owner merges**) + deploy lge-dashboard-prod
- [ ] Autopilot ramp decision (batch sizes, block-rate monitoring)
- [ ] Dashboard PIN gate (unauthenticated dashboard + readable clients table = pilot risk, fix before real client data)
- [ ] MinIO `lge-assets` bucket + client access keys
- [ ] Server-capacity module (dashboard tab: sites hosted vs VPS limits)
- [ ] First client website gen test on `*.anagataitsolutions.in` subdomain (Coolify + WordPress)
- [ ] Data cleanup: mojibake in lead names (Ã chars from Odoo export encoding)
- [ ] Credential rotation: DB, SSH, tokens (after drill stabilizes)

## Known quirks (do not rediscover)
- Coolify 4.3.14 panel = `source-*` containers, bridged to `coolify` net w/ legacy aliases; `extra_hosts` fix in compose file — re-apply runbook: `dashboard/DEPLOY-STATE.md`
- Deploys go to `coolify2` network (destination repointed); `coolify` network has malformed IPv6 gateway — do NOT recreate it while containers are attached
- `qkwscgkcoswookwo44k4k4w8-proxy` container sits in Created state (pre-existing, not ours — ask owner)
- Ops tables (leads/messages/demos…) are separate from `crm_lead`; sender + Sales use crm_lead, Inbox chat still ops
