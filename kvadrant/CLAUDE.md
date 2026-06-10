# CLAUDE.md — Kvadrant CRM tooling (Scandic demo on Twenty)

Read this first. It's the lean entry point; the detail lives in the linked docs — follow the pointer
rather than guessing.

## What this is
The **`kvadrant/` layer** of the Kvadrant baseline fork of **Twenty** (AGPL CRM) — build scripts, seed
data, docs, and the Scandic demo snapshot. It lives *inside* the fork (`github.com/efedesat/twenty`),
not in a separate repo. Business model: bespoke CRM per client on the client's own EU cloud,
**fork-and-build-deeply, one git branch per client** — so this layer travels with every client branch.

- **Single repo, single clone.** Twenty source is in `../packages/`; everything Kvadrant-specific is
  here under `kvadrant/`. See **`SETUP.md`** for clone → run → restore.
- **The Scandic demo's source of truth is the DB snapshot** `demo-data/scandic-db.sql.gz` (restored via
  `build/db_restore.sh`) — it captures objects, records, *and* workflows. The build scripts evolve the
  schema; they don't bootstrap a fresh machine.
- The demo runs on the **prebuilt `twentycrm/twenty:latest` image** (set by `TAG` in the docker `.env`),
  which may lag the `../packages/` source — verify behaviour against what's actually running.

## Client source documents (read before designing)
- **`scandic-source/`** — drop Scandic briefs, specs, and reference material here. **Git-ignored** (never
  committed — client/proprietary). If present, **read everything in it first** to ground CRM design
  decisions in the client's actual requirements. Empty/absent on a fresh clone.

## Read these for detail (don't duplicate them here)
- **`SETUP.md`** — clone, run the stack, restore the Scandic snapshot, re-snapshot when it changes.
- **`docs/SCANDIC-ON-SOURCE.md`** — how to run the full Scandic env on a from-source instance (DB copy + the 4 gotchas).
- **`docs/PROJECT.md`** — canonical: vision, licensing, architecture, the demo, status.
- **`docs/TWENTY-OPERATIONS.md`** — the living **gotchas / do's & don'ts** log for the running image.
  Read before scripting metadata, seeding, views, or workflows. Add to it when you learn something.
- **`build/GENERATE_QUOTE_WORKFLOW.md`** — the no-AI pricing "Generate Quote" + "Approve Quote"
  workflows (built & verified).
- **`docs/PRICING-DATA-MODEL.md`** — OPEN design thread (where money fields live). Not settled; UX first.
- **`docs/ENTERPRISE-LIMITATIONS.md`**, **`docs/BASELINE.md`** — enterprise-fit findings and backlog.

## Top do's & don'ts (full list in TWENTY-OPERATIONS.md)
- **Verify against the running image, never trust self-reports** — GraphQL introspection is disabled
  and the image may differ from `twenty/` source. Check via REST (`/rest/open-api/core` for field
  shapes) or DB.
- **Restart the server after direct `viewField`/DB edits** (`docker compose restart server`) — a Redis
  flush alone is not enough.
- **Reserved field names** get rejected: `currency` (use `currencyCode`), `role` on Person (use
  `contactRole`), `type` (use e.g. `activityType`).
- **REST rate limit ≈ 100/60s** — throttle scripts (~0.7s/req).
- **Workflows with Code steps** need `LOGIC_FUNCTION_TYPE=LOCAL` on **both** server and worker; the
  Code step's function is a build-pipeline file (not REST-creatable) → build Code-step workflows in
  the **UI**, not by API/DB.
- **Field types are immutable** — to change, delete + recreate (capture/restore values).

## Where things run / live
- Stack: **Colima + docker compose** at `../packages/twenty-docker/` → http://localhost:3000.
  After a reboot: `colima start`, then `docker compose up -d`.
- Env snapshot: `demo-data/scandic-db.sql.gz` ← `build/db_dump.sh`, restored by `build/db_restore.sh`.
- Build scripts (schema evolution, not bootstrap): `build/build_schema.py` (objects/fields),
  `build/seed.py` (records), `build/add_columns.py` (view columns → pipe to psql),
  `build/quote_engine.py` (no-AI pricing CLI/reference), `build/rfp_intake.py` (AI RFP intake demo).
  API key in `build/.apikey`.
- Generated dataset + presenter path: `demo-data/` (incl. `NARRATIVE.md`).

## Persistent agent memory
Cross-session notes also live in `~/.claude/projects/<this>/memory/` (personal, not committed). The
**committed** source of truth for shared/agent knowledge is this file + `TWENTY-OPERATIONS.md` — prefer
adding durable, team-relevant findings there so they travel with each client fork.
