# Kvadrant CRM — Project Journal

> A custom-CRM delivery practice built on **Twenty** (open-source CRM). Kvadrant builds and
> operates bespoke CRMs for clients, hosted on the *client's own* EU cloud — no vendor lock-in.
>
> **Status (2026-06-03):** Foundation validated; a full **Scandic Group & Meeting** demo is built,
> seeded, and verified, running locally. Next: the production fork + first client engagement.

---

## 1. Vision & business model

Kvadrant is a Danish/EU commercial consultancy that historically avoided CRM work (dislike of
vendor relationships / lock-in). The thesis here flips that:

- Use **Twenty** (AGPL, self-hostable) as the CRM engine — software cost ≈ €0.
- Build a **bespoke CRM per client**, deployed on the **client's own Azure/AWS in the EU**.
- Charge for **implementation + managed services**, not licences.
- The pitch to EU enterprises: *"Your CRM, your servers, your data, in the EU — no vendor who can
  hike prices or get acquired."* Salesforce/Dynamics cannot offer that.
- The unbundling: take the commodity (CRM engine) for free, charge for the scarce thing
  (judgment + customization + trust). Positioning is **premium, not cheap**.

Many enterprises pay €100k+/yr for a CRM and use ~20% of it (companies, contacts, a pipeline,
some activities). That spend can shift from licence-rent to Kvadrant's expertise.

## 2. Licensing (AGPL-3.0)

Twenty is **AGPL-3.0**, which *explicitly permits* charging for software + services and
self-hosting on client infrastructure — fully compatible with this model. The only obligation
(§13) is offering source to *that client's own users*, which is trivial and reinforces the
no-lock-in pitch.

