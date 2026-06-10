# Twenty CRM — Enterprise Limitations & Capability Map

> A tested map of where Twenty's out-of-box capability ends and custom/fork/licensed work begins.
> Compiled from a hands-on stress-test of the running `twentycrm/twenty:latest` image (the Scandic
> Group & Meeting build). Companion to `PROJECT.md`. This is reusable IP for scoping client deals.

**How to read this**
- **Status legend:**
  - ✅ **Native** — works out of the box / pure config.
  - 🔶 **Workaround** — achievable now without forking, but indirect (job/script/extra objects); has caveats.
  - 🔧 **Fork** — requires editing Twenty's code (allowed under AGPL; this is the "build-deeply" work Kvadrant sells).
  - 🔒 **License-gated** — `@license Enterprise` (Twenty's commercial license); cannot copy/edit those files without a deal. Reimplement or license.
- **Evidence:** **[tested]** = verified live on the instance · **[code]** = read from source, not run · **[policy]** = Twenty's commercial terms, to confirm with Twenty.

**The one-line pattern:** *Twenty is strong where it's generic (data/metadata engine) and thin where it's opinionated (UI presentation, governance, anything org-controlled).* The data layer models almost anything fast; the gaps cluster in (a) the frontend privileging standard objects and (b) the absence of admin/org governance — both are squarely fork-and-build-deeply territory, not foundation weaknesses.

---

## 1. License-gated features (the hard commercial line) 🔒

~300 files are marked `/* @license Enterprise */` — NOT AGPL. Most are Twenty's own SaaS plumbing (billing, usage, DNS, Cloudflare) and irrelevant to a self-hosted client. The ones that matter:

| Capability | Status | Evidence | Notes / escape hatch |
|---|---|---|---|
| **SSO / SAML / OIDC** (federated login via the client's IdP) | 🔒 | [code] | The genuine enterprise line. Escape: reimplement, or self-host **Keycloak** (EU, no vendor), or license Twenty enterprise. |
| **Advanced RBAC + row-level permissions** | 🔒 | [code] | `row-level-permission-predicate` is gated. Basic roles are free. This is the backbone of BU data isolation (§2). |
| **Audit / event logs** | 🔒 | [code] | Compliance (GDPR/finance). Build or license. |
| "Login with **Google** / **Microsoft**" (OAuth sign-in) | ✅ | [code] | **NOT gated** — free. Only SAML/OIDC *federation* is gated. |
| Billing / usage / DNS / Cloudflare | 🔒 | [code] | Irrelevant — Twenty's SaaS; clients bill directly. |

**Twenty's commercial model** 🔒 [policy]: enterprise features are reportedly supported only on **un-forked** deployments, with extension limited to the apps SDK. To confirm directly with Twenty. If true, the "no-fork + apps + their enterprise license" path is a different commercial relationship than the AGPL fork path — and reintroduces a vendor.

---

## 2. Multi-business-unit / data isolation

Two separate requirements people conflate:

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| **Different pipeline / sales process per BU** | ✅ / 🔶 | [tested] | A pipeline is just a KANBAN view grouped by a SELECT. Proven: built a 2nd full pipeline ("Contracting Pipeline") on a custom object alongside the standard Enquiries pipeline. Options: multiple stage fields on one object + per-view Kanban, OR a separate pipeline object per BU over shared Account/Contact/Hotel. |
| **True "record types"** (one object, per-type layout + picklist + enforced process) | 🔧 | [code] | No native record-types (Salesforce-style). Fork. |
| **BU-scoped data isolation** (BU A cannot SEE BU B's records) | 🔒 | [code] | This is row-level permissions → enterprise-gated. The real crux + the one with a cost: license or reimplement. If BUs may see each other's data, the native pipeline workarounds suffice at no cost. |

---

## 3. Account hierarchy ✅ (mostly native)

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| Arbitrary-depth account hierarchy (global → regional → local → child) | ✅ | [tested] | Self-referential relation works (no target≠source guard). Built IKEA→Maersk→Volvo, verified parent + subsidiaries traversal both ways. Can add a 2nd self-relation for a different axis (owner/association vs corporate parent). |
| Org-chart **tree visualization** | 🔧 | [code] | Twenty shows a flat relation field + related list, not a graphical tree. Fork. |
| **Roll-up aggregation** across the hierarchy (e.g. total pipeline across all subsidiaries) | 🔧 | [code] | Not native. Fork. |

---

## 4. Unified Activity model & consolidated timeline/calendar

The richest area we stress-tested. The goal: one Activity object (visits, calls, touchpoints, emails, meetings) relating to Accounts/Contacts/Enquiries, visible in one consolidated timeline + calendar per record.

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| One custom **Activity** object with direct relations to Account/Contact/Enquiry/Hotel | ✅ | [tested] | Renders as clean named chips. The shippable model. |
| **Polymorphic** relation (one Activity → any object type, many at once) via `MORPH_RELATION` + junction | ✅ data / 🔧 UI | [tested] | Data layer works; junction auto-extends to new objects. BUT a **custom junction renders "Untitled" chips** — only built-in note/task targets get named-chip treatment. Good UX = frontend fork. |
| Activity on the related record's **Timeline** | 🔧 | [tested] | Timeline propagation is **hardcoded** to `note`/`task`/`noteTarget`/`taskTarget`. A custom Activity does NOT appear on related records' timelines. A **Task** does (and is clickable). |
| Activity on the related record's **Calendar** | 🔧 | [tested] | Calendar tab is bound to `CalendarEvent` only. |
| One native primitive feeding **both** timeline + calendar | ❌ | [tested] | None exists. Task→timeline; CalendarEvent→calendar. "One consolidated view of everything" is not fully native regardless of primitive chosen. |
| Calendar tab showing **manually-created** events with title + click-through | 🔧 | [tested] | The calendar widget is a **read-only sync visualization**. Manual events render as **"Not shared"** time blocks — no title, not clickable. Un-hide requires real calendar sync (channel with `SHARE_EVERYTHING`) OR a frontend fork. `calendarEvent` has no FIELDS_WIDGET view (hardcoded record page) so a custom relation chip can't be surfaced on it via config either. |
| **Hybrid** (mirror Enquiry → Task for timeline, → CalendarEvent for calendar) | 🔶 | [tested] | Timeline hybrid works well + is clickable. Calendar hybrid puts the event on the calendar but it's "Not shared" / non-clickable (same ceiling). No systematic mirror is built — would be an adapter. |

---

## 5. UI / presentation layer (consistent theme)

Root cause across all of these: **the frontend privileges Twenty's own standard objects with polish that custom objects don't inherit.** None are *data* limitations — the data is always correct via API/DB; it's presentation config.

| Limitation | Status | Evidence | Notes |
|---|---|---|---|
| Custom fields don't auto-appear as **list-view columns** | 🔶 | [tested] | Land hidden; must add `viewField` rows. Fixed via script. |
| Custom fields dumped into **"System"** group on record pages | 🔶 | [tested] | Must populate the object's FIELDS_WIDGET view. |
| Custom-object **record pages** need manual layout config to show fields/relations | 🔶 | [tested] | Same FIELDS_WIDGET mechanism + server restart. |
| **Standard fields can't be made required** | 🔧 | [tested] | `updateOneField isNullable:false` on a standard composite field (e.g. person.emails) is silently ignored. Mandatory = fork. |
| **Field type is immutable** | ⚠️ | [tested] | `UpdateFieldInput` omits `type`. To change type (e.g. Year NUMBER→TEXT) you must delete + recreate the field (capture/restore values). |
| Brand **accent color** not configurable | 🔧 | [tested] | No `brandColor` field / picker in this image. Workspace name + logo only; accent color = code change. |
| Half-built feature flags (e.g. `IS_RECORD_PAGE_LAYOUT_EDITING_ENABLED`) | ℹ️ | [code] | Signals the UI layer is mid-evolution; record-page layout editing is arriving. |

---

## 6. Mailbox / calendar connection governance (the org-control gap)

Twenty treats the employee's inbox/calendar as **personal and self-governed** — a sensible product default, but the opposite of what a 400-person enterprise rollout needs. This whole category is the same shape: per-user by design, no admin governance, fork to centralize.

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| Connect an **org** Google Workspace / Microsoft 365 mailbox+calendar | ✅ | [code] | Free, NOT gated, Google **and** Microsoft. Same flow as personal accounts. |
| Email (Gmail) + calendar sync | ✅ | [tested] | Free, not gated. Same single Google OAuth grant (scopes include gmail + calendar); separate feature flags. Enabled on the instance. |
| **Connected by default** for all staff (no per-user action) | 🔧 | [code] | NOT native, even with SSO. SSO governs *login* only — zero references to connectedAccount/calendarChannel. No domain-wide delegation / admin "connect everyone." Each user connects once via OAuth. True zero-touch = fork (Google service-account domain-wide delegation / MS application permissions). Admin app-allow-listing makes per-user ~frictionless but still per-user. |
| **Enforced / locked** sync settings (admin sets, users can't change) | 🔧 / 🔶 | [code] | NOT native. Per-channel settings (`visibility` SHARE_EVERYTHING vs METADATA, `isContactAutoCreationEnabled`, `contactAutoCreationPolicy`, `excludeNonProfessionalEmails`, `isSyncEnabled`) are per-user, code-defaulted, UI-editable. No workspace-level policy/lock (the only WORKSPACE visibility concept in code is for *Views*). Workaround: a scheduled job re-writes settings to org standard (resets drift). Proper: fork a workspace channel policy. |
| **Role-based** activity sharing (e.g. Sales reps' comms shared, Marketing/Pricing/Commercial private) | 🔶 / 🔧 | [code] | NOT native, but a legitimate pattern (cf. Salesforce Einstein Activity Capture). Pieces exist: roles are free; channel→connectedAccount→accountOwner(workspaceMember)→role chain is derivable; `visibility` is the lever. Deliver via (a) enforcement job keyed on role, or (b) fork a role-keyed channel policy. |
| Channels reachable via public **REST API** (for the enforcement job) | ❌ | [tested] | `MessageChannel` / `CalendarChannel` / `ConnectedAccount` are NOT in the REST schema (only `WorkspaceMember` is). An enforcement job must use the workspace ORM/GraphQL or direct DB — not a simple REST script. |

---

## 7. Apps SDK ceiling (the no-fork extension path)

Relevant only if pursuing Twenty's "un-forked + apps" model (§1). Custom UI = a `FRONT_COMPONENT` widget packaged in an app.

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| Custom UI on a record page (e.g. Opportunity), incl. a full **tab** | ✅ | [code] | `FRONT_COMPONENT` widget; the postcard example puts one on its own record-page tab. |
| Page-layout **types** exist: RECORD_PAGE, RECORD_INDEX, DASHBOARD, STANDALONE_PAGE | ✅ | [code] | Infra for full custom pages + custom list/Kanban exists. |
| App can place a front-component on **STANDALONE_PAGE / RECORD_INDEX** + nav to it | ❓ | [code] | UNVERIFIED via the SDK — the example's nav item targets a *view*, not a standalone component page. **The key question to put to Twenty**: can an app ship a full custom page / custom index experience, or are front-components record-page-tab-only? This decides whether Salesforce-style custom screens are buildable as an app (no fork) or not. |

---

## 8. Operational gotchas (not "limitations," but bite during a build)

These are config/process traps, captured so they don't recur. None are blockers.

- **Reserved field names:** `type`, `role` are reserved (use `activityType`, `contactRole`). Server adds a "Custom" suffix otherwise / rejects.
- **REST rate limit:** 100 requests / 60s → throttle (~0.7s) + retry on 429 for bulk seeding.
- **Direct DB/view edits bypass cache:** after editing `viewField`/`view`/metadata in the DB, `docker compose restart server` to render (Redis FLUSHALL alone insufficient).
- **Changing a SELECT field's options wipes that field's `viewGroup` rows** → Kanban goes blank; rebuild the viewGroups.
- **Renaming an object label does NOT change its REST endpoint** (Enquiries still POST to `/rest/opportunities`; Contracts to `/rest/corporateAgreements`).
- **Phone `primaryPhoneCountryCode`** must not be hard-coded (conflicts with non-matching numbers) — omit, let it infer.
- **Workflows with code steps** need `LOGIC_FUNCTION_TYPE=LOCAL` on **both** server AND worker (off by default → sample workflows fail with "Logic function transpilation is disabled").
- **Hand-inserting a user** needs a UUID with version nibble 1–5 or the auth cache silently returns USER_NOT_FOUND.

---

## 9. Observations & judgments (things I noticed across the build, beyond the discrete tests)

Softer than the tables above — patterns, risks, and read-between-the-lines findings worth recording. Mostly **[judgment]** from working in the codebase + running the build, not single tests.

**Product maturity & trajectory**
- **The product is mid-evolution, visibly.** Half-built feature flags (`IS_RECORD_PAGE_LAYOUT_EDITING_ENABLED`, `..._GLOBAL_EDITION_ENABLED`), SDK at v2.x, the `twenty-cli` already **deprecated** in favor of `twenty-sdk`, and DB upgrade commands that **delete & recreate record page layouts** between versions. Implication: pin a version per client; expect churn in exactly the UI-layer areas you'd fork; re-test your forks on upgrade.
- **Upstream moves fast** (we cloned at v0.3.4, daily commits). Good for security patches, but a moving target under any fork.

**Architecture observations**
- **Two API planes with different rules.** Auth/metadata mutations live on `POST /metadata`; record data on `POST /graphql` + `/rest`. Introspection is **disabled** on the prod image, and the running image's schema may **not match repo source** — so capabilities must be verified live, never assumed from source. This caused real friction.
- **REST is a deliberately narrow surface.** System objects (channels, connected accounts, calendar internals) are intentionally absent from REST. Anything governance-related must drop to GraphQL/ORM/DB — REST won't carry it. This recurs.
- **The metadata engine is the genuine strength.** Custom objects/fields/relations/selects/morph/self-relations all created cleanly via API, usually first try, idempotently. If you're modeling a domain, Twenty is fast and pleasant. The ceiling is never the data model — it's always presentation or governance.
- **"Standard vs custom" is a first-class distinction in the code**, and it leaks into UX everywhere: standard objects get named-chip junctions, hardcoded rich record pages, timeline/calendar wiring, special field handling — custom objects get the generic treatment. Every "why doesn't my custom thing look as good as Opportunity" trace ended here. **This single asymmetry explains ~80% of the UI gaps.**

**Reliability / delivery observations (from actually building)**
- **Agent/automation self-reports are unreliable; only DB/REST ground truth counts.** A browser-automation agent confidently reported an object rename succeeded when the DB proved it hadn't; another looped on signup. Lesson baked into how the rest of the build was verified.
- **Browser-driving the UI for setup is fragile; the API path is far more reliable + re-runnable.** The whole demo was ultimately built API-first.
- **Manual events are second-class in the calendar** specifically because Twenty assumes calendar data comes from *sync* — a recurring "it assumes the integration is the source of truth" theme (also true of contacts auto-created from sync, etc.).

**Strategic / commercial read [judgment]**
- **The recurring failure mode is governance, not capability.** Connection, sync settings, visibility, provisioning — Twenty consistently models these as *personal, user-owned* choices. Excellent privacy default for a product; wrong default for a centrally-administered enterprise. This is the single biggest theme and the clearest fork/upsell surface.
- **Easy to oversell by analogy.** "It has roles" ≠ row-level isolation; "it syncs Google/365" ≠ centrally managed; "it has a calendar" ≠ interactive activity calendar; "it has workflows" ≠ enabled by default. Each pairing burned a question this session. Pre-empt them in client scoping.
- **The calendar widget is the single most fork-or-nothing surface encountered.** Almost everything else bends to config or a workaround; the calendar genuinely doesn't (read-only, sync-coupled, non-interactive). If an interactive activity calendar is a hard requirement, budget the fork explicitly.
- **`@license Enterprise` is a real constraint but the boundary is favorable** — the gated set is mostly Twenty's SaaS plumbing; the only client-relevant gated items are SSO, row-level RBAC, audit logs. Everything else we wanted was AGPL-forkable.

## Summary: where the money is

The limitations cluster into a coherent, sellable **"enterprise layer"** Kvadrant builds on the fork:

1. **Governance** — admin-provisioned mailbox connection, locked/role-based channel policies, centralized defaults. (§6)
2. **Data isolation & record types** — row-level BU isolation, per-type layouts/process. (§2) *(isolation crosses the license line — decide license vs reimplement.)*
3. **Activity & calendar UX** — unified Activity surfaced in timeline + an interactive, titled, click-through calendar. (§4)
4. **Presentation polish** — custom-object record layouts, required fields, branding. (§5)
5. **Reporting** — hierarchy roll-ups, cross-type activity analytics. (§3, §4)

None are foundation weaknesses — the data/metadata engine is solid (hierarchy, polymorphic relations, multi-pipeline, custom objects all tested working). They're precisely the opinionated/governance surface a young free product hasn't built yet — i.e. the depth a vendor-free premium consultancy is positioned to deliver and bill for. The discipline for client conversations: **name these explicitly up front** so "it syncs Google/365" / "it has roles" isn't mistaken for "it's centrally governed / isolated" — the gap between them is the engagement.
