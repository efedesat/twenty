#!/usr/bin/env python3
"""
Scandic Group & Meeting — deterministic (NO-AI) pricing engine.

Reference implementation of the Meetings & Events pricing math + a CLI that reads an
Enquiry (+ its Hotel's Rate Card + the account's active Corporate Agreement) from Twenty,
computes a Quote with itemised Quote Lines, and writes them back via REST.

Same inputs -> same number, every time. No Anthropic key, no .env needed.

Usage:
    python3 build/quote_engine.py "Ericsson Leadership Forum Q3 2026"
    python3 build/quote_engine.py "Volvo Group AGM 2026" --dry-run   # compute + print only

The pure function compute_quote() is mirrored verbatim by build/quote_logic_function.js,
which runs inside the native Twenty "Generate Quote" workflow code step.
"""
import json, os, sys, urllib.request, urllib.error
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TWENTY = "http://localhost:3000/rest"
TWENTY_KEY = open(os.path.join(HERE, ".apikey")).read().strip()
TWENTY_APP = "http://localhost:3000"


# ---------- Twenty REST ----------
def t_get(path):
    r = urllib.request.Request(f"{TWENTY}/{path}", headers={"Authorization": f"Bearer {TWENTY_KEY}"})
    return json.loads(urllib.request.urlopen(r).read())


def t_post(path, body):
    r = urllib.request.Request(f"{TWENTY}/{path}", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TWENTY_KEY}", "Content-Type": "application/json"}, method="POST")
    try:
        return json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:300]}


def _list(plural):
    return t_get(f"{plural}?limit=200").get("data", {}).get(plural, [])


def _node(resp):
    if "data" in resp and isinstance(resp["data"], dict):
        for v in resp["data"].values():
            if isinstance(v, dict) and "id" in v:
                return v
    return None


def _rel_id(rec, field):
    """Twenty REST may return a relation as '<field>Id' or as a nested {'<field>': {'id': ...}}."""
    if rec.get(f"{field}Id"):
        return rec[f"{field}Id"]
    sub = rec.get(field)
    if isinstance(sub, dict):
        return sub.get("id")
    return None


# ---------- pure pricing math (mirrored in quote_logic_function.js) ----------
def _meeting_days(start, end):
    """Days between event start/end (inclusive of at least 1). Accepts ISO date or datetime strings."""
    if not start:
        return 1
    s = date.fromisoformat(start[:10])
    e = date.fromisoformat(end[:10]) if end else s
    return max(1, (e - s).days)


def compute_quote(enquiry, rate_card, agreement):
    """
    Pure, deterministic. MINIMAL rules (v1):
      ddr      = rate_card.listDayDelegateRate                 (list; no DDR discount yet)
      roomRate = agreement.negotiatedRoomRate if active else rate_card.listRoomNightRate
      total    = ddr*delegates*meetingDays + roomRate*roomNights
    Returns dict: {ddr, roomRate, meetingDays, lines[], total, basis, currency}.
    Door left open: volume / season / floor + enquiryType line-gating (see PROJECT plan).
    """
    if not rate_card:
        raise ValueError("no rate card for this enquiry's hotel")
    delegates = int(enquiry.get("numberOfDelegates") or 0)
    room_nights = int(enquiry.get("roomNights") or 0)
    meeting_days = _meeting_days(enquiry.get("eventStartDate"), enquiry.get("eventEndDate"))

    ddr = int(rate_card["listDayDelegateRate"])
    list_room = int(rate_card["listRoomNightRate"])
    has_agreement = bool(agreement and agreement.get("status") == "ACTIVE" and agreement.get("negotiatedRoomRate"))
    room_rate = int(agreement["negotiatedRoomRate"]) if has_agreement else list_room
    room_basis = (f"{agreement['name']} negotiated rate" if has_agreement
                  else "list room-night rate (no active agreement)")

    ddr_line = ddr * delegates * meeting_days
    rooms_line = room_rate * room_nights
    total = ddr_line + rooms_line

    lines = [
        {"lineType": "DDR", "quantity": delegates * meeting_days, "unitRate": ddr,
         "lineTotal": ddr_line, "basis": f"list DDR x {delegates} pax x {meeting_days} day(s)"},
        {"lineType": "ROOM_NIGHT", "quantity": room_nights, "unitRate": room_rate,
         "lineTotal": rooms_line, "basis": f"{room_basis} x {room_nights} room-nights"},
    ]
    basis = (f"Rooms at {agreement['name']} negotiated rate; list DDR" if has_agreement
             else "List rates (no active agreement)")
    return {"ddr": ddr, "roomRate": room_rate, "meetingDays": meeting_days,
            "lines": lines, "total": total, "basis": basis, "currency": rate_card.get("currencyCode", "SEK")}


