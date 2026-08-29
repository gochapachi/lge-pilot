# Local Growth Engine — pilot stack
Private monorepo for the LGE pilot (owner: gochapachi / Anagata IT Solutions).

- `dashboard/` — owner control tower + client portal (static SPA)
- `outreach-sender/` — Odoo → Evolution API WhatsApp sender (ban-safe)
- `supabase-schema.sql` equivalent → `dashboard/supabase-schema.sql`
- Infra guardrails: `infra-manifest.md` (lge-pilot-* naming, create-only pilot)

## Environments
- `main` = production · `staging` = integration · every change = feature PR → staging → PR → main
