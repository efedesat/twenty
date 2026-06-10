/**
 * Scandic Group & Meeting — "Generate Quote" workflow Code step (NO AI).
 *
 * Deterministic pricing math from build/quote_engine.py, as a Twenty workflow Code step.
 * Pure (no I/O) — the workflow's Find Records steps fetch records and pass them in; the
 * Create Record steps write the Quote + Quote Lines.
 *
 * FOUR inputs (map each to a Find Records step's `.all` result; strings/arrays tolerated):
 *   enquiry        ← Find Enquiry (Id = trigger record)
 *   rateCard       ← Find Rate Card (Hotel → Id = trigger.hotelId)
 *   agreement      ← Find Corporate Agreement (Account → Id = trigger.companyId, Status ACTIVE) — may be empty
 *   existingQuotes ← Find Quote (Enquiry → Id = trigger.id) — for auto-versioning; may be empty
 *
 * Returns flat fields for the Quote + Quote Line create steps, an auto-incremented `version`,
 * and `snapshot` (the full calculation as a JSON string) for the Quote.pricingSnapshot field.
 * Requires LOGIC_FUNCTION_TYPE=LOCAL. Mirrors compute_quote()/next_version() in quote_engine.py.
 */
export const main = async (params: {
  enquiry: any;
  rateCard: any;
  agreement: any;
  existingQuotes: any;
}): Promise<object> => {
  const parse = (x: any) => {
    let v = x;
    if (typeof v === "string") { try { v = JSON.parse(v); } catch (e) { v = undefined; } }
    return v;
  };
  const pick = (x: any) => { const v = parse(x); return (Array.isArray(v) ? v[0] : v) || {}; };
  const list = (x: any) => { const v = parse(x); return Array.isArray(v) ? v : v ? [v] : []; };

  const enquiry = pick(params.enquiry);
  const rateCard = pick(params.rateCard);
  const agreement = pick(params.agreement);
  const existingQuotes = list(params.existingQuotes);

  if (rateCard.listDayDelegateRate == null) {
    throw new Error("no rate card for this enquiry's hotel");
  }

  const version =
    existingQuotes.reduce(
      (m: number, q: any) => Math.max(m, parseInt(String(q?.version || 0), 10) || 0),
      0,
    ) + 1;

  let meetingDays = 1;
  if (enquiry.eventStartDate) {
    const s = new Date(String(enquiry.eventStartDate).slice(0, 10)).getTime();
    const e = enquiry.eventEndDate
      ? new Date(String(enquiry.eventEndDate).slice(0, 10)).getTime()
      : s;
    meetingDays = Math.max(1, Math.round((e - s) / 86400000));
  }

  const pax = parseInt(String(enquiry.numberOfDelegates || 0), 10);
  const nights = parseInt(String(enquiry.roomNights || 0), 10);
  const ddr = parseInt(String(rateCard.listDayDelegateRate), 10);
  const listRoom = parseInt(String(rateCard.listRoomNightRate), 10);
  const hasAgreement =
    agreement.status === "ACTIVE" && !!agreement.negotiatedRoomRate;
  const roomRate = hasAgreement
    ? parseInt(String(agreement.negotiatedRoomRate), 10)
    : listRoom;
  const roomBasis = hasAgreement
    ? `${agreement.name} negotiated rate`
    : "list room-night rate (no active agreement)";

  const ddrQty = pax * meetingDays;
  const ddrTotal = ddr * ddrQty;
  const roomsTotal = roomRate * nights;
  const currency = rateCard.currencyCode || "SEK";
  const total = ddrTotal + roomsTotal;
  const basis = hasAgreement
    ? `Rooms at ${agreement.name} negotiated rate; list DDR`
    : "List rates (no active agreement)";

  const out = {
    version, ddr, roomRate, meetingDays, total, currency, basis,
    ddrQty, ddrUnit: ddr, ddrTotal, ddrBasis: `list DDR x ${pax} pax x ${meetingDays} day(s)`,
    roomsQty: nights, roomsUnit: roomRate, roomsTotal, roomsBasis: `${roomBasis} x ${nights} room-nights`,
  };

  const snapshot = JSON.stringify({
    generatedAt: new Date().toISOString(),
    rateCard: rateCard.name,
    agreement: hasAgreement ? agreement.name : null,
    inputs: { delegates: pax, roomNights: nights, meetingDays },
    ...out,
  });

  return { ...out, snapshot };
};
