#!/bin/sh
# LGE bootstrap2 (inside VPS, fetched from public repo)
# Generates PW in-VPS -> rotates lge_admin -> applies schema-pg.sql -> stashes PW in private gist.
# Env provided by runner: GIST_TOKEN EVO_KEY EVO_URL EVO_INSTANCE OWNER_WA
set +e
DB=$(docker ps --format '{{.Names}}' | grep -i db | head -1)
echo "DB=$DB"

NEWPW="Lge$(head -c9 /dev/urandom | base64 | tr -d '/+=' )x"
docker exec "$DB" psql -U lge_admin -d lge -c "ALTER USER lge_admin WITH PASSWORD '$NEWPW';" > /tmp/alter.log 2>&1
echo "alter_rc=$?"
cat /tmp/alter.log 2>/dev/null

docker exec "$DB" psql -U lge_admin -d lge -tAc 'select 1' > /tmp/verify.txt 2>&1
echo "verify_rc=$? out=$(cat /tmp/verify.txt | head -1)"

# apply full schema via stdin pipe
curl -fsSL https://raw.githubusercontent.com/gochapachi/lge-pilot/staging/dashboard/schema-pg.sql -o /tmp/schema.sql
docker exec -i "$DB" psql -U lge_admin -d lge < /tmp/schema.sql > /tmp/schema_out.txt 2>&1
echo "schema_rc=$?"
grep -ci error /tmp/schema_out.txt | head -1
docker exec "$DB" psql -U lge_admin -d lge -tAc 'select count(*) from leads' > /tmp/leads.txt 2>&1
echo "leads_count=$(cat /tmp/leads.txt)"

BODY='{"public":false,"files":{"pgpw.txt":{"content":"'"$NEWPW"'"}}}'
RESP=$(curl -s -X POST -H "Authorization: token $GIST_TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/gists -d "$BODY")
GID=$(echo "$RESP" | grep -o '"id": "[^"]*"' | head -1)
echo "gist_line=$GID"
GID_CLEAN=$(echo "$GID" | sed 's/.*"\(.*\)"/\1/')
curl -s -X POST -H "apikey: $EVO_KEY" -H "Content-Type: application/json" \
  "$EVO_URL/message/sendText/$EVO_INSTANCE" \
  -d "{\"number\":\"$OWNER_WA\",\"text\":\"LGE: PG rotated + schema applied. pw in gist $GID_CLEAN\"}" \
  -o /dev/null -w "wa=%{http_code}\n"
echo BOOT2_DONE