# ---------- I/O: fetch -> compute -> write ----------
def find_enquiry(name):
    for e in _list("opportunities"):
        if e.get("name") == name:
            return e
    return None


def rate_card_for(hotel_id):
    for c in _list("rateCards"):
        if _rel_id(c, "hotel") == hotel_id:
            return c
    return None


def active_agreement_for(account_id):
    cand = [a for a in _list("corporateAgreements")
            if _rel_id(a, "account") == account_id and a.get("status") == "ACTIVE"]
    return cand[0] if cand else None


def next_version(enquiry_id):
    versions = [int(q.get("version") or 0) for q in _list("quotes") if _rel_id(q, "enquiry") == enquiry_id]
    return (max(versions) + 1) if versions else 1


def generate(enquiry_name, dry_run=False):
    enq = find_enquiry(enquiry_name)
    if not enq:
        print(f"ERROR: no enquiry named {enquiry_name!r}"); return 1
    hotel_id = _rel_id(enq, "hotel")
    account_id = _rel_id(enq, "company")
    rc = rate_card_for(hotel_id)
    ag = active_agreement_for(account_id)
    if not rc:
        print(f"ERROR: no rate card found for enquiry's hotel (hotelId={hotel_id})"); return 1

    res = compute_quote(enq, rc, ag)
    cur = res["currency"]
    print(f"\n  Enquiry : {enquiry_name}")
    print(f"  Rate card: {rc['name']}")
    print(f"  Agreement: {ag['name'] if ag else '(none active)'}")
    print(f"  Days     : {res['meetingDays']}   DDR: {res['ddr']} {cur}   Room rate: {res['roomRate']} {cur}")
    print("  " + "-" * 56)
    for ln in res["lines"]:
        print(f"  {ln['lineType']:<11} {ln['quantity']:>6} x {ln['unitRate']:>6} = {ln['lineTotal']:>12,} {cur}   [{ln['basis']}]")
    print("  " + "-" * 56)
    print(f"  {'TOTAL':<11} {res['total']:>30,} {cur}")
    print(f"  Basis    : {res['basis']}\n")

    if dry_run:
        print("  (dry-run: nothing written)\n"); return 0

    ver = next_version(enq["id"])
    snapshot = json.dumps({"rateCard": rc["name"], "agreement": ag["name"] if ag else None,
                           "version": ver, **res})
    q_payload = {"name": f"{enquiry_name} – Quote v{ver}", "version": ver,
                 "totalValue": res["total"], "dayDelegateRateOffered": res["ddr"],
                 "status": "PENDING_APPROVAL", "pricingSnapshot": snapshot, "enquiryId": enq["id"]}
    qnode = _node(t_post("quotes", q_payload))
    if not qnode:
        print("ERROR: failed to create quote"); return 1
    for ln in res["lines"]:
        t_post("quoteLines", {"name": f"{ln['lineType']} – v{ver}", "quoteId": qnode["id"], **ln})
    print(f"  Created Quote v{ver} + {len(res['lines'])} lines")
    print(f"  {TWENTY_APP}/object/quote/{qnode['id']}\n")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    sys.exit(generate(args[0], dry_run="--dry-run" in sys.argv))
