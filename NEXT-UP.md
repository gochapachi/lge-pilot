# NEXT UP — single source of truth for remaining work (updated 31-Aug)

## Now (this week)
- [ ] **Owner: open staging on phone** → try Sales → lead → 🤖 AI cockpit (steering + autopilot)
- [x] **AIRM stopped by owner (31-Aug)** — cross-talk resolved. FreeLLM swap (`crm/AIRM-provider-fix.md`) still pending owner MCP toggle if AIRM comes back.
- [ ] **Drill state (31-Aug):** D1 → "where did you get my number" answered → D2 nudge 07:15 IST → owner "explain more" 07:35 → demo explanation + live samples 07:48 → **owner picked "Whatsapp pe"** → **AIRM cross-talk resolved (owner stopped it; GPay referral audited = never ours)**. Resume walkthrough. ⚠️ Owner replies land under lid JID `259768245555447@lid` — inbox.py watches both now.
- [x] **Reply bridge LIVE (31-Aug):** `crm/bridge.py` polls Evolution → ops leads (auto-create + lid-JID adoption) → `messages` (Inbox now shows chats) → FreeLLM Hinglish replies with per-thread memory + steering. Guardrails: test lead NEVER auto-replied, opt-out mute, 4/lead/day · 40/day global · 45s anti-burst · quiet hours 21:30–08:00 IST. Run `--listen` on the VPS for 24/7 (sandbox listener dies with session).
- [x] **Dashboard v0.4.4 LIVE:** `openLead()` uuid-cast bug fixed (ops chat drawers never opened — root cause of "chats not reflecting"), ops drawer got steering+autopilot cockpit, inbox cards polished. **`leads` seeding bug in schema-pg.sql (30 duplicate test rows) still unfixed — make seed idempotent.**
- [ ] Pilot drill e2e on 10421: reply ✅ → explanation ✅ → owner picked "Whatsapp pe" → **walkthrough resumes now that AIRM is stopped** → Cashfree test link → closed_won → **exit gate**.
- [x] **Vision QA round 3 on live staging (31-Aug):** pass — search/FAB/crash/cockpit all verified; **1 real bug found+fixed+deployed**: Today KPIs (msgs/replies/paid) silently always 0 (epoch-ms filter → 400s swallowed); v0.4.3 live, zero console errors, KPIs verified rendering (1331 pipeline). UI activity feed shows D2 row ✅

## UI polish (minor, from QA round 3 — batch into next PR)
- [ ] Today pipeline chip strip clips 4th chip at right edge ("PROBIN…") — add right padding/fade
- [ ] Cockpit: next_action label truncates without ellipsis ("D2 demo nudge sen")
- [ ] FAB overlaps last lead card (standard, low priority — extra list bottom padding)

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
