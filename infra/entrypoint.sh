#!/bin/sh
set -e

mkdir -p /data

# Detect runtime: prefer bun (production image) but fall back to node so
# this script also works locally via `npm start` / plain node.
if command -v bun >/dev/null 2>&1; then
  RUNTIME=bun
else
  RUNTIME=node
fi

if [ -n "$LITESTREAM_GCS_BUCKET" ]; then
  echo "Litestream restore from gs://$LITESTREAM_GCS_BUCKET/digest-db (runtime=$RUNTIME)"
  litestream restore -if-replica-exists -if-db-not-exists /data/digest.db
  exec litestream replicate -exec "$RUNTIME server.js"
else
  echo "LITESTREAM_GCS_BUCKET unset - running ephemeral (local dev mode, runtime=$RUNTIME)"
  exec "$RUNTIME" server.js
fi
