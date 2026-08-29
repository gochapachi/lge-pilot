#!/bin/sh
# LGE bootstrap3 (runs inside VPS)
# 1. rotate PW once  2. apply schema  3. gist the PW  4. WA notify  5. sleep forever (no restart loops)
DB=$(docker ps --format '{{.Names}}' | grep -i db | head -1)
echo "DB=$DB"

NEWPW="Lge$(head -c9 /dev/urandom | base64 | tr -d '/+=')z"
docker exec "$DB" psql -U lge_admin -d lge -c "ALTER USER lge_admin WITH PASSWORD '$NEWPW';"
echo "alter_rc=$?"
docker exec "$DB" psql -U lge_admin -d lge -tAc 'select 1' && echo PSQL_OK

curl -fsSL https://raw.githubusercontent.com/gochapachi/lge-pilot/staging/dashboard/schema-pg.sql -o /tmp/schema.sql
docker exec -i "$DB" psql -U lge_admin -d lge < /tmp/schema.sql > /tmp/schema_out.txt 2>&1
echo "schema_rc=$?"
docker exec "$DB" psql -U lge_admin -d lge -tAc 'select count(*) from leads'
echo "leads_count_above"

BODY='{"public":false,"files":{"pgpw.txt":{"content":"'"$NEWPW"'"}}}'
RESP=$(curl -s -X POST -H "Authorization: token $GIST_TOKEN" -H "Accept: application/vnd.github+json" https://api.github.com/gists -d "$BODY")
echo "$RESP" | grep -o '"id": "[^"]*"' | head -1

curl -s -X POST -H "apikey: $EVO_KEY" -H "Content-Type: application/json" \
  "$EVO_URL/message/sendText/$EVO_INSTANCE" \
  -d "{\"number\":\"$OWNER_WA\",\"text\":\"LGE FINAL: pg rotated once + schema. pw in newest gist\"}" \
  -o /dev/null -w "wa=%{http_code}\n"

echo "ROTATE_COMPLETE — sleeping to prevent restart re-rotation"
sleep 99999999