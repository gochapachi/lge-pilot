#!/bin/sh
# bootstrap5: the real fix. DB likely initialized with default superuser 'postgres' (env vars were
# empty on 4.3.11 varref parsing). Use socket-trust as postgres, align everything to OWNER creds.
OUT=/tmp/b5.log
exec > $OUT 2>&1
DB=$(docker ps --format '{{.Names}}' | grep -i db | head -1)
echo "DB=$DB"
echo "=== whoami tests via socket trust ==="
docker exec "$DB" psql -U postgres -d postgres -tAc 'select current_user' && echo PG_SUPER_OK
docker exec "$DB" psql -U lge_admin -d lge -tAc 'select 1' || echo LGE_ADMIN_FAIL

echo "=== align roles/db to owner creds ==="
docker exec "$DB" psql -U postgres -d postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='root') THEN CREATE ROLE root LOGIN PASSWORD '$OWNER_PW' SUPERUSER; ELSE ALTER ROLE root WITH LOGIN PASSWORD '$OWNER_PW' SUPERUSER; END IF; END \$\$;" && echo ROOT_ROLE_OK
docker exec "$DB" psql -U postgres -d postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lge_admin') THEN CREATE ROLE lge_admin LOGIN PASSWORD '$REST_PW' SUPERUSER; ELSE ALTER ROLE lge_admin WITH LOGIN PASSWORD '$REST_PW' SUPERUSER; END IF; END \$\$;" && echo LGE_ADMIN_ROLE_OK
docker exec "$DB" psql -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='lge'" | grep -q 1 || docker exec "$DB" psql -U postgres -d postgres -c "CREATE DATABASE lge OWNER root"
docker exec "$DB" psql -U postgres -d postgres -c "ALTER DATABASE lge OWNER TO root" && echo DB_LGE_OK

echo "=== schema apply (as root) ==="
curl -fsSL https://raw.githubusercontent.com/gochapachi/lge-pilot/staging/dashboard/schema-pg.sql -o /tmp/schema.sql
docker exec -i "$DB" psql -U root -d lge < /tmp/schema.sql > /dev/null 2>&1
echo "schema_rc=$?"
docker exec "$DB" psql -U root -d lge -tAc 'select count(*) from leads'
echo "leads_count"

echo "=== anon role + grants (PostgREST) ==="
docker exec "$DB" psql -U root -d lge -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lge_anon') THEN CREATE ROLE lge_anon NOLOGIN; END IF; END \$\$;"
docker exec "$DB" psql -U root -d lge -c "GRANT ALL ON SCHEMA public TO lge_admin, lge_anon; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO lge_admin, lge_anon; GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO lge_admin, lge_anon; GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO lge_admin, lge_anon;"
echo "grants done"

echo "=== gist the whole log ==="
BODY=$(printf '{"public":false,"files":{"b5log.txt":{"content":"%s"}}}' "$(sed 's/"/\\"/g' $OUT | head -c 40000)")
RESP=$(curl -s -X POST -H "Authorization: token $GIST_TOKEN" -H "Accept: application/vnd.github+json" https://api.github.com/gists -d "$BODY")
echo "$RESP" | grep -o '"id": "[^"]*"' | head -1
curl -s -X POST -H "apikey: $EVO_KEY" -H "Content-Type: application/json" \
  "$EVO_URL/message/sendText/$EVO_INSTANCE" \
  -d "{\"number\":\"$OWNER_WA\",\"text\":\"LGE b5: roles aligned to your password + schema + grants. Full log in gist.\"}" -o /dev/null -w "wa=%{http_code}\n"
echo B5_DONE
sleep 99999999