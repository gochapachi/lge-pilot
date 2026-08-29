#!/bin/sh
# bootstrap4: create/align users with OWNER's chosen creds + apply schema.
# Runs inside VPS (docker:cli). OWNER_PW comes from runner command (not envs).
DB=$(docker ps --format '{{.Names}}' | grep -i db | head -1)
echo "DB=$DB"
docker exec "$DB" psql -U lge_admin -d lge -c "ALTER USER lge_admin WITH PASSWORD '$REST_PW';"
echo "alter_lge_admin_rc=$?"
docker exec "$DB" psql -U lge_admin -d lge -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='root') THEN CREATE ROLE root LOGIN PASSWORD '$OWNER_PW'; ELSE ALTER ROLE root WITH LOGIN PASSWORD '$OWNER_PW'; END IF; END \$\$;"
echo "root_role_rc=$?"
docker exec "$DB" psql -U lge_admin -d lge -tAc 'select 1' && echo PSQL_OK
curl -fsSL https://raw.githubusercontent.com/gochapachi/lge-pilot/staging/dashboard/schema-pg.sql -o /tmp/schema.sql
docker exec -i "$DB" psql -U lge_admin -d lge < /tmp/schema.sql > /tmp/schema_out.txt 2>&1
echo "schema_rc=$?"
docker exec "$DB" psql -U lge_admin -d lge -tAc 'select count(*) from leads'
echo "leads_count"
docker exec "$DB" psql -U lge_admin -d lge -tAc "select count(*) from information_schema.tables where table_schema='public'"
echo "tables_count"
curl -s -X POST -H "apikey: $EVO_KEY" -H "Content-Type: application/json" \
  "$EVO_URL/message/sendText/$EVO_INSTANCE" \
  -d "{\"number\":\"$OWNER_WA\",\"text\":\"LGE: root role = your password. Schema applied. Check pilot dashboards.\"}" -o /dev/null -w "wa=%{http_code}\n"
echo BOOT4_DONE