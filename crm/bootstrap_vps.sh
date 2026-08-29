#!/bin/sh
# LGE VPS bootstrap (runs inside docker:cli service; fetched from this public repo)
# Rotates PG password, reads MinIO runtime creds, stores them in a PRIVATE gist, WA-notifies.
# Tokens arrive as env vars: GIST_TOKEN EVO_KEY EVO_URL EVO_INSTANCE OWNER_WA
set +e

OUT=/tmp/lge_bootstrap.log
{
  echo "=== docker ==="
  docker version --format '{{.Server.Version}}' || echo SOCKET_FAIL

  echo "=== containers ==="
  docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}'

  DB=$(docker ps --format '{{.Names}}' | grep -i db | head -1)
  MI=$(docker ps --format '{{.Names}}' | grep -i minio | head -1)
  echo "DB=$DB MI=$MI"

  NEWPW="Lge-$(date +%s)-x"
  echo "=== pg password reset ==="
  docker exec "$DB" psql -U lge_admin -d lge -c "ALTER USER lge_admin WITH PASSWORD '$NEWPW';"
  echo "alter_rc=$?"
  docker exec "$DB" psql -U lge_admin -d lge -tAc 'select 1' && echo PSQL_VERIFY_OK

  echo "=== minio runtime env ==="
  MU=$(docker exec "$MI" printenv MINIO_ROOT_USER)
  MP=$(docker exec "$MI" printenv MINIO_ROOT_PASSWORD)
  echo "MINIO user=$MU pass_len=${#MP}"

  echo "=== stash to private gist ==="
  BODY='{"public":false,"files":{"lge_creds.json":{"content":"PGPW:'"$NEWPW"' MIOU:'"$MU"' MIOP:'"$MP"'"}}}'
  RESP=$(curl -s -X POST -H "Authorization: token $GIST_TOKEN" \
    -H "Accept: application/vnd.github+json" https://api.github.com/gists -d "$BODY")
  echo "$RESP" | grep -o '"id": "[^"]*"' | head -1

  curl -s -X POST -H "apikey: $EVO_KEY" -H "Content-Type: application/json" \
    "$EVO_URL/message/sendText/$EVO_INSTANCE" \
    -d "{\"number\":\"$OWNER_WA\",\"text\":\"LGE bootstrap: PG password rotated; creds in private gist\"}" \
    -o /dev/null -w "wa_http=%{http_code}\n"

  echo BOOTSTRAP_DONE
} >> "$OUT" 2>&1