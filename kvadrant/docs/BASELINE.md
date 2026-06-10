# Kvadrant CRM — Baseline Design

> What we change in `efedesat/twenty` before any client work begins.
> Everything here goes on `main`. Client branches pull from main and add their vertical specifics.
>
> **Status:** Design / not yet built. Companion to `ENTERPRISE-LIMITATIONS.md`.

---

## Why a baseline exists

Twenty out of the box is a product for individuals and small teams. Every European enterprise
client we take on will hit the same set of gaps — not because the data layer is wrong (it's
solid), but because the product hasn't built the *governance and presentation* layer that
organisations need. That layer is what the baseline is.

Building it once on `main` means:
- No client pays for the same work twice.
- Scandic, the next client, and the one after that all start from the same place.
- When upstream Twenty ships a security patch, we backport once, all clients benefit.

The baseline does **not** include vertical objects (hotels, tickets, products) — those go on
client branches. It does include the infrastructure those verticals sit on.

---

## Change areas

### 1. Brand colour configuration

**The gap:** Workspace branding is name + logo only. The accent colour is hardcoded in the
frontend. Every client we show this to will ask why it's the same purple.

**What we build:**
- A `brandColor` field (hex string) on the Workspace entity.
- A workspace admin settings page section: "Branding" — logo, name, colour picker.
- On workspace load, the frontend injects `--brand-color` (and derived tokens:
  `--brand-color-light`, `--brand-color-dark`) as CSS custom properties on `:root`.
- All existing accent usages in the design system already reference the brand colour token;
  we only need to make it dynamic.

**Where in the code:**
- `packages/twenty-server/src/engine/core-modules/workspace/workspace.entity.ts` — add field
- `packages/twenty-server/src/engine/core-modules/workspace/workspace.resolver.ts` — expose
- `packages/twenty-front/src/modules/workspace/` — branding settings form
- `packages/twenty-front/src/app/AppThemeProvider.tsx` (or equivalent) — inject CSS vars on load

**Scope:** Small. The design-system plumbing already uses variables; we're making the source
dynamic. One afternoon of work.

---

### 2. Required standard fields

**The gap:** `updateOneField isNullable: false` on a standard composite field (e.g.
`person.emails`) is silently ignored — the server returns `isNullable: true`, no error, and a
no-email record still saves. Every enterprise will have mandatory-field requirements.

**What we build:**
- Remove the guard that prevents `isNullable` from being mutated on standard fields.
- Make the server enforce `NOT NULL` validation at the create/update level for fields marked
  `isNullable: false`, same as it does for custom fields.
- Make the frontend form show the field as required (red asterisk, block submit) when the
  metadata says `isNullable: false` — this probably already works for custom fields; it needs
  to also work for standard ones.

**Where in the code:**
- `packages/twenty-server/src/engine/metadata-modules/field-metadata/` — remove the guard
- `packages/twenty-server/src/engine/api/graphql/` — validation middleware
- `packages/twenty-front/src/modules/object-record/record-field/` — form required logic

**Scope:** Small–medium. The mechanism exists for custom fields; we're extending it to standard
ones and removing the bailout.

---

### 3. Allowed currency list

**The gap:** The currency picker on CURRENCY fields shows all ~170 ISO 4217 currencies.
For a European enterprise this is noise and a data-quality risk (a rep picks USD by accident
on a SEK deal).

**What we build:**
- A `allowedCurrencyCodes` field (string array) on the Workspace entity. Empty = all currencies
  (backward compatible default).
- The workspace admin settings page: a multi-select for currencies.
- The frontend currency picker component reads the workspace config and filters its option list.
  If the workspace has no list set, it shows all currencies (today's behaviour).

**Where in the code:**
- `packages/twenty-server/src/engine/core-modules/workspace/workspace.entity.ts` — add field
- `packages/twenty-front/src/modules/object-record/record-field/types/field-currency/` — picker
- Workspace settings form — same "Branding" or a new "Localisation" section

**Scope:** Small. Piggybacking on the workspace entity work from §1.

---

### 4. Channel governance

**The gap:** Email and calendar sync settings — `visibility` (SHARE_EVERYTHING vs METADATA),
`isContactAutoCreationEnabled`, `contactAutoCreationPolicy`, `excludeNonProfessionalEmails`,
`isSyncEnabled` — are per-user, code-defaulted, and editable by anyone. There is no
workspace-level policy and no way for an admin to lock or set org defaults.

For a 400-person enterprise this means: without admin control, one rep sets their calendar
to METADATA and their deals disappear from reporting; another auto-creates contacts from every
email thread and pollutes the database.

**What we build:**

**4a — WorkspaceChannelPolicy entity:**
A new workspace-scoped config object (admin-only) that stores:
```
visibility:                  SHARE_EVERYTHING | METADATA
isContactAutoCreationEnabled: boolean
contactAutoCreationPolicy:   CREATION_AND_UPDATE | CREATION_ONLY
excludeNonProfessionalEmails: boolean
isSyncEnabled:               boolean
```
Plus a `lockSettings: boolean` flag. When `lockSettings: true`, the user-facing settings UI
hides or disables the controls.

**4b — Apply policy on channel creation:**
When a user connects their Google/Microsoft account and a `calendarChannel` / `messageChannel`
row is created, read the workspace policy and apply it. The user's manual choice in the connect
flow is overridden if a policy exists.

**4c — Drift correction job:**
A cron logic function (runs nightly or hourly) that queries all `calendarChannel` and
`messageChannel` rows and resets any that have drifted from the policy. This is the lightweight
path that doesn't require locking the UI.

**4d — Role-keyed policy (phase 2):**
An extension of the policy that maps workspace member roles to different policies. E.g.:
- `Sales Rep` → SHARE_EVERYTHING, contacts auto-created
- `Commercial / Pricing / Marketing` → METADATA, contacts not auto-created

This uses the workspace member `role` field as the key. The policy entity grows a `roleOverrides`
JSON column.

**Where in the code:**
- New entity: `packages/twenty-server/src/engine/core-modules/workspace-channel-policy/`
- Hook: `packages/twenty-server/src/modules/messaging/message-channel/` — on channel create
- Hook: `packages/twenty-server/src/modules/calendar/calendar-channel/` — on channel create
- Cron job: new logic function or NestJS scheduler in the messaging/calendar modules
- Admin settings UI: `packages/twenty-front/src/modules/settings/` — new "Sync Policy" page

**Note on the REST gap:** `MessageChannel` / `CalendarChannel` / `ConnectedAccount` are NOT
in the public REST API — only `WorkspaceMember` is. The drift-correction job must use the
internal TypeORM repositories (not the public REST/GraphQL surface).

**Scope:** Large. This is the most commercially valuable item — and the most work.
Phase 1 (policy entity + apply on create + drift cron) is a solid deliverable. Phase 2
(role-keyed) is a follow-on.

---

### 5. Unified Activity model

**The gap:** Twenty has Note and Task as native activity primitives. They surface in the
Timeline widget via hardcoded `note`/`task`/`noteTarget`/`taskTarget` queries. A custom
`Activity` object (site visits, calls, ad-hoc touchpoints) does NOT appear in any related
record's timeline — it only appears on itself.

The goal: one `Activity` object, with a type field (Call / Site Visit / Email / Meeting /
Custom), that appears in the timeline of every related record (Account, Contact, Enquiry, etc.)
exactly as Tasks and Notes do today.

**What we build:**

**5a — Activity as a baseline standard object:**
Rather than making each client create it via the metadata API, we ship `Activity` as a
first-class standard object in the baseline, alongside Note and Task. Fields:
- `activityType` (SELECT: Call, Site Visit, Meeting, Email, Custom)
- `subject` (TEXT)
- `happenedAt` (DATE_TIME)
- `duration` (NUMBER, minutes)
- `direction` (SELECT: Inbound, Outbound)
- `outcome` (TEXT)
- `source` (SELECT: Manual, Calendar Sync, Call Recording, Email Sync)
- Direct MANY_TO_ONE relations to Company, Person, Opportunity (the three standard core objects)
  — clients add more relations on their branch (e.g., Hotel for Scandic)

Making it a standard object means it participates in the standard object symmetry — named
chips, proper record pages, timeline wiring — without frontend fork work.

**5b — Timeline propagation fork:**
`packages/twenty-server/src/modules/timeline/standard-objects/timeline-activity.service.ts`
is hardcoded to note/task/noteTarget/taskTarget. Fork this service to also query the Activity
object via its direct MANY_TO_ONE relations. The query pattern is the same as for Task —
find all Activities where `companyId = X` (or `personId`, `opportunityId`) and include them
in the timeline response.

This is a bounded, locatable fork: one service file. Re-applying it on upstream merges is
straightforward — the file has a clear responsibility and the upstream hasn't been changing it
frequently.

**Where in the code:**
- New standard object definition: `packages/twenty-server/src/modules/activity/` (or similar,
  mirroring `packages/twenty-server/src/modules/note/`)
- Timeline fork: `packages/twenty-server/src/modules/timeline/standard-objects/timeline-activity.service.ts`
- Standard object registration (wherever Note and Task are registered)

**Scope:** Medium. The data model is well-understood from the Scandic prototype. The timeline
fork is small but needs to be maintained on upgrades — document it clearly.

---

### 6. Calendar widget — manual events and click-through

**The gap:** The calendar tab on Account/Contact/Opportunity records is a read-only sync
visualisation. Manually-created `CalendarEvent` records (not coming from a connected Google/365
account) render as "Not shared" grey blocks — no title, not clickable — because the visibility
calculation requires a `calendarChannel` with `visibility = SHARE_EVERYTHING`. Manual events
have no channel, so they always resolve to METADATA → hidden.

Additionally, there is no click-through from a calendar event to the related CRM record (e.g.,
the Enquiry it mirrors).

**What we build:**

**6a — Manual events as first-class calendar entries:**
Fork the visibility calculation in
`packages/twenty-server/src/modules/calendar/timeline-calendar-event/timeline-calendar-event.service.ts`
to treat manually-created CalendarEvents (no `calendarChannelEventAssociation`) as
SHARE_EVERYTHING by default. This is a policy decision: manual events were created intentionally
by a CRM user, not synced from a private inbox — they should be visible.

A workspace toggle (via the channel governance settings, §4): `manualEventsVisibility:
SHARE_EVERYTHING | METADATA`. Default: SHARE_EVERYTHING.

**6b — Relation chip on CalendarEvent:**
`CalendarEvent` has a hardcoded record page (no FIELDS_WIDGET view, so config-level relation
chips can't be surfaced). Add a `relatedRecord` polymorphic field (or direct relation fields
for the standard objects — Company, Person, Opportunity) to the CalendarEvent entity.
Surface this on the calendar event detail / tooltip.

**6c — Click-through from calendar:**
The calendar widget frontend needs a click handler on event tiles that navigates to the related
CRM record. Today clicking does nothing for manual events. With the relation field from 6b,
the tile can resolve the target and push the router.

**Where in the code:**
- `packages/twenty-server/src/modules/calendar/timeline-calendar-event/timeline-calendar-event.service.ts` — visibility fork
- `packages/twenty-server/src/modules/calendar/standard-objects/calendar-event.entity.ts` — add relation fields
- `packages/twenty-front/src/modules/activities/calendar/components/` — click handler + relation chip render

**Scope:** Large. This is the most significant frontend fork, and the one most likely to
conflict with upstream changes. The backend side (visibility calc) is small and locatable;
the frontend side (click-through, tile render) touches the calendar component tree.
Prioritise 6a (visibility) first — it delivers value with a small, locatable change.
6b and 6c are the UX-completion step.

---

### 7. Account hierarchy visualisation

**The gap:** The data layer for account hierarchy works natively — self-referential
MANY_TO_ONE relations support arbitrary depth (global → regional → local → subsidiary), in
both directions. The presentation is a flat relation chip + related-records list, which doesn't
communicate the structure to a key account manager.

**What we build:**
A `HierarchyWidget` frontend component that:
- Reads the Company object's self-referential relation metadata to identify the parent/child
  fields (generic — it works for any object with a self-referential relation).
- Renders a collapsed tree: current node + parent chain upward + immediate children downward.
  Clicking a node navigates to that record.
- Registered as a new page widget type (alongside the existing FIELDS_WIDGET and relation
  list widgets) so it can be placed on the Company record page via config.

A roll-up aggregation field (e.g. "Total Pipeline (all subsidiaries)") is out of scope for
the baseline — it requires recursive SQL and a dedicated aggregate service. Log it as a
follow-on.

**Where in the code:**
- `packages/twenty-front/src/modules/object-record/record-show/` — new widget component
- `packages/twenty-front/src/modules/object-record/record-show/record-show-right-drawer-fields.component.tsx`
  (or equivalent) — register the widget type
- The widget uses the existing GraphQL/REST to walk the relation chain; no server changes needed.

**Scope:** Medium. Pure frontend. The data is already there via relation queries; this is
rendering work. The recursive data fetch (parent chain) needs care for depth limits.

---

### 8. Currency framework

**The gap:** Twenty's CURRENCY composite field stores `{amountMicros, currencyCode}` correctly
for a single deal — but there is no concept of a workspace base currency, no exchange rate
table, and no way to aggregate amounts across currencies for reporting. A pipeline of SEK, NOK,
DKK and EUR deals cannot be summed without conversion.

**Design decision — wrap, don't replace:**
The composite storage is correct (local currency + amount is the right unit of truth per record)
and ripping it out would break Twenty internals. Instead, build a framework on top:

- `WorkspaceCurrencySettings` — base currency (e.g. EUR), update frequency (daily/manual),
  rate source (ECB free API for EUR cross-rates; fallback to manual entry).
- `ExchangeRate` standard object — `fromCurrency`, `toCurrency`, `rate`, `effectiveDate`.
  A daily cron syncs from ECB (or configurable source). Rates are snapshotted, not live —
  so a deal's converted value is stable unless explicitly refreshed.
- `amountBase` computed field — added by the framework to every CURRENCY field on every object.
  Stored as NUMBER (base currency units). Auto-calculated by a trigger on record create/update:
  reads `amountMicros + currencyCode`, looks up today's `ExchangeRate`, writes `amountBase`.
  Displayed as read-only in the UI, labelled `Amount (EUR)` or whatever the base is.
- Currency picker (§3) becomes: show `allowedCurrencyCodes` list from workspace settings.

**What the framework unlocks:**
- Reporting and dashboard aggregation work across currencies (sum `amountBase`).
- "Amount (Local)" + "Amount (EUR)" pattern on every object — no per-client wiring needed.
- Rate history is preserved (each `ExchangeRate` row is dated) — a deal closed in Q1 at the
  Q1 rate is not retroactively repriced by a Q3 rate refresh.

**Where in the code:**
- New module: `packages/twenty-server/src/modules/currency/` — ExchangeRate entity, ECB sync
  cron, rate-lookup service
- `packages/twenty-server/src/engine/core-modules/workspace/` — add baseCurrency,
  allowedCurrencyCodes, rateUpdateFrequency
- `packages/twenty-server/src/engine/metadata-modules/field-metadata/` — hook: on CURRENCY
  field creation, auto-add a companion `<fieldName>Base` NUMBER field
- `packages/twenty-front/` — display `amountBase` as read-only; currency picker filters

**Scope:** Medium. The ECB API is simple (one XML feed). The computed field trigger is the
same pattern as the workflow logic functions already in the codebase. The tricky part is the
metadata hook that auto-creates the companion field — but it follows existing field-creation
patterns.

---

### 9. Row-level security

**The gap:** `row-level-permission-predicate` is `@license Enterprise` — gated. Basic workspace
roles are free; restricting which *rows* a role can see (e.g., BU A cannot see BU B's records,
or a rep can only see their own opportunities) is not.

**Options:**
1. **License Twenty Enterprise** — clean, supported, but reintroduces a vendor relationship
   and reportedly requires an un-forked deployment (conflicts with the fork model). Confirm
   directly with Twenty.
2. **Reimplement in the fork** — the predicate pattern is understood from reading the
   enterprise files (we cannot copy them, but we can implement the same concept independently).
   Build a `RowAccessPolicy` entity: `{objectName, roleId, predicate: JSON filter expression}`.
   Evaluated at the GraphQL resolver layer before query execution.

**Recommended approach:** Reimplement. The concept is not novel — it's the same as
PostgreSQL row security or Salesforce sharing rules. The enterprise files implement it in a
specific way; we implement it our own way on top of the same data model.

**Minimal first shape:**
- `RowAccessPolicy` entity with `objectName`, `workspaceMemberRole`, `filterJson`
  (same filter syntax as Twenty's existing view filters — already serialisable).
- A resolver interceptor that, for each incoming query, finds applicable policies for the
  current user's role and appends them as WHERE conditions.
- Admin UI: a "Data Access" settings page. Per-object, per-role, define which records are
  visible. Start with simple ownership rules (`ownerId = currentUserId`) and BU-scoped rules
  (`buId = currentUserBuId`).

**Scope:** Large. This is security-critical code — it needs tests at the query layer to verify
predicates are not bypassable (e.g., via direct REST, via GraphQL introspection tricks, via
bulk operations). Do not ship without a security review pass.

---

### 10. Split-screen record view

**The gap:** Records open either in a right-side drawer (peek) or full page. There is no way
to view two records side by side, or to view a record list and a record detail simultaneously
in a split layout.

**What we build:**
A split-screen layout mode for the record index page:
- A toggle on the list/kanban view: "Split view" (the Salesforce-style layout).
- When active: left panel = the record list (narrower), right panel = the selected record's
  detail page (replaces the drawer).
- The right panel is a full record view, not a truncated peek — all tabs, all fields.
- State persists per object per user (if you prefer split view on Opportunities, it stays split).

This is orthogonal to the drawer vs. full-page decision — it adds a third layout mode.

**Where in the code:**
- `packages/twenty-front/src/modules/object-record/record-index/` — layout toggle + split mode
- `packages/twenty-front/src/modules/object-record/record-show/` — reuse as right panel
- User preference stored in `core.keyValuePair` (same mechanism as other UI preferences)

**Scope:** Medium. The record show component already exists; this is a layout wrapper and
preference persistence. The list panel needs responsive narrowing.

---

### 11. Independent pinned tabs — drawer vs full page

**The gap:** The right-side drawer (peek view) and the full record page show the same tabs in
the same default order. There is no way to set a different default/pinned tab for each context.
A user viewing a quick peek of a Contact wants to see the Timeline tab; the same user opening
the full Contact page wants to see the Fields tab with all details.

**What we build:**
- Per-object, per-context (DRAWER / FULL_PAGE) pinned tab preference.
- Admin can set workspace defaults; users can override for themselves.
- Stored in `core.keyValuePair` with key pattern `pinnedTab:{objectName}:{context}`.
- The tab bar reads the preference on mount and activates the pinned tab instead of defaulting
  to the first tab.

**Where in the code:**
- `packages/twenty-front/src/modules/object-record/record-show/components/` — tab activation
  logic reads preference
- `packages/twenty-front/src/modules/settings/` — admin workspace default per object
- `packages/twenty-front/src/modules/object-record/record-show/hooks/` — user preference hook

**Scope:** Small. Mostly preference storage + a one-line tab activation change.

---

### 12. Field-level role permissions (creation and edit)

**The gap (creation):** Fields can be set as non-nullable via metadata, but enforcement is
silently ignored on standard fields (§2). Beyond that, there is no way to mark a field as
*required at creation specifically* (some fields are optional during creation but must be
filled before a stage advance, for example).

**The gap (edit locking):** There is no way to lock a field from editing based on the current
user's role. A pricing field visible to all but editable only by Pricing team members, for
example, is not achievable natively.

**What we build:**

**12a — Creation-required vs always-required distinction:**
A `isRequiredAtCreation` flag on field metadata (separate from `isNullable`). When true, the
creation modal enforces the field even if the record allows null after creation (e.g., a stage
field that defaults after creation via workflow).

**12b — Role-based field edit lock:**
A `FieldEditPolicy` entity: `{fieldMetadataId, workspaceMemberRole, canEdit: boolean}`.
- The record edit form reads policies for the current user's role and renders locked fields
  as read-only (with a lock icon and tooltip: "Editing requires [Role] permissions").
- The server enforces the same at the mutation layer — a locked field value is stripped from
  the update payload before it reaches the database.

**Where in the code:**
- Field metadata entity: add `isRequiredAtCreation`
- `packages/twenty-front/src/modules/object-record/record-create/` — creation form enforcement
- New entity: `FieldEditPolicy` in the metadata module
- `packages/twenty-front/src/modules/object-record/record-field/` — read-only rendering
- `packages/twenty-server/src/engine/api/` — strip locked fields at mutation layer

**Scope:** Medium. 12a is small (one flag + form check). 12b is medium — the enforcement at
the server layer needs to be thorough (covers REST and GraphQL mutations).

---

### 13. Dashboard filters

**The gap:** The dashboard page has no filter controls. Every widget shows all-time / all-record
data. There is no way to filter the whole dashboard by date range, team, BU, or any other
dimension without editing each widget individually.

**What we build:**
- A dashboard-level filter bar (top of the dashboard page) with configurable filter dimensions:
  date range picker, plus any SELECT/RELATION fields the admin enables as dashboard dimensions
  (e.g., "BU", "Owner", "Stage").
- Dashboard filters are stored with the dashboard definition and applied as additional WHERE
  clauses to every widget query.
- User can override the dashboard default with a session-scoped filter (not persisted).

**Where in the code:**
- `packages/twenty-front/src/modules/dashboard/` — filter bar component, filter context
- Widget query layer: inject dashboard filter conditions into each widget's data fetch
- Dashboard settings: configure which fields appear as filter dimensions

**Scope:** Medium. The filter component exists (it's used in list views); adapting it for
dashboard context is the main work. The query injection is the sensitive part — must not break
widget-level filters.

---

### 14. Bug — dashboard widget persists after deletion

**The symptom:** Deleting a dashboard widget does not permanently remove it; it reappears
after page reload or navigation.

**Likely cause:** The delete mutation succeeds on the frontend (the widget disappears from
state) but either (a) the server delete fails silently, (b) the widget is soft-deleted but the
dashboard query does not filter `deletedAt IS NULL`, or (c) the frontend optimistic update
is not followed by a cache invalidation, and the next query re-fetches the stale record.

**Investigation path:**
- Check the dashboard widget delete mutation in the network tab — does it return success?
- Check the DB: does the widget row have `deletedAt` set after deletion?
- Check the dashboard widgets query — does it include a `filter: { deletedAt: { is: NULL } }` clause?

**Fix:** Whichever of (a/b/c) is the root cause — either the server soft-delete filter or the
Apollo cache invalidation. Document the exact cause when investigated.

**Scope:** Small fix once diagnosed. Log as a bug ticket; investigate against the live dev
instance before coding.

---

### 15. Dashboard-style widgets on object record pages

**The gap:** Object record pages are text-heavy (fields, relation lists). There is no way to
surface KPIs or visual summaries — e.g., "Total pipeline value for this Account", "NPS trend
for this Hotel", "Booking pace chart for this Enquiry" — as visual widgets alongside the
standard fields.

**What we build:**
A new widget type — `SUMMARY_WIDGET` — that can be placed on an object's record page:
- Displays a computed aggregate (count, sum, average) over related records, with an optional
  sparkline or bar chart.
- Configuration: related object, aggregation field, aggregation type, optional filter
  (e.g., only Enquiries in stage = Definite).
- Rendered as a compact card (number + label + optional mini-chart) in the record page layout.
- Works off the existing GraphQL relation queries — no new data layer needed.

The page layout editor (§5 in ENTERPRISE-LIMITATIONS.md, `IS_RECORD_PAGE_LAYOUT_EDITING_ENABLED`
flag — arriving upstream) is the natural placement mechanism once it ships. Until then,
widgets are configured via `viewField` rows in the DB.

**Where in the code:**
- `packages/twenty-front/src/modules/object-record/record-show/` — new `SummaryWidget`
  component + widget type registration
- `packages/twenty-front/src/ui/display/chart/` — minimal sparkline component (or a thin
  wrapper on an existing charting lib already in the bundle)
- No server changes needed — data comes from existing relation queries.

**Scope:** Medium. The charting piece is the variable — if we use a library already in the
bundle (Recharts is likely present for the dashboard), it is minimal. If not, evaluate bundle
cost before adding one.

---

### 16. Approval flows

**Design note:** Approval flows are a significant feature with multiple sub-patterns
(sequential approvals, parallel, delegated, conditional, time-bounded). Opening this properly
as a separate design session. Placeholder here.

Likely shape: `ApprovalRequest` standard object + `ApprovalStep` + workflow integration
(trigger: record reaches a stage; action: create ApprovalRequest; gate: record cannot advance
until request is approved). Email notification via the messaging module.

---

## Module roadmap

Three modules go on `main` because every client in the commercial/enterprise space eventually
needs them. They are not included in the initial baseline pass — they follow the governance and
Activity work.

### Service Desk
Customer-facing tickets, internal SLA tracking, shared inbox abstraction.
Minimal object set: `Ticket` (type, priority, status, SLA due, account, contact, assignee),
`TicketComment`, `TicketQueue` (routing rules).
Integration surface: email-to-ticket ingest (uses the messaging module); auto-close on reply.

### Marketing
Campaign and segment management, not email delivery (email delivery = external service).
Minimal object set: `Segment` (filter definition over Company/Person), `Campaign`
(name, channel, status, send date), `CampaignMembership` (segment → campaign).
Integration surface: webhook push to Mailchimp/Brevo/etc.; the CRM owns the segment logic,
not the send.

### Pricing / CPQ
Product catalogue and structured quoting.
Minimal object set: `Product` (name, category, unit, list price, currency), `PriceBook`
(name, currency, validity), `PriceBookEntry` (product × price book × price),
`QuoteLine` (quote × product × qty × unit price × discount).
The Quote object (already built for Scandic) is the anchor; QuoteLine makes it structured.

---

## Branch and release strategy

```
main
 └─ baseline changes 1–7 land here as features merge
 └─ modules land here as they are built

client/scandic              branches from main at baseline completion
 └─ hotel, meeting-room, room-block, enquiry-pipeline objects
 └─ OPERA integration layer
 └─ Scandic-specific workflows

client/<name>               branch from main at engagement start
```

**Upstream sync discipline:**
- `git fetch upstream && git merge upstream/main` on security releases only (watch the Twenty
  release notes for CVE tags).
- Feature updates from upstream: cherry-pick selectively. The areas most likely to conflict
  with our fork: the timeline service (§5), the calendar module (§6), and workspace settings UI
  (§1/§3/§4). Keep these fork points documented at the top of the relevant files with a
  `// KVADRANT: ...` comment explaining what changed and why.

---

## Research backlog — features from market scan

Items sourced from a web research pass (Gartner, G2, Capterra, Salesforce/HubSpot/Dynamics
comparisons, European compliance sources). Marked as **In scope** or **Out of scope** for the
baseline. Out-of-scope items are kept for reference — a specific client vertical or module
phase may pull them in.

### In scope — add to baseline design

| # | Feature | One-line description | Priority signal |
|---|---|---|---|
| R1 | **AI deal/lead scoring** | ML probability on open deals + leads based on activity signals and ICP fit | Table-stakes in 2026; every enterprise pipeline review needs it |
| R2 | **Sales forecasting** | Pipeline roll-up with weighted probability, commit vs. best-case vs. pipeline views, trend vs. prior period | No native equivalent in Twenty; top ask in enterprise evaluations |
| R3 | **Territory management** | Account assignment rules, quota per territory, regional sales hierarchy, rep-to-territory mapping | Top gap vs. Salesforce for 100–500 person B2B; cited across multiple sources |
| R4 | **Multi-language UI** | Full UI + email templates + quote layouts in multiple languages simultaneously; locale per user | Mandatory for EU deployments with mixed-language teams (DK/SE/FI/DE/NL) |
| R5 | **Audit trail (reimplemented)** | Immutable per-record action log (who changed what, when, from what value); GDPR + SOX compliance | Already in ENTERPRISE-LIMITATIONS as license-gated; reimplement in the fork |
| R6 | **PII field masking** | Dynamic redaction of sensitive fields (email, phone, revenue) for users without data access; GDPR-specific | Strong EU differentiator; US CRMs consistently get this wrong |
| R7 | **Data quality / pipeline hygiene dashboard** | Completeness scoring per record, stale deal alerts, missing-field flags, duplicate detection | Repeatedly cited as gap in open-source CRMs |
| R8 | **Mobile offline sync** | Full record create/update offline with automatic conflict-resolving sync on reconnect | Field sales reality in EU; cited in Resco and enterprise mobile CRM reviews |
| R9 | **Expansion revenue tracking** | Upsell/cross-sell opportunity pipeline separate from new business; net revenue retention view per account | SaaS + subscription clients; complements the Contracting Pipeline |
| R10 | **Deal desk / discount approval** | Approval chain for deals requiring non-standard pricing, legal exceptions, or above-threshold discounts | The sales-specific incarnation of §16 Approval Flows; design together |
| R11 | **CLM integration hooks** | Contract lifecycle: document storage, renewal tracking, signature workflow trigger (DocuSign/Adobe Sign), expiry alerts | Relevant to the Contracting Pipeline; integration hook not a full build |
| R12 | **Email tracking + activity attribution** | Open/click/reply detection feeding into Activity model; pipeline attribution across email, call, meeting | Complements §5 Activity model; signal source for R1 scoring |
| R13 | **Capacity planning** | Resource utilisation tracking, pipeline-to-headcount forecasting, workload visualisation per rep/team | High relevance for professional services clients (Kvadrant's own segment) |

### Out of scope for baseline — keep for reference

These are real enterprise CRM features but either (a) require third-party integration rather
than platform build, (b) are vertical-specific, or (c) are too far from the current build
surface to sequence.

| # | Feature | Reason out of scope |
|---|---|---|
| N1 | **AI conversation intelligence** (call transcription, sentiment, auto-field update) | Depends on call recording integration (Fireflies, Gong, etc.); platform provides the hook, not the AI |
| N2 | **Customer health score + churn prediction** | SaaS/subscription-specific; relevant for clients whose customers are on recurring contracts — add on client branch |
| N3 | **Buyer intent data integration** (Bombora, G2 signals) | Third-party data layer; platform provides webhook ingest, not the intent source |
| N4 | **Revenue intelligence / deal analytics AI** | Requires sufficient deal history to train; a later-phase AI feature once data is accumulating |
| N5 | **Partner / channel management (PRM)** | Vertical-specific; relevant for clients with reseller networks — client branch |
| N6 | **Sales playbooks** (battle cards, ROI calculators in-app) | Content management feature; better served by a linked knowledge base than a CRM core feature |
| N7 | **Call centre QA scoring + coaching** | Contact centre tooling; not B2B sales CRM territory |
| N8 | **Social listening + competitive intelligence** | External monitoring layer; not CRM platform work |
| N9 | **LinkedIn social selling tools** | Requires LinkedIn API partnership; nice-to-have, not core |
| N10 | **Customer Data Platform (CDP) integration** | Enterprise integration project per client; not baseline platform |
| N11 | **Knowledge base with AI self-service** | Belongs in the Service Desk module (§ Module roadmap), not the core platform |
| N12 | **Professional Services Automation (PSA)** | Time tracking + project billing is a separate tool category; out of CRM scope unless client is a consultancy |
| N13 | **Account scoring (ICP fit)** | Overlaps with R1 (deal scoring); consolidate there |

---

## Sequencing — to be structured into workstreams

The items below are not yet ordered. Next step: group into workstreams
(Workspace Config, Governance, UX/Layout, Data Model, Modules, AI/Reporting) and sequence within each.

**All in-scope items:**

| § | Change | Size | Theme |
|---|---|---|---|
| 1 | Brand colour | S | Workspace config |
| 2 | Required standard fields | S | Data quality |
| 3 | Allowed currency list | S | Workspace config |
| 4 | Channel governance (phase 1) | L | Governance |
| 4d | Channel governance — role-keyed (phase 2) | M | Governance |
| 5 | Activity model + timeline fork | M | Data model |
| 6a | Calendar — manual events visible | S | UX |
| 6b/c | Calendar — click-through | L | UX |
| 7 | Account hierarchy widget | M | UX |
| 8 | Currency framework | M | Data model |
| 9 | Row-level security | L | Governance |
| 10 | Split-screen record view | M | UX/Layout |
| 11 | Independent pinned tabs | S | UX/Layout |
| 12a | Required at creation | S | Data quality |
| 12b | Field-level role edit lock | M | Governance |
| 13 | Dashboard filters | M | Reporting |
| 14 | Bug: dashboard widget deletion | S | Bug |
| 15 | Summary widgets on object pages | M | UX/Reporting |
| 16 | Approval flows | L | Workflow — design TBD |
| R1 | AI deal/lead scoring | L | AI/Reporting |
| R2 | Sales forecasting | M | Reporting |
| R3 | Territory management | L | Data model/Governance |
| R4 | Multi-language UI | M | Workspace config |
| R5 | Audit trail (reimplemented) | M | Governance |
| R6 | PII field masking | M | Governance |
| R7 | Data quality / pipeline hygiene dashboard | M | Reporting |
| R8 | Mobile offline sync | L | UX |
| R9 | Expansion revenue tracking | S | Data model |
| R10 | Deal desk / discount approval | M | Workflow |
| R11 | CLM integration hooks | M | Integration |
| R12 | Email tracking + attribution | M | Data model |
| R13 | Capacity planning | L | Reporting |
| — | Service Desk module | L | Module |
| — | Marketing module | L | Module |
| — | Pricing / CPQ module | L | Module |
