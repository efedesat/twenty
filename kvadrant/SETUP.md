# Setup — Kvadrant CRM (Scandic demo on Twenty)

One repo, one clone. This is the **Kvadrant baseline fork** of Twenty; everything Kvadrant-specific
lives under `kvadrant/`. Each client is a branch off this baseline.

## Prerequisites
- Docker (via **Colima** on macOS, or Docker Desktop on Windows/Linux)
- Python 3 (for the build/seed scripts — only needed if rebuilding the demo from scratch)

## 1. Clone

```bash
git clone https://github.com/efedesat/twenty.git
cd twenty
```

That's it — no second repo. The old `crm-tooling` repo has been folded into `kvadrant/`.

## 2. Start the stack

```bash
# macOS:
colima start
cd packages/twenty-docker
cp .env.example .env        # then fill in the secrets (see below)
docker compose up -d        # http://localhost:3000
```

Wait until `docker compose ps` shows `server` healthy, then open http://localhost:3000.

## 3. Load the Scandic environment

The demo environment (custom objects, fields, views, **all records, and the workflows**) is captured
as a full database snapshot — **not** rebuilt from scripts. This is the source of truth for the demo.

```bash
# from the repo root, with the stack up:
kvadrant/build/db_restore.sh
docker compose -f packages/twenty-docker/docker-compose.yml restart server worker
```

Restoring the snapshot is the *only* step needed — you do **not** need to run `build_schema.py` /
`seed.py` on a fresh machine. Those scripts are for *evolving* the schema, not bootstrapping.

> **Snapshot ↔ image TAG:** restore a snapshot into the same Twenty image `TAG` it was taken on
> (see `packages/twenty-docker/.env`). A much newer image can trip schema migrations.

## 4. When the demo changes — re-snapshot

After you change the demo (new objects, records, or workflows), capture it and commit:

```bash
kvadrant/build/db_dump.sh
git add kvadrant/demo-data/scandic-db.sql.gz && git commit -m "Update Scandic snapshot"
git push
```

Teammates pull and re-run `db_restore.sh` to get the new state. This is how the demo stays in sync
across laptops.

## Layout

```
twenty/                          github.com/efedesat/twenty (Kvadrant baseline)
├── packages/                    upstream Twenty + Kvadrant first-class modules
├── packages/twenty-docker/      the local stack (docker compose) + .env
└── kvadrant/                    everything Kvadrant-specific
    ├── build/                   build_schema.py, seed.py, db_dump/restore.sh, quote_engine.py, …
    ├── demo-data/               JSON seed + scandic-db.sql.gz (the env snapshot)
    ├── docs/                    PROJECT.md, TWENTY-OPERATIONS.md, BASELINE.md, …
    ├── CLAUDE.md                agent entry point for the Kvadrant layer
    └── SETUP.md                 this file
```

## Secrets

- `packages/twenty-docker/.env` — stack secrets (DB password, `APP_SECRET`, OAuth keys). **Gitignored.**
- `kvadrant/build/.apikey` — a Twenty REST API key. It's **per-instance** (tied to a workspace +
  `APP_SECRET`); the committed value works only against the machine it was minted on. Generate a new
  one in the UI (Settings → API & Webhooks) if the build scripts return 401.
- `kvadrant/build/.env` — `ANTHROPIC_API_KEY` for the RFP-intake demo (`rfp_intake.py`). Blank by
  default; paste a key to use it.

For a fresh machine using the **snapshot restore** path, you don't need a working `.apikey` — the
records come from the dump, not the API.
