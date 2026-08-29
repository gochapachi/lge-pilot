# Infra Manifest — pilot guardrails (the safety contract)

## Rules (in force for the whole pilot)
1. **CREATE-ONLY on existing infra.** Never edit, redeploy, stopping, or delete ANY existing Coolify project/application/service or ANY existing n8n workflow, credential, or variable.
2. Everything I create is named with a prefix:
   - Coolify: `lge-pilot-*` (projects, apps, DBs)
   - n8n: `[HERMES] <name>` (workflows, credentials)
   - DNS: only subdomains like `<something>.clients.<yourdomain>` or `pilot.<yourdomain>`
3. Every resource I create gets logged in the table below — name, ID, date, why — so you can audit / delete in one afternoon when pilot ends.
4. Anything that needs touching existing infra (firewall, ports, upgrades) → I ASK in chat first, you click/allow.
5. Keys you share live in config files with owner-only perms (or the dashboard vault); rotate everything after pilot.

## Created resources log
| Date | Platform | Name | ID | Purpose | Remove how |
|---|---|---|---|---|---|
| — | — | — | — | nothing created yet | — |