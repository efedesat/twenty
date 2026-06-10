#!/usr/bin/env bash
# Snapshot the entire Scandic Twenty database (schema + data + workflows) to a
# committed file. This is the source of truth for the demo environment — run it
# whenever the demo changes, then commit the resulting dump.
#
# Captures EVERYTHING Twenty stores: custom objects/fields, views, all records,
# and the UI-built workflows (which the build_*.py scripts cannot recreate).
#
# Usage:  kvadrant/build/db_dump.sh
# Requires: the docker stack to be up (colima start && docker compose up -d).
set -euo pipefail

DOCKER_DIR="$(cd "$(dirname "$0")/../../packages/twenty-docker" && pwd)"
OUT="$(cd "$(dirname "$0")/.." && pwd)/demo-data/scandic-db.sql.gz"

cd "$DOCKER_DIR"

echo "Dumping 'default' database from the db service..."
docker compose exec -T db \
  pg_dump -U postgres -d default --no-owner --no-privileges --clean --if-exists \
  | gzip > "$OUT"

echo "Wrote $(du -h "$OUT" | cut -f1) -> $OUT"
echo "Now commit it:  git add kvadrant/demo-data/scandic-db.sql.gz && git commit"
