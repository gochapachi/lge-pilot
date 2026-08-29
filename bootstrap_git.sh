#!/bin/bash
set -e
cd /workspace/gtm
TOKEN=$(python3 -c "import json;print(json.load(open('secrets/credentials.json'))['github']['token'])")
cat > .gitignore <<'EOF'
secrets/
*.log
__pycache__/
node_modules/
.crumbs/
.DS_Store
EOF
cat > README.md <<'EOF'
# Local Growth Engine — pilot stack
Private monorepo for the LGE pilot (owner: gochapachi / Anagata IT Solutions).

- `dashboard/` — owner control tower + client portal (static SPA)
- `outreach-sender/` — Odoo → Evolution API WhatsApp sender (ban-safe)
- `supabase-schema.sql` equivalent → `dashboard/supabase-schema.sql`
- Infra guardrails: `infra-manifest.md` (lge-pilot-* naming, create-only pilot)

## Environments
- `main` = production · `staging` = integration · every change = feature PR → staging → PR → main
EOF
git init -q -b staging
git config user.name "gochapachi"
git config user.email "sanjeevcs0034@gmail.com"
git add -A
git commit -q -m "pilot baseline: dashboard, outreach sender, playbooks, test-lead runbook, infra manifest"
git remote add origin "https://gochapachi:${TOKEN}@github.com/gochapachi/lge-pilot.git"
git push -q -u origin staging
# main branch from same commit (production)
git checkout -q -b main
git push -q -u origin main
git checkout -q staging
echo "pushed: staging + main"