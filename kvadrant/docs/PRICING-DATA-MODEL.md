# Pricing data model — open design discussion (NOT finalized)

**Status: OPEN.** This records a design conversation, not an agreed model. The schema is unchanged.
Decision deferred until we design the **UX for the actual sales flows** (below) — the right field
homes follow from how reps actually work, not from a tidy diagram.

## Context
The deterministic Generate-Quote workflow is built and working (see `build/GENERATE_QUOTE_WORKFLOW.md`).
While wiring it, we noticed overlap in where money/figures live:
- **Enquiry** (the Opportunity object) currently holds `dayDelegateRate`, `meetingRoomRevenue`,
  `fbRevenue`, `bedroomRevenue`, plus `amount` (pipeline value) and the demand facts (pax, room-nights,
  dates).
- **Quote** holds `version`, `status`, `totalValue`, `dayDelegateRateOffered`, `pricingSnapshot`.
- **Quote Line** holds the per-line breakdown (DDR / Room Night → qty, unit, total, basis).
- **Rate Card** = list prices per hotel; **Corporate Agreement** = negotiated rate/discount;
  **Room Block** = operational OPERA hold.

## The principle we agree on
- **Enquiry = what the client wants** (demand) and **the pipeline opportunity** — so it MUST carry a
  value for forecasting. It is the main opportunity object.
- **Quote (+Lines) = what we offered** — a *versioned, point-in-time snapshot*. It is correct (not
  redundant) for a Quote to copy the figures it was priced on, so it stays fixed when the enquiry or
  rate card change later.
- **Rate Card / Agreement = the price book.** **Room Block = the operational hold.**
- Redundancy is only a problem when the **same live fact is hand-maintained in two places**.

## What makes this NOT a simple "move fields to the Quote" — the real complications
Raised in discussion; these drive the design:

1. **Enquiry needs its own value field for pipeline.** `amount` stays on the Enquiry regardless —
   that's how pipeline/forecast is calculated. The question is only how it's *populated* (manual vs
   rolled-up from the accepted quote vs both).
2. **Multiple money concepts, not one.** They are genuinely different and may each need a home:
   - **Budget** — a ceiling/expectation the *client* brings. The rep should be able to enter it.
   - **Forecast / pipeline value** (`Enquiry.amount`) — expected deal value for reporting.
   - **Quoted value** (`Quote.totalValue`) — what we formally offered, per version (snapshot).
   - **Accepted / contracted value** — the accepted quote's total (could set `amount` on win).
   - **Actual revenue** — post-delivery; may differ again.
3. **Pricing authority varies by deal** — this is the crux:
   - Sometimes **we price it** (Generate Quote computes from Rate Card + Agreement).
   - Sometimes the **client gives a budget/target** and we build/quote to it.
   - Sometimes the **customer selects the price**.
   Where the headline number *originates* differs per flow, so a single fixed field home is wrong.
4. **`dayDelegateRate` on the Enquiry is ambiguous** — is it a *client budget/target DDR* (demand-side
   input) or the *quoted DDR* (offer-side, already `Quote.dayDelegateRateOffered`)? These are different
   things that happen to share a number shape.
5. **Revenue split** (meeting / F&B / bedroom) — currently Enquiry fields; conceptually a Quote-Line
   breakdown. But reps may want a quick split on the enquiry *before* a quote exists.

## Tentative direction (to validate against UX, not to implement yet)
- Keep `Enquiry.amount` as the forecast/pipeline value; allow manual entry, and optionally auto-set
  from the accepted quote on win.
- Add an explicit **client budget** concept on the Enquiry (e.g. `budgetValue`, optional, rep-entered)
  — distinct from forecast and from quoted.
- Treat the **Quote + Quote Lines** as the system of record for the *offered* price and its breakdown
  (snapshot). Revenue split → line types (DDR / Room Night / F&B / Room Hire).
- Reconsider/rename or drop `Enquiry.dayDelegateRate` and the three revenue fields once the budget vs
  quoted vs forecast roles are settled by the flows.
- Add `currencyCode` to Corporate Agreement (the one clear bug — a negotiated rate with no currency).

## Open questions to resolve via UX first
- For each pricing-authority flow (we-price / client-budget / customer-selected), what does the rep
  enter, where, and when? What's read-only vs editable?
- Does the enquiry show a budget AND a forecast AND the latest-quote total side by side?
- On quote acceptance, what writes back to the Enquiry (amount, stage, room block rate)?
- Revenue split: needed on the Enquiry pre-quote, or only as Quote Lines?

## Next step
Design the UX for the three flows, then map fields to objects from that — and only then change schema.
Nothing here is committed.
