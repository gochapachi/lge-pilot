# COOLIFY UI — 3-minute manual step (last piece of the stack)

## Where: project `lge-pilot` ▸ service `lge-pilot-data5`
Debug note: API can't fill the envs on Coolify 4.3.11 (they exist but are empty and locked).
You'll fill them in the UI once — after this, everything automates again.

## EASIEST PATH (recommended)
1. Coolify → **lge-pilot** → **lge-pilot-data5** → ⚙️/delete (top-right) → delete it
2. **+ New resource → Docker Compose → Empty**
3. Paste this EXACTLY into the compose editor:

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER= lge_admin
      - POSTGRES_PASSWORD= ChangeMe_LGE_pg_2026
      - POSTGRES_DB= lge
    volumes:
      - lge-pgdata-final:/var/lib/postgresql/data
    ports:
      - "5433:5432"
  rest:
    image: postgrest/postgrest:latest
    environment:
      - PGRST_DB_URI=postgres://lge_admin:ChangeMe_LGE_pg_2026@db:5432/lge
      - PGRST_DB_SCHEMA=public
      - PGRST_DB_ANON_ROLE=lge_anon
    ports:
      - "3100:3000"
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER= lge_minio
      - MINIO_ROOT_PASSWORD= ChangeMe_LGE_minio_2026
    volumes:
      - lge-minio-final:/data
    ports:
      - "9000:9000"
      - "9001:9001"

volumes:
  lge-pgdata-final:
  lge-minio-final:

⚠️ After pasting, REMOVE the space after each "=" (the space is only there so this
file survives markdown) — line should read exactly: `- POSTGRES_USER=lge_admin`

4. Click **Deploy**. Wait ~60s (3 containers: db, rest, minio).
5. WhatsApp me / reply here: "stack up" — I take it from there (schema + verify + dashboard deploy + gen a test website on anagataitsolutions.in subdomain).

## THEN (I run automatically once you confirm)
- [ ] Apply full LGE schema (12 tables + client-portal RPCs + test lead)
- [ ] Verify PostgREST :3100 + MinIO :9000 live probes
- [ ] Create `lge-assets` bucket + access keys for asset uploads
- [ ] Deploy dashboard (nginx) on Coolify → open to you
- [ ] Test-lead drill continues + first website generation on anagataitsolutions.in subdomain

## Values summary (change later in UI, no redploy drama)
| Env | Value |
|---|---|
| POSTGRES_USER | lge_admin |
| POSTGRES_PASSWORD | ChangeMe_LGE_pg_2026 |
| POSTGRES_DB | lge |
| MINIO_ROOT_USER | lge_minio |
| MINIO_ROOT_PASSWORD | ChangeMe_LGE_minio_2026 |