# Repository SOP — how every change ships (STRICT)

## Golden rules
1. **NEVER push directly to `main` or `staging`.** All work goes through feature branches + Pull Requests.
2. `main` = production · `staging` = integration/testing · `feat/*`, `fix/*`, `infra/*` = work branches.
3. Every PR: self-review checklist filled + one-line changelog in the description.
4. Deployments:
   - **staging** (integration): PR merged → Coolify resource watching `staging` → Redeploy.
   - **main** (production): PR staging→main, merged ONLY after the stack is verified healthy on staging.
5. **Secrets never enter the repo.** `secrets/` is gitignored. Compose files may hold pilot literals in this private repo ONLY until first production client — then move to Coolify envs (tracked as tech-debt issue).
6. Every PR title: `feat:|fix:|infra:|docs: <what>` · small, single-purpose diffs.
7. Rollback = `git revert` PR to staging + Redeploy. Never force-push any shared branch.

## Merge policy (solo-founder-lean, adjustable)
- `feat/* → staging`: LGE agent merges after self-review IF change is additive (new files/docs);
  anything touching existing behavior → PR link sent to owner on WhatsApp for 1-click review.
- `staging → main`: ALWAYS owner merges (that's the production trigger).

## Repo map
- `dashboard/` — control tower SPA + schema-pg.sql
- `outreach-sender/` — Odoo→Evolution WA sender
- `infra/` — docker-compose stacks deployed via Coolify (from repo, not hand-pasted)
- `playbooks/` → playbooks/run docs live in repo root *.md (numbered files)

## Tags
- `vX.Y.Z` on main after each production merge (what's live, when).