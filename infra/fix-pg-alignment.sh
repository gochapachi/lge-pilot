#!/bin/bash
# fix-pg-alignment.sh — align the LGE Postgres to owner creds + provision PostgREST roles.
# Usage: fix-pg-alignment.sh <OWNER_PW> <REST_PW> [EVO_KEY] [EVO_URL] [EVO_INSTANCE] [OWNER_WA]
# Volume/label based targeting (never fuzzy). Designed for lge-pilot-data-v7 on Coolify 4.3.11.
set +e
OWNER_PW="${1:-Itachi933641}"
REST_PW="${2:-LgeRest2026#pw}"
EVO_KEY="${3:-}"
EVO_URL="${4:-}"
EVO_INSTANCE="${5:-}"
OWNER_WA="${6:-}"
PG_VOLUME="lge-pgdata-v7"
PROJECT="lge-pilot-data-v7"

echo "=== 1. isolate target container ==="
TARGET=$(docker ps -q --filter "volume=${PG_VOLUME}")
if [ -z "$TARGET" ]; then
  TARGET=$(docker ps -q --filter "publish=5434" | head -1)
fi
if [ -z "$TARGET" ]; then
  TARGET=$(docker ps -q --filter "label=com.docker.compose.project=${PROJECT}" --filter "label=com.docker.compose.service=db" | head -1)
fi
if [ -z "$TARGET" ]; then
  echo "FATAL: no container found for volume ${PG_VOLUME}"
  docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}" | grep -Ei "postgres|5434"
  exit 1
fi
docker ps --filter "id=$TARGET" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

echo "=== 2. superuser probe via socket (OS user postgres, trust auth) ==="
SUPER=""
for U in postgres root lge_admin; do
  R=$(docker exec -u postgres "$TARGET" psql -U $U -d postgres -tAc "select 1" 2>&1)
  echo "probe $U -> $R"
  if [ "$R" = "1" ]; then SUPER=$U; break; fi
done
if [ -z "$SUPER" ]; then echo "FATAL: no superuser via socket"; exit 1; fi
echo "WORKING_SUPERUSER=$SUPER"

echo "=== 3. align passwords (postgres, root, lge_admin) ==="
docker exec -u postgres "$TARGET" psql -U $SUPER -d postgres -c "ALTER USER $SUPER WITH PASSWORD '$OWNER_PW';" && echo "PG_ALIGNED=$SUPER"
docker exec -u postgres "$TARGET" psql -U $SUPER -d postgres -c "DO \$do\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='root') THEN CREATE ROLE root LOGIN PASSWORD '$OWNER_PW' SUPERUSER; ELSE ALTER ROLE root WITH LOGIN PASSWORD '$OWNER_PW' SUPERUSER; END IF; END \$do\$;" && echo ROOT_OK
docker exec -u postgres "$TARGET" psql -U $SUPER -d postgres -c "DO \$do\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lge_admin') THEN CREATE ROLE lge_admin LOGIN PASSWORD '$REST_PW' SUPERUSER; ELSE ALTER ROLE lge_admin WITH LOGIN PASSWORD '$REST_PW' SUPERUSER; END IF; END \$do\$;" && echo LGE_ADMIN_OK

echo "=== 4. ensure database lge ==="
docker exec -u postgres "$TARGET" psql -U $SUPER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='lge'" | grep -q 1 || \
  docker exec -u postgres "$TARGET" psql -U $SUPER -d postgres -c "CREATE DATABASE lge OWNER root"
docker exec -u postgres "$TARGET" psql -U $SUPER -d postgres -c "ALTER DATABASE lge OWNER TO root" && echo DB_LGE_OK

echo "=== 5. provision lge_anon + grants ==="
docker exec -i -u postgres "$TARGET" psql -U $SUPER -d lge <<EOF
DO \$do\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lge_anon') THEN CREATE ROLE lge_anon NOLOGIN; END IF; END \$do\$;
GRANT lge_anon TO $SUPER;
GRANT lge_anon TO root;
GRANT lge_anon TO lge_admin;
GRANT ALL ON SCHEMA public TO root, lge_admin, lge_anon;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO lge_admin, lge_anon;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO lge_admin, lge_anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO lge_admin, lge_anon;
EOF
echo "anon_grants_rc=$?"

echo "=== 6. apply dashboard schema (schema-pg.sql from repo) ==="
curl -fsSL https://raw.githubusercontent.com/gochapachi/lge-pilot/staging/dashboard/schema-pg.sql -o /tmp/schema.sql
docker exec -i -u postgres "$TARGET" psql -U $SUPER -d lge < /tmp/schema.sql > /tmp/schema_out.txt 2>&1
echo "schema_rc=$? errors=$(grep -ci error /tmp/schema_out.txt 2>/dev/null)"
docker exec -u postgres "$TARGET" psql -U $SUPER -d lge -tAc "select count(*) from leads"
echo "leads_count_above"
docker exec -u postgres "$TARGET" psql -U $SUPER -d lge -tAc "select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE'"
echo "tables_count_above"

echo "=== 7. WA notify ==="
if [ -n "$EVO_KEY" ]; then
  curl -s -X POST -H "apikey: $EVO_KEY" -H "Content-Type: application/json" \
    "$EVO_URL/message/sendText/$EVO_INSTANCE" \
    -d "{\"number\":\"$OWNER_WA\",\"text\":\"LGE: PG aligned (postgres/root/lge_admin all = owner password). Schema applied. Verifying dashboards next.\"}" \
    -o /dev/null -w "wa=%{http_code}\n"
fi
echo "ALIGNMENT_DONE"