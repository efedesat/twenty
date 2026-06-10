# TWENTY-OPERATIONS.md — operating the running Twenty image (living gotchas log)

The hard-won ins/outs of scripting and configuring the **prebuilt `twentycrm/twenty:latest`** image
used for the Scandic demo. **This is a living log** — point-in-time observations, some may age; verify
before relying, and **append what you learn** so the next agent doesn't repeat the mistake. Consolidated
from prior sessions' notes + the pricing-workflow build (2026-06).

> Golden rule: **GraphQL introspection is disabled and the running image can differ from `twenty/`
> source. Never trust an agent's self-report that something worked — verify via REST or the DB.**

## Auth & APIs
- **Auth lives on `POST /metadata`, not `/graphql`.** Headless flow: `getLoginTokenFromCredentials(email,
  password, origin)` → `getAuthTokensFromLoginToken(...)`, `origin="http://localhost:3000"`.
- **API keys are scoped to REST + metadata**, not the core `/graphql` the frontend uses. To call core
  GraphQL mutations (e.g. workflow internals) you need a **user access token** (mint via the login flow),
  not the API key. Demo API key is in `build/.apikey` (long-lived).
- **Schema = metadata API** (`POST /metadata`, Bearer): `createOneObject`, `createOneField`,
  `updateOneObject/Field`. **Data = REST** (`/rest/{namePlural}`, Bearer).
- **Authoritative field shapes: `GET /rest/open-api/core`.** The metadata `objects{ fields(paging:{...}) }`
  nested query is **unreliable — it truncates/returns partial field sets**. Don't trust it for
  completeness; use the OpenAPI spec or the DB.

## Objects & fields
- Creating objects then relations: **refresh the object cache between** (re-query objects) so new objects'
  ids are known before adding relation fields. (`build/build_schema.py` does this.)
- **Reserved field names** are rejected ("name is reserved; system will add Custom suffix"): `currency`
  (use `currencyCode`), `role` on Person (use `contactRole`), `type` (use e.g. `activityType`).
- **SELECT options:** colours must be set explicitly per option. **Updating a SELECT's options WIPES that
  field's `viewGroup` rows** → any Kanban grouped by it goes blank; rebuild the viewGroups after.
- **Field type is immutable** (`UpdateFieldInput` has no `type`). To change type: delete + recreate
  (capture values first, repopulate after).
- **Money fields** = `{ amountMicros, currencyCode }`. Plain rate fields are raw NUMBER ints. **Relations**
  are set via `<rel>Id` in REST bodies; in GET they may come back as `<rel>Id` or nested `{<rel>:{id}}`.
- **Renaming an object's label keeps `nameSingular`** → the REST endpoint is unchanged (renamed
  "Enquiry" still POSTs to `/rest/opportunities`).
- **Standard composite fields can't be made required** (`isNullable:false` on e.g. `person.emails` is
  silently ignored) — mandatory = fork work.

## Views / UI
- **New custom fields don't auto-appear as list columns.** Add `core."viewField"` rows (see
  `build/add_columns.py`, which generates SQL → pipe to psql). Use the workspace standard `applicationId`
  (`2f43416d-1f60-47bf-99c2-9abaf953172e`).
- **After direct `viewField`/DB edits, `docker compose restart server`.** A Redis FLUSHALL alone is NOT
  enough to make them render.
- **Brand/accent colour is NOT configurable** in this image (no `brandColor` field/picker) → needs a code
  change (real fork work). Demo branding = workspace name only.
- **A second pipeline on any custom object** is just a KANBAN view grouped by a SELECT `stage` + a
  CURRENCY value field (+ viewGroup rows per option). No fork needed.

## Workflows & logic functions (built the pricing flow on these)
- **Code steps need `LOGIC_FUNCTION_TYPE=LOCAL` on BOTH `server` and `worker`** (off by default → runs
  fail "Logic function transpilation is disabled"). Set in `twenty/packages/twenty-docker/.env` + both env
  blocks of `docker-compose.yml`; `docker compose up -d server worker`.
- **The Code step's function is a build-pipeline file**, stored under the server's
  `.local-storage/<ws>/<app>/source/<fnId>/src/index.ts` (+ built `.mjs`), referenced by
  `logicFunctionId`. The `core.logicFunction` table is **not REST-exposed** → **build Code-step workflows
  in the UI**, not by API/DB (workflow/workflowVersion themselves ARE REST objects, but hand-authoring
  steps + per-step `outputSchema` + the function file is brittle).
- **Manual single-record trigger does NOT expose the record's fields to the Code-step variable picker**
  on this image (source says it should). **Workaround: re-fetch the record via a Find Records step** and
  map from that. Trigger fields ARE available in Find-Records *filters* as `{{trigger.<field>}}` (e.g.
  `{{trigger.id}}`, `{{trigger.hotelId}}`).
- **Relation filters match by Id**: use field `<Relation> → Id`, operand **Is** (matching `→ Name` with
  CONTAINS against an id returns nothing).
- **Code-step inputs map to the whole record** — use the step's `.all` (or `.first`), NOT `.first.id`.
- **A Code step's output schema is generated by a Test run.** Enter sample JSON per param to produce a
  result, which exposes the output fields for downstream mapping. **Re-pasting code resets the test
  inputs** — re-enter them, as raw JSON values (not field names).
- Available step types here: MANUAL/DATABASE_EVENT triggers; FIND_RECORDS, CODE, CREATE_RECORD,
  UPDATE_RECORD, FILTER, IF_ELSE, FORM, HTTP_REQUEST, AI_AGENT, ITERATOR.

## Local stack
- **Colima + docker compose** (Colima chosen over Docker Desktop for licensing). Compose at
  `twenty/packages/twenty-docker/`. App at http://localhost:3000. After reboot: `colima start` first.
  DB: `default`, user `postgres` (password in that `.env`); metadata tables in the `core` schema,
  workspace data in `workspace_<id>`.
- **REST rate limit ≈ 100 req / 60s** → throttle scripts (~0.7s/req; back off 20s on HTTP 429).
- Hand-inserting a `user` row needs a UUID whose version nibble is 1–5, or auth cache returns
  USER_NOT_FOUND.

## Enterprise-gated (cost decisions, not bugs)
- **Row-level / BU data isolation** is `@license Enterprise`-gated → license or reimplement in fork.
- **SSO/SAML/OIDC login** is enterprise-gated (mailbox/calendar connection itself is free, per-user OAuth).
- Org-chart tree visualisation & cross-hierarchy roll-ups = fork work (relations themselves are native).

## Known modelling caveat (Scandic)
- **Corporate Agreement has a negotiated rate but no currency** → a SEK rate gets applied to EUR/DKK/NOK
  hotels. Add `currencyCode` (and a guard) when the pricing data model is finalised — see
  `PRICING-DATA-MODEL.md`.
