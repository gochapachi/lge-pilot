# DEPLOY STATE — LGE Pilot (updated 30-Aug-2026)

## Live right now
| Thing | URL / location | Status |
|---|---|---|
| Dashboard **staging v0.4.0-agentic** | https://pilot-staging.anagataitsolutions.in | ✅ 200, TLS |
| Dashboard prod (old v0.3 UI, frozen until first e2e sale) | https://pilot.anagataitsolutions.in | ✅ 200, TLS |
| Coolify panel | https://server.anagataitsolutions.in | ✅ 4.3.14 |
| PostgREST API (same-origin) | https://pilot{,-staging}.anagataitsolutions.in/api | ✅ 200 |
| Data stack | lge-db-final :5434 · lge-rest :3200 · lge-minio :9002/9003 | ✅ docker-run (not Coolify) |

## The 30-Aug incident + recovery (postmortem)
**What happened:** Coolify 4.3.11 → 4.3.14 upgrade (needed to escape a compose/IPv6 deploy bug) stopped the panel's 4 control-plane containers and did not restart them. All 60+ user services kept running the whole time (only the panel 502'd).

**Recovery (all panel-only, zero user-service disruption):**
1. `cd /data/coolify/source && docker compose up -d` — starts `source-{coolify,postgres,redis,soketi}-1`
2. Panel containers land on `source_default` with new names — old names needed → bridged onto the `coolify` network with legacy aliases:
   `docker network connect --alias coolify-db coolify source-postgres-1` (+ `coolify-redis`→source-redis-1, `coolify-realtime`→source-soketi-1, `coolify`→source-coolify-1)
3. Deploys then failed `ssh: Could not resolve hostname host.docker.internal` → added to `/data/coolify/source/docker-compose.yml` under the `coolify:` service:
   `extra_hosts: ["host.docker.internal:host-gateway"]` then `docker compose up -d` (recreates panel app) + re-bridge alias.
4. Deploys then failed `ParseAddr("fd83:cf7c:a65c::1/64")` — the `coolify` docker network carries a malformed IPv6 gateway; compose (any version) crashes parsing it. Network can't be edited in place.
   **Fix:** created clean network `coolify2` (10.0.24.0/24, no IPv6), hot-connected `coolify-proxy` to it, and repointed Coolify's destination:
   `update standalone_dockers set network='coolify2' where network='coolify';` + panel restart. New deploys → coolify2; existing 60 containers untouched on `coolify` (proxy is dual-homed).
5. Staging HTTPS: Coolify's static-pack label generator only emits http routers → set `applications.custom_labels` (DB) to the working TLS label set from `infra/dashboard-web.staging.yml` (lge-staging router + LE certresolver + http→https redirect).
6. Old duplicate service `lge-dashboard-staging-web` (web-0730…, was serving the 29-Aug build) deleted via API — the application `tku33…` is now the single canonical staging server.

## Re-apply runbook (if panel containers are ever recreated)
```bash
cd /data/coolify/source && docker compose up -d
docker network connect --alias coolify-db coolify source-postgres-1
docker network connect --alias coolify-redis coolify source-redis-1
docker network connect --alias coolify-realtime coolify source-soketi-1
docker network connect --alias coolify coolify source-coolify-1
```
(extra_hosts + coolify2 destination are persisted in the compose file / DB)

## Rollback levers
- Destination back to `coolify` network: `update standalone_dockers set network='coolify';` + restart panel (but deploys will ParseAddr-fail again)
- Panel: backup of pre-fix compose at `/data/coolify/source/docker-compose.yml.bak-0830`

## Deploying staging now (the working path)
1. PR → merge to `staging` branch (repo gochapachi/lge-pilot)
2. `POST /api/v1/deploy?uuid=tku33uuof3ap37pzcfvof7va&force=true` (Coolify API)
3. Verify: `curl -s https://pilot-staging.anagataitsolutions.in/ | grep v0.4` → marker present

## Known open items
- Prod still served by service `lge-dashboard-prod-web` (web-swvje…) with old UI — intentional (staging-only until first e2e sale on test lead #10421)
- `/api/clients` readable by anon (access codes) — PIN gate needed before real client data
- `qkwscgkcoswookwo44k4k4w8-proxy` container in Created state (pre-existing, not ours to touch without asking)
- Proxy logs show acme "missing token" warnings — LE certs currently valid/renewing via existing resolvers; monitor
