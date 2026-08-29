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

## Pending after DB healthy
apply schema-pg.sql (43 stmts + test-lead seed) → PostgREST :3100 probe → dashboard app deploy → MinIO bucket `lge-assets` creation
| 2026-08-29 | Coolify | app lge-dashboard-staging (branch staging) | b3ajomufklzssswfftpxamy0 | http://pilot-staging.anagataitsolutions.in | delete app |
| 2026-08-29 | Coolify | app lge-dashboard-prod (branch main) | smp37boufquxlqhyn9hke97t | http://pilot.anagataitsolutions.in (idle til PR#2) | delete app |
| 2026-08-29 | GitHub | PRs #1,#3 merged to staging; #2 (staging->main) awaiting owner | — | SOP flow | close PR |
