#!/usr/bin/env bash
# Restore the committed Scandic database snapshot into a running Twenty stack.
# This recreates the FULL demo environment (objects, fields, views, records,
# workflows) on a fresh machine — no need to run build_schema/seed.
#
# Usage:  kvadrant/build/db_restore.sh
# Requires: the docker stack to be up. For a clean restore on a fresh machine,
# bring the stack up once so the db is healthy, then run this.
#
# NOTE: use the SAME image TAG the snapshot was taken on (see .env / compose).
# Restoring an old snapshot into a much newer image can trip schema migrations.
set -euo pipefail

DOCKER_DIR="$(cd "$(dirname "$0")/../../packages/twenty-docker" && pwd)"
DUMP="$(cd "$(dirname "$0")/.." && pwd)/demo-data/scandic-db.sql.gz"

[ -f "$DUMP" ] || { echo "No snapshot at $DUMP — run db_dump.sh on the source machine first."; exit 1; }

cd "$DOCKER_DIR"

echo "Restoring $DUMP into 'default' database..."
gunzip -c "$DUMP" | docker compose exec -T db psql -U postgres -d default -v ON_ERROR_STOP=0

echo "Restore complete. Restart the server so it picks up the restored state:"
echo "  docker compose restart server worker"
