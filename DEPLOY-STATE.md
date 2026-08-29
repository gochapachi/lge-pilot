# Deploy state (2026-08-29)
- STAGE: repo PUBLIC + sanitized (PR#4). Staging dashboard LIVE from staging-branch build:
  http://pilot-staging.anagataitsolutions.in  (ip:3101 also works)
- Pattern that works on Coolify 4.3.11: /applications/public + token-URL fails (token stripped)
  BUT public repo clones fine; static pack builds; 4.3.11 ParseAddr(IPv6) bug breaks app-start
  -> serve built image via compose service with traefik labels (WORKS).
- Prod app: recreate same way after owner merges PR#2 (staging->main) + new build.
- DB stack (pg+postgrest+minio infra/lge-stack.yml): pending ONE manual UI deploy (envs API 409).
- SearXNG: searchxng.anagataitsolutions.in available as search engine.
