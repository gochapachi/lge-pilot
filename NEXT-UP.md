# NEXT UP — single source of truth for remaining work

## Now (this week)
- [ ] **Owner: open staging on phone** → try Sales → lead → 🤖 AI cockpit (steering + autopilot)
- [ ] **OWNER ACTION (NOW DRILL-CRITICAL):** n8n → workflow **"Anagata AIRM - Multi-Agent Sales"** → settings → enable **"Available in MCP"**. Then I apply the scripted FreeLLM swap (`crm/AIRM-provider-fix.md`). **Why now:** AIRM auto-replies are cross-talking on the drill thread (off-context GPay chatter after owner's "Whatsapp pe" reply + it sent a raw "Bad request — Generate Post" error to 919026019566). Same WhatsApp sender, two brains — swap or pause AIRM before the walkthrough continues.
- [ ] **Drill state (31-Aug):** D1 → "where did you get my number" answered → D2 nudge 07:15 IST → owner "explain more" 07:35 → demo explanation + live samples 07:48 → **owner picked "Whatsapp pe"** → **HOLD: AIRM cross-talk on the thread, owner asked "did you send it?" (audit: no — GPay referral never touched our instance)**. Resume walkthrough right after AIRM swap. ⚠️ Owner replies land under lid JID `259768245555447@lid` — inbox.py watches both now.
- [ ] Pilot drill e2e on 10421: reply ✅ → explanation ✅ → **next: owner picks live demo call ya WhatsApp continue → Cashfree test link → closed_won → exit gate**.
- [x] **Vision QA round 3 on live staging (31-Aug):** pass — search/FAB/crash/cockpit all verified; **1 real bug found+fixed+deployed**: Today KPIs (msgs/replies/paid) silently always 0 (epoch-ms filter → 400s swallowed); v0.4.3 live, zero console errors, KPIs verified rendering (1331 pipeline). UI activity feed shows D2 row ✅
- [ ] n8n reply bridge (webhook → messages table) so replies land in Inbox automatically

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
