# Infra Manifest — pilot guardrails (the safety contract)

## Rules (in force for the whole pilot)
1. **CREATE-ONLY on existing infra.** Never edit, redeploy, stop, or delete ANY existing Coolify project/application/service or ANY existing n8n workflow, credential, or variable.
2. Everything I create is named with a prefix: Coolify `lge-pilot-*` · n8n `[HERMES] <name>` · DNS subdomains only.
3. Every created resource is logged below — audit + one-afternoon cleanup when pilot ends.
4. Anything needing existing infra (firewall/ports/upgrades) → asked in chat first.
5. Keys in `gtm/secrets/credentials.json` (chmod 600, gitignored); rotate after pilot.

## Existing resources seen (NOT touched — audit trail)
- Coolify projects: Anagata Apps, newproject, remotion project, Hyperframes, Property Verify, AIRM
- n8n instance "n8n" (Evolution WA connected), Odoo 18 (anaagtaerp), GoDaddy domain anagataitsolutions.in

## Created resources log
| Date | Platform | Name | ID | Purpose | Remove how |
|---|---|---|---|---|---|
| 2026-08-29 | GitHub | repo lge-pilot (private) | gochapachi/lge-pilot | pilot codebase, staging env, main prod | delete repo |
| 2026-08-29 | Coolify | project lge-pilot | xq6dorfvtjrjez2ausdqqkgi | pilot container group | delete project |
| 2026-08-29 | Coolify | service lge-pilot-data (pg+postgrest) v1 | idirnmbg6ync7bo8vnowab1k | **DELETED** (fresh-volume rebuild) | — |
| 2026-08-29 | Coolify | **service lge-pilot-data v2** (postgres16+postgrest+minio) | zgybdosvfnvpaohzvxpr4fzi | dashboard DB + S3 asset storage | delete service |
| 2026-08-29 | Evolution | 5+2 test WA msgs to 917705****46 | secrets/last_drill.json | pilot drill D1 | n/a |
| 2026-08-29 | Odoo | chatter note on lead 10421 | lead 10421 | drill audit | delete note |

| 2026-08-29 | Coolify | app dockerfile-pack (deleted, never cloned repo) | — | learning | — |
| 2026-08-29 | Coolify | app /public xgkqb... (token-URL, stripped) | — | learning | — |
| 2026-08-29 | Coolify | app lge-dashboard-staging (ssh+key, image built; ParseAddr bug on start) | tku33uuof3ap37pzcfvof7va | learn ParseAddr IPv6 bug | delete app |
| 2026-08-29 | Coolify | service lge-dashboard-staging-web (serves built image, traefik) | bd5ruzmtyh1nekgjs4qb69zd | **STAGING LIVE** pilot-staging.anagataitsolutions.in :3101 | delete service |
| 2026-08-29 | GitHub | repo made PUBLIC (sanitized, PR#4; audit: zero real secrets) | 1350357715 | Coolify clone access | re-private post-pilot |
| 2026-08-29 | GitHub | deploy key added (ed25519, id 161654395) + Coolify key lge-deploy-key | — | future private deploys | delete both |

## Pending after DB healthy
apply schema-pg.sql (43 stmts + test-lead seed) → PostgREST :3100 probe → dashboard app deploy → MinIO bucket `lge-assets` creation
| 2026-08-29 | Coolify | app lge-dashboard-staging (branch staging) | b3ajomufklzssswfftpxamy0 | http://pilot-staging.anagataitsolutions.in | delete app |
| 2026-08-29 | Coolify | app lge-dashboard-prod (branch main) | smp37boufquxlqhyn9hke97t | http://pilot.anagataitsolutions.in (idle til PR#2) | delete app |
| 2026-08-29 | GitHub | PRs #1,#3 merged to staging; #2 (staging->main) awaiting owner | — | SOP flow | close PR |
| 2026-08-30 | VPS | Traefik dynamic config `/data/coolify/proxy/dynamic/lge-api.yml` (file in repo: infra/traefik/lge-api.yml) — HTTPS `/api` route pilot + pilot-staging → lge-rest :3200 | — | dashboard API | delete file |
| 2026-08-30 | DB | `crm/harden-api.sql` applied: crm_activity table created, lge_rest authenticator role, lge_anon revoked on clients+credentials (RPCs are SECURITY DEFINER), crm DML grants, updated_at trigger | — | — | — |
| 2026-08-30 | VPS | lge-rest relaunched least-privilege (connects as lge_rest, anon role lge_anon, host net, :3200) — verified: crm_lead 200, clients/credentials 401, rpc 200 | — | — | — |