**The one constraint:** ~300 files are marked `/* @license Enterprise */` (Twenty's *commercial*
licence, **not** AGPL). Most are irrelevant (Twenty's own SaaS billing/usage/DNS/Cloudflare).
Three gated areas could be client asks:

| Gated feature | Why it matters | Plan |
|---|---|---|
| **SSO / SAML / OIDC** | Enterprise table-stakes | Google + Microsoft OAuth login **are free**; for SAML/OIDC reimplement or use self-hosted **Keycloak** (EU, no vendor — avoid Clerk/US-SaaS) |
| **Advanced RBAC + row-level permissions** | Granular access | Basic roles are free; build row-level ourselves if needed |
| **Audit / event logs** | Compliance (GDPR) | Build or licence if a client requires it |

Rule: **do not copy/edit the `@license Enterprise` files.** Reimplement or use external services.

## 3. Architecture decision — "fork-and-build-deeply"

Decided after weighing options against the business model:

- Maintain a **Kvadrant baseline fork** of Twenty = Twenty + our own vanilla **Service Desk,
  Marketing, and Pricing/CPQ** modules, built as **first-class core modules** (the way Twenty
  builds Opportunity/messaging/workflow) — because Twenty does **not** ship these.
- **Each client = a git branch off that baseline.** Per-client customization = commits. Deep core
  edits are fine and expected (premium bespoke work; frozen customized forks are normal in
  enterprise CRM, cf. MS Dynamics).
- Chosen **over** the Twenty "apps" SDK: apps have a customization *ceiling* (narrow surface), bad
  for a depth-selling shop. Apps reserved only for thin connectors/glue (Slack notifier, webhook
  ingest).
- External hosted services are fine (auth, email/SMS, search, doc-gen) — even Salesforce relies on
  them.

**Two things that still matter** (and *fit* a managed-services model rather than fight it):
1. **Security patches ≠ feature updates.** Even a frozen client fork needs upstream *security*
   fixes backported — a billable managed-service deliverable.
2. The **enterprise-licence line** above.

## 4. What Twenty gives out of the box

**26 standard objects.** Coverage is **Sales + Communication + Automation**, not a full suite:

| Area | Out of box? | Notes |
|---|---|---|
| Sales CRM | ✅ | Company, Person, Opportunity, Task, Note |
| Email + Calendar sync | ✅ | Gmail/Outlook two-way, threads, multi-account |
| Workflow automation | ✅ | Visual builder + custom-code "logic functions"; triggers on record change/cron/webhook |
| **Service / Support** | ❌ | No tickets/SLAs/inbox — *we build it* |
| **Marketing** | ❌ | No campaigns/forms/landing pages — *we build it* (public forms/pages fit neither core nor apps → external service) |

Stack: Nx monorepo (Yarn 4, Node 24.5). Backend `twenty-server` (NestJS + GraphQL + PostgreSQL +
Redis + BullMQ). Frontend `twenty-front` (React 18 + Vite + Jotai). Metadata-driven: custom
objects/fields are created at runtime (no migration), which is what made the demo build scriptable.

---

## 5. The Scandic Group & Meeting demo

**Prospect:** Scandic Hotels' Meetings, Groups & Events (MICE) business — corporate sales + group &
meeting sales (hotels) + CX/marketing follow-up. **Why they have no CRM:** Oracle OPERA Cloud has a
group/meeting module but it's ERP-like, not a commercial tool; they need bi-directional sync with
OPERA to avoid double-entry, and OPERA licences for ~400 staff are expensive.

**Concept:** one commercial thread (the **Enquiry**) running lead → tentative → definite → delivery
→ follow-up, three teams sharing it, mirrored to OPERA.

### Data model (built on the live instance, config-level — no code changes)

| Object | Origin | Notes |
|---|---|---|
| **Enquiry** | renamed Opportunity | The pipeline. 8 colored stages: Lead → Qualified → Proposal Sent → **Tentative** → **Definite** → Delivery → Completed → Follow-up. MICE fields: delegates, room nights, DDR, revenue split, event dates, hold/decision/cut-off dates, OPERA block code/confirmation/sync status, win-loss + competitor |
| **Account** | renamed Company | + segment, city, country |
| **Contact** | renamed Person | + contactRole (booker/EA/procurement/event-mgr/decision-maker) |
| **Hotel** | custom | city, country, brand, meeting m², capacity, bedrooms, sustainability cert, airport distance |
| **Meeting Room** | custom | → Hotel; m², capacity by setup (theatre/classroom/banquet/boardroom/reception), daylight, hire price |
| **Room Block** | custom | → Hotel, → Enquiry; rooms/night, nights, rate, cut-off, pickup, OPERA block id |
| **Quote** | custom | → Enquiry; version, total, DDR offered, valid-until, status |
| **Corporate Agreement** | custom | → Account; year, negotiated rate, room-night commitment/actualised, discount %, renewal, status |
| **Event Feedback** | custom | → Enquiry; NPS, comments, would-rebook |

**119 seeded records:** 14 accounts, 22 contacts, 8 hotels, 22 meeting rooms, 23 enquiries
(all 8 stages), 10 quotes, 8 room blocks, 6 corporate agreements, 6 event feedback. All
relationships verified at 100% coverage.

**Hero records** (built to demo depth):
- **Volvo Group AGM 2026** — Definite, Scandic Triangeln, 220 pax, 182 room nights, DDR 695, 1.22M
  SEK; accepted quote v2 (v1 declined), room block synced to OPERA (`BLK-2026-0481`), POC Anders Björklund.
- **Ericsson Global Kickoff 2026** — Completed, Helsinki, NPS 9 (full lifecycle).
- **Ericsson Leadership Forum Q3 2026** — Tentative, hold expiring, quote sent, competitor named.

**Demo caveat:** branding is **workspace name only** ("Scandic Group & Meeting"). The dark-red
accent colour is **not configurable** in this image (no `brandColor` field / picker) — it needs a
code change (real fork work), out of scope for a config-only demo.

**OPERA story (faked for demo, real shape):** OPERA exposes OHIP APIs. The demo shows the
`operaBlockCode` / `operaConfirmationNo` / `syncStatus` fields populated — pitch: *"the moment the
client signs, the block flows into OPERA, no double-entry."*

The full presenter walkthrough is in [`demo-data/NARRATIVE.md`](demo-data/NARRATIVE.md).

> **Enterprise capability map:** every limitation we hit (license-gated, fork-needed, native-with-workaround, UI/governance gaps) is catalogued in [`ENTERPRISE-LIMITATIONS.md`](ENTERPRISE-LIMITATIONS.md) — the reusable IP for scoping client deals.

### How to run it

Prereqs (already installed on Efe's Mac): Homebrew, **Colima** + docker CLI + docker-compose plugin.

```bash
# 1. start the container runtime (after a Mac reboot)
colima start

# 2. bring up Twenty (from the docker package dir)
cd twenty/packages/twenty-docker
docker compose up -d            # server + worker + postgres + redis
#   manage: docker compose stop|start|down [-v] ; logs: docker compose logs -f server

# 3. open the app
open http://localhost:3000
#   login: demo@scandic-gm.dev  /  ScandicDemo2026!   (local demo only)
#   open "Enquiries" → switch to the "By Stage" Kanban for the pipeline view
```

### How it was built (and how to re-run)

Scripts live in [`build/`](build/), data in [`demo-data/`](demo-data/). The build is **API-driven**
(reliable + re-runnable) — schema via Twenty's metadata API, data via REST:

| File | Purpose |
|---|---|
| `build/build_schema.py` | Creates all objects/fields/relations + colored SELECTs via the **metadata API** (idempotent) |
| `build/seed.py` | Seeds all records via **REST**, resolving name-refs → IDs in dependency order (throttled for the rate limit) |
| `build/fix_people.py` | Re-seeds contacts (phone-country-code fix) |
| `build/m.sh` | curl helper → `POST /metadata` |
| `build/add_columns.py` | Enriches TABLE/KANBAN **view columns** (surfaces business + relation fields, hides system noise) — generates SQL, pipe to psql |
| `demo-data/*.json` | The generated Scandic dataset (1 file per object) |
| `demo-data/NARRATIVE.md` | Presenter click-path |
| `build/rfp_intake.py` | **AI RFP Intake** wow-feature: paste RFP email → Claude extracts enquiry + recommends best-fit hotel → creates it live in Twenty + files the email as a Note on the Enquiry/Contact timeline + drafts a proposal email. Run `python3 build/rfp_intake.py` → http://localhost:8787. Needs `build/.env` (ANTHROPIC_API_KEY). Frame as the demo form of a production "forward RFPs to an inbox → auto-file" (core-fork work). |

> ⚠️ **Secrets:** `build/.apikey` (the API key) and `twenty/packages/twenty-docker/.env`
> (ENCRYPTION_KEY, DB password) **must never be committed** — `.gitignore` them before any push.
> The API key is also currently hard-coded in `build/m.sh` — scrub it before sharing.

### Lessons / gotchas (verified against this image)

- **Trust only ground truth (DB/REST), not agent self-reports.** A browser-automation agent falsely
  claimed the Enquiry rename succeeded; the DB proved it hadn't. Every claim here was DB/REST-verified.
- Auth lives on `POST /metadata`, **not** `/graphql`. GraphQL introspection is disabled; the running
  `latest` image may not match repo source — verify, don't assume.
- Rename a standard object's label via `updateOneObject` (labels only — `isLabelSyncedWithName` is
  rejected on standard objects). It's stored in `standardOverrides`; `nameSingular` is unchanged so
  REST endpoints stay (e.g. Enquiries still POST to `/rest/opportunities`).
- `role` is a reserved field name on Person → use `contactRole`.
- REST rate limit is **100 req / 60 s** → throttle (~0.7 s/req) + retry on 429.
- Phone `primaryPhoneCountryCode` must not be hard-coded — omit and let it infer.
- **Workflows with code steps need `LOGIC_FUNCTION_TYPE`.** Twenty ships 2 sample workflows ("Quick Lead", "Create company when adding a new person", both SYSTEM-created, ACTIVE). They contain CODE (logic-function) steps which are **disabled by default** in the prebuilt image → every run FAILS with *"Logic function transpilation is disabled."* Fix: add `LOGIC_FUNCTION_TYPE: ${LOGIC_FUNCTION_TYPE:-DISABLED}` to **both** the `server` AND `worker` environment blocks in `docker-compose.yml` (workflows execute on the worker), set `LOGIC_FUNCTION_TYPE=LOCAL` in `.env`, then `docker compose up -d server worker`. LOCAL uses esbuild + child-process (works in the standard image). Verified: a person.upserted now COMPLETES. "Create company…" logic = is-personal-email? → filter business → extract domain → **find company by domain** → attach or create. So it **dedupes by domain**, not name.
- **Standard fields can't be made required.** `updateOneField isNullable:false` on a standard composite field (e.g. person.`emails`) is silently ignored (returns isNullable:true, no error) and a no-email record still creates. Making a standard field mandatory is core-fork work. (RFP intake sidesteps this by always synthesizing an email.)
- **New custom fields don't appear as list-view columns automatically** — they land in the record page's "System" group and are absent from table/kanban views. Surface them by adding `core."viewField"` rows (`build/add_columns.py`); `applicationId` is NOT NULL (use the workspace's standard app id). **Direct `viewField`/DB edits bypass Twenty's cache** → after editing, `docker compose restart server` (Redis FLUSHALL alone isn't enough) to make changes render.

---

## 6. Repository layout

```
crm/
├── PROJECT.md            ← this file
├── build/                ← API build + seed tooling (secrets gitignored)
├── demo-data/            ← generated Scandic dataset + NARRATIVE.md
├── *.png                 ← demo screenshots (kanban, Volvo record, etc.)
└── twenty/               ← the Twenty clone (~1.5 GB, its own git repo → twentyhq/twenty)
```

`twenty/` is upstream's repo and is **not** part of this project's git. The future Kvadrant
baseline fork will be a separate repo (forked from `twentyhq/twenty`).

## 7. Status & next steps

**Done:** strategy + licensing analysis; local Twenty running; extension surface mapped; Scandic
demo built, seeded, verified (UI + data).

**Next:**
1. **Rehearse the demo** end-to-end before presenting (the one remaining demo risk).
2. Decide GitHub: a small **Kvadrant tooling repo** (this `build/` + `demo-data/`) vs. the
   **production fork** of Twenty. Scrub secrets first.
3. When real: stand up the **source dev environment** (Node 24.5 + Yarn 4) and start the baseline
   fork with the first core module (Service Desk / Pricing / Marketing).
4. For Scandic specifically: the OPERA/OHIP integration design, and the dark-red branding (code change).
```
