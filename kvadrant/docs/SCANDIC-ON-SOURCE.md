# Running Scandic on a from-source Twenty (custom-code dev)

How to get the **full Scandic environment — records + workflows + view/visual edits** — into a
**from-source** Twenty instance for writing custom code. Proven 2026-06-10. Hard-won; read the
gotchas before improvising.

## Why a DB copy, not the build scripts

The demo's Scandic environment lives in the **database**: custom objects/fields, every record, the
**workflows** (`workflow`/`workflowVersion` tables), and the **visual edits** (table columns, kanban
groupings, filters → `view`/`viewField`/`viewGroup`). A `pg_dump` → restore carries **all** of it.
The `kvadrant/build` scripts can recreate objects/fields/records but **cannot** recreate workflows or
saved view layouts — so for a faithful copy, duplicate the database. (The scripts are the fallback /
schema-as-code path and are now complete & version-robust — see `build/build_schema.py`.)

## Two different runtimes — don't conflate

| | Demo | Custom-code |
|---|---|---|
| Folder | `crm/twenty` | `twenty-custom` |
| Runs | prebuilt **image** `twentycrm/twenty:<TAG>` | **built from source** (`yarn start`) |
| For | clickable demo | writing custom code |

You can only move the **database** between them, and the database is **version-bound**. So every route
reduces to: get the data to a version, run code at that **same** version.

## The recipe

**1. Upgrade the demo to a released tag (the blessed upgrade path).**
Edit `packages/twenty-docker/.env` → `TAG=v2.9.0`, then `docker compose pull && docker compose up -d`.
The image runs the workspace `upgrade` automatically on boot. Verify: data/workflows/views intact and
`select distinct "executedByVersion" from core."upgradeMigration"` shows the new version.

**2. Snapshot the upgraded DB.**
```
docker exec -t twenty-db-1 pg_dump -U postgres -d default --no-owner --no-privileges --clean --if-exists | gzip > scandic.sql.gz
```

**3. Build the source env from the SAME release tag** (not `main`/dev-tip — that's an unreleased moving
target and the version won't match the data).
```
git clone <fork> twenty-custom && cd twenty-custom
git checkout -b kvadrant-baseline v2.9.0
yarn install
bash packages/twenty-utils/setup-dev-env.sh      # dev postgres/redis (separate 'twenty-dev' compose project)
```

**4. Restore the dump into the dev DB BEFORE the server's first boot.**
```
gunzip -c scandic.sql.gz | docker exec -i twenty-dev-db-1 psql -U postgres -d default -v ON_ERROR_STOP=0
```

**5. Apply the three required fixes (see Gotchas), then start:** `NX_TUI=false yarn start`
(front :3001, server :3000). Log in at http://localhost:3001.

## Gotchas — these caused every "An error occurred" we hit

1. **Version must match exactly.** v2.8.3 data into v2.10-dev source → workspace metadata inconsistent
   → error. Upgrade the demo to a *release* and build source from the *same* release tag.

2. **Subdomain must be `app`.** The restored workspace keeps the demo's random subdomain
   (e.g. `brilliant-purple-leopard`). The dev frontend resolves the workspace by the `app` subdomain
   (`getPublicWorkspaceDataByDomain`); a mismatch returns nothing → Apollo *"link chain completed
   without emitting a value"* → **"An error occurred"** on page load.
   ```
   update core.workspace set subdomain='app';   -- and activationStatus must be 'ACTIVE'
   ```

3. **`ENCRYPTION_KEY` must match the demo's.** The restored workspace's JWT **signing key** is encrypted
   with the demo's `ENCRYPTION_KEY`. A different key → *"No encryption key matches keyId … / No active
   signing key available to sign asymmetric token"* → **"An error occurred"** at **login**. Copy the
   demo's `ENCRYPTION_KEY` (from `twenty-docker/.env`) into `packages/twenty-server/.env`, restart.

4. **Port 3000 is shared.** The demo docker stack AND the source `yarn start` both bind :3000 — they
   fight. Stop the demo (`docker compose stop`) before running the source server, or they'll collide
   and the frontend may talk to the wrong backend.

After restore the original user passwords are unknown (and old tokens are dead — different
`APP_SECRET`), but password login works. Reset one:
```
node -e "require('./node_modules/bcrypt').hash('PASS',10).then(h=>process.stdout.write(h))"
update core."user" set "passwordHash"='<hash>' where email='demo@scandic-gm.dev';
```

## Debugging note

Server-side everything can read 200/healthy while the browser shows "An error occurred" — it's a
**frontend runtime** error. Get the **browser console** error first; don't spelunk the backend. Also:
`clientConfig` is REST `GET /client-config`, not GraphQL. `NX_TUI=false` makes `yarn start` write
readable logs (the default TUI hides them).
