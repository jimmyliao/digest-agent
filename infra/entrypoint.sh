#!/bin/sh
set -e

mkdir -p /data

if [ -n "$LITESTREAM_GCS_BUCKET" ]; then
  echo "Litestream restore from gs://$LITESTREAM_GCS_BUCKET/digest-db"
  litestream restore -if-replica-exists -if-db-not-exists /data/digest.db
  exec litestream replicate -exec "node server.js"
else
  echo "LITESTREAM_GCS_BUCKET unset - running ephemeral (local dev mode)"
  exec node server.js
fi
