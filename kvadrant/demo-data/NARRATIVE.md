# Scandic Group & Meeting CRM — Demo Click-Path

**For the salesperson presenting the CRM tomorrow.**
This is a suggested 10–15 minute walkthrough that tells a complete MICE sales story from first enquiry through to post-event feedback and OPERA sync.

---

## The Story Arc

> "Let me show you how a deal lives from the moment it arrives to the moment the delegates check out — and how everything syncs with OPERA automatically."

---

## Step 1 — The Kanban Pipeline (30 seconds)

Open the **Enquiries board** (Kanban view). Point out cards in every column — from LEAD on the left to FOLLOW_UP on the right. The board has 23 live enquiries totalling over 14M in revenue across five currencies.

Highlight the **DEFINITE** column: three anchor deals already confirmed.

---

## Step 2 — Hero Deal: Volvo Group AGM 2026 (3 minutes)

Open **"Volvo Group AGM 2026"** in the DEFINITE column.

**Tell the story:**
- 220 delegates, 3 days at Scandic Triangeln, Malmö — 182 room nights, DDR 695 SEK, total **1,218,000 SEK**
- Account: **Volvo Group** (corporate agreement in place — 12.5% discount, 400-night commitment)
- Decision-maker: **Anders Björklund**, SVP Corporate Affairs. Event Manager: **Kristoffer Lindqvist**.
- Revenue split: Meeting rooms 184k / F&B 412k / Bedrooms 622k — exactly to budget

**Quote trail:** Show **Quote – Volvo Group AGM v1** (DECLINED — rate negotiated down) → **Quote – Volvo Group AGM v2** (ACCEPTED). This shows version history and the negotiation in one click.

**Room block:** Open **Block – Volvo Group AGM 2026** — 91 rooms/night × 2 nights @ 1,695 SEK. Pickup already at 86/91. Cut-off: 14 August.

**OPERA sync talking point:** `operaBlockCode: BLK-2026-0481` and `operaConfirmationNo: OPERA-778231` are both populated, `syncStatus: SYNCED`. Say: *"The moment the client signed, the block flowed straight into OPERA. No double-entry."*

---

## Step 3 — The Live Deal Under Pressure: Ericsson Leadership Forum Q3 2026 (2 minutes)

Switch to the **TENTATIVE** column. Open **"Ericsson Leadership Forum Q3 2026"**.

- **Tentative hold expiry: 20 June 2026** — 17 days away. Decision date: 18 June.
- Quote v2 is **SENT** (895 SEK DDR, total 784,500 SEK). Quote v1 was declined — rate came down.
- Competitor: Radisson Blu Waterfront Stockholm is named. Show the `competitorHotel` field.
- `syncStatus: PENDING` — the block is reserved in OPERA but not confirmed until the client signs.

Say: *"This is the deal your sales manager wakes up thinking about. The hold expires in 17 days, the competitor is visible, and the quote is sitting in the client's inbox."*

Also mention: Ericsson has a corporate agreement (negotiated room rate 1,695 SEK, 600-night commitment) — show the **Ericsson 2026 Agreement** under Corporate Agreements.

---

## Step 4 — The Completed Lifecycle: Ericsson Global Kickoff 2026 (2 minutes)

Now jump to **COMPLETED**. Open **"Ericsson Global Kickoff 2026"**.

- 480 delegates, Scandic Marina Congress Center Helsinki, 3 days — 360 room nights, total **162,000 EUR**
- Delivered February 2026. `syncStatus: SYNCED`, `operaConfirmationNo: OPERA-741089`.

Open feedback: **"Feedback – Ericsson Global Kickoff 2026"**
- **NPS 9**, `wouldRebook: true`
- Quote: *"The main auditorium tech set-up was flawless… Will absolutely return for our next global event."*

Say: *"This is what the full lifecycle looks like. Lead → Qualified → Proposal → Definite → Delivery → Completed → NPS 9 and a repeat booking already in progress."*

---

## Step 5 — The Upcoming Blockbuster: Novo Nordisk Diabetes Congress 2026 (1 minute)

Jump to **DEFINITE**. Open **"Novo Nordisk Diabetes Congress 2026"**.

- 310 delegates, Scandic Copenhagen, 4 days, **2,140,000 DKK** — the largest deal on the board
- 680 room nights (multi-night, multi-room type), cut-off 10 October
- Source: **CVENT_RFP** — shows the platform integration feeding the pipeline
- `syncStatus: SYNCED` — OPERA block confirmed

This is a good moment to mention the **Novo Nordisk 2026 corporate agreement** (10% discount, 500-night commitment, 152 nights actualised so far).

---

## Step 6 — Pipeline Health at a Glance (1 minute)

Return to the pipeline view. Make three points:

1. **Currency spread:** SEK, DKK, NOK, EUR all live — multi-market at a glance.
2. **Source mix:** CVENT_RFP, DIRECT, REPEAT, AGENCY, MICE_BID all represented — source attribution works.
3. **OPERA sync status:** Green (SYNCED) on all confirmed deals, PENDING on tentatives, NOT_SYNCED only on early-stage leads. No manual chasing.

---

## OPERA Sync Talking Point (anywhere in the demo)

> "Every definite enquiry has a block code and a confirmation number that live in both systems. The `syncStatus` field is the handshake — SYNCED means OPERA and the CRM agree. PENDING means the hold is parked. NOT_SYNCED means it's too early — we don't want to pollute OPERA with leads."

Reference deals: Volvo AGM (`BLK-2026-0481` / `OPERA-778231`), Novo Nordisk Congress (`BLK-2026-0398` / `OPERA-762140`), Scandinavian Cardiology Congress (`BLK-2026-0420` / `OPERA-765300`).

---

## Optional Deep-Dive: Nordic Conference Partners – MedTech Forum

If time allows and the audience includes procurement: open this QUALIFIED enquiry (250 delegates, Scandic Copenhagen, DKK 890k, competitor Bella Center Copenhagen visible). Shows how PCO/agency business enters the pipeline via Cvent RFP and is tracked against a direct competitor before a decision is made.

---

*Data current as of June 2026. All figures in local currency.*
