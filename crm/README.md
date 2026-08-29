# LGE-CRM (our own — replaces the Odoo lead layer)

Your CRM, same database as the dashboard, zero external dependency.

## Components
| File | What |
|---|---|
| `crm-schema.sql` | `crm_lead` (1,331 imported Odoo leads fit here) + `crm_activity` (every touch: WA msgs, calls, demos, payments, stage moves) |
| `import_leads.sql` | One-command Odoo import (idempotent upsert, stage mapping New/FollowUp/… → our stages) |
| `sync_odoo.py` | Future: periodic delta-sync from Odoo if kept alive in parallel (optional) |

## Data flow now
```
Import (once)          Outreach sender        Dashboard
Odoo CSV → crm_lead → sends WA → replies recorded in crm_activity → portal dashboards
```

## Odoo decommission plan
- [x] FULL export → secrets/odoo_leads_export.{json,csv} (1,331 leads)
- [ ] Deploy data stack → apply crm-schema.sql → run import
- [ ] outreach-sender switched to read crm_lead (PR pending)
- [ ] Freeze Odoo (owner stops using; no deletion until 2 clean weeks)
- [ ] Delete Odoo leads only after owner confirms (create-only pilot rule)

## Stage mapping
Odoo New/Contacted/FollowUp/Replied/Probing/Demo Sent/Negotiating/Won/Lost → our 9-stage pipeline (same names + `followup`).