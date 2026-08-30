# Dashboard Deploy State

## Current (v0.3.0 — 2026-08-30)
- **Zero-config:** dashboard auto-connects to `location.origin + /api` — no Supabase form, no user setup.
- **API route:** Traefik dynamic config `/data/coolify/proxy/dynamic/lge-api.yml` (source of truth in repo: `infra/traefik/lge-api.yml`) serves `https://pilot{,-staging}.anagataitsolutions.in/api/*` → lge-rest (PostgREST, host net, :3200).
  - If Coolify regenerates proxy config and drops the file, re-apply: `python3 secrets/push_traefik.py` (from gtm/ workspace).
- **Least privilege:** lge-rest connects as role `lge_rest` (authenticator, member of `lge_anon`). Anon cannot read `clients`/`credentials` directly — portal RPCs are SECURITY DEFINER. Rollback to superuser connection = relaunch container with root URI.
- **Sales tab** reads `crm_lead` (1,331 rows); ops drawer (chat/demos/payments) on `leads` — namespaced keys `crm:<id>` / `ops:<id>`.
- **Mobile-first:** top nav ≥768px, 5-tab bottom bar + More sheet below; bottom-sheet lead drawer on phones; safe-area padding.

## Deploy flow
PR → merge staging → Coolify lge-dashboard-staging Redeploy (uuid b3ajomufklzssswfftpxamy0)
→ verify staging → owner merges PR staging→main → Coolify lge-dashboard-prod Redeploy (uuid smp37boufquxlqhyn9hke97t)

## Historical
- v0.2.0 CRM schema PR#7 · v0.1.0 first prod release PR#2 · TLS fix PR#14 · sanitize/public-repo PR#4 · SOP PR#6
- Coolify 4.3.11 quirks (env API 409s, masked secrets, parser password regen) — see git history + SOP.
