# Coolify deployment map (from this repo — SOP compliant)

## Apps
| Coolify app | Branch | Purpose | Domain |
|---|---|---|---|
| lge-dashboard-staging | `staging` | integration testing | pilot-staging.anagataitsolutions.in |
| lge-dashboard-prod | `main` | production | pilot.anagataitsolutions.in |

## Data stack
`infra/lge-stack.yml` (postgres + postgrest + minio) — deployed once via Coolify UI (v4.3.11 envs API limitation, see DO-THIS-NOW.md), then managed in-repo.

## Flow
PR → staging branch merged → Coolify **lge-dashboard-staging** Redeploy → verify
→ PR staging→main (owner merges) → Coolify **lge-dashboard-prod** Redeploy → tag vX.Y.Z