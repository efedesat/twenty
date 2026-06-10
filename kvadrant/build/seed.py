#!/usr/bin/env python3
"""Seed Scandic demo data via REST, resolving name-refs to IDs in dependency order."""
import json, urllib.request, urllib.error, time, os

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, ".apikey")).read().strip()
BASE = "http://localhost:3000/rest"
DATA = os.path.join(HERE, "..", "demo-data")
H = {"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(6):
        time.sleep(0.7)  # throttle: stay under 100 req / 60s
        r = urllib.request.Request(BASE + path, data=data, headers=H, method=method)
        try:
            with urllib.request.urlopen(r) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("    429 rate-limited; waiting 20s..."); time.sleep(20); continue
            return {"_error": e.code, "_msg": e.read().decode()[:200]}
    return {"_error": 429, "_msg": "rate limit retries exhausted"}

def load(name): return json.load(open(f"{DATA}/{name}.json"))

def D(v):  # normalize date -> ISO datetime
    if not v: return None
    return v if "T" in v else v + "T00:00:00.000Z"

def wipe(plural):
    n = 0
    while True:
        d = req("GET", f"/{plural}?limit=200")
        recs = d.get("data", {}).get(plural, [])
        if not recs: break
        for rec in recs:
            req("DELETE", f"/{plural}/{rec['id']}"); n += 1
        if len(recs) < 200: break
    return n

def seed(plural, rows):
    ids = {}
    ok = err = 0
    for row in rows:
        key = row.pop("_key", None)
        if key is None and isinstance(row.get("name"), str):
            key = row["name"]
        d = req("POST", f"/{plural}", row)
        # REST returns {"data": {"createOpportunity": {...}}} OR {"data":{...}} — handle both
        node = None
        if "data" in d and isinstance(d["data"], dict):
            for v in d["data"].values():
                if isinstance(v, dict) and "id" in v: node = v; break
        if node:
            ok += 1
            if key: ids[key] = node["id"]
        else:
            err += 1
            print(f"  ERR {plural} '{key}':", d.get("_error"), d.get("_msg", d))
    print(f"{plural}: {ok} created, {err} errors")
    return ids

print("== WIPE existing demo records ==")
for p in ["quoteLines","opportunities","hotels","meetingRooms","roomBlocks","quotes","corporateAgreements","eventFeedbacks","rateCards","people","companies"]:
    print(f"  wiped {p}: {wipe(p)}")

# ---- companies (Accounts) ----
acc_rows = [{"name":a["name"], "employees":a.get("employees"),
             "domainName":{"primaryLinkUrl":"https://"+a["domainName"]} if a.get("domainName") else None,
             "segment":a.get("segment"), "city":a.get("city"), "country":a.get("country")}
            for a in load("accounts")]
acc = seed("companies", [{k:v for k,v in r.items() if v is not None} for r in acc_rows])

# ---- hotels ----
hot = seed("hotels", load("hotels"))

# ---- rate cards ----
rc_rows = []
for c in load("rateCards"):
    r = {k:c.get(k) for k in ("name","listDayDelegateRate","listRoomNightRate","currencyCode")}
    r["validFrom"] = D(c.get("validFrom"))
    if c.get("hotelRef") in hot: r["hotelId"] = hot[c["hotelRef"]]
    rc_rows.append({k:v for k,v in r.items() if v is not None})
seed("rateCards", rc_rows)

# ---- contacts (People) ----
ppl_rows = []
for c in load("contacts"):
    r = {"name":{"firstName":c["firstName"],"lastName":c["lastName"]},
         "jobTitle":c.get("jobTitle"), "contactRole":c.get("role"),
         "_key": f'{c["firstName"]} {c["lastName"]}'}
    if c.get("email"): r["emails"] = {"primaryEmail": c["email"]}
    if c.get("phone"): r["phones"] = {"primaryPhoneNumber": c["phone"]}  # let country infer from +prefix (Nordic numbers conflict with a forced SE)
    if c.get("accountRef") in acc: r["companyId"] = acc[c["accountRef"]]
    ppl_rows.append({k:v for k,v in r.items() if v is not None})
seed("people", ppl_rows)

# ---- meeting rooms ----
mr_rows = []
for m in load("meetingRooms"):
    r = {k:m.get(k) for k in ("name","sizeM2","capacityTheatre","capacityClassroom","capacityBanquet","capacityBoardroom","capacityReception","naturalDaylight","fullDayHire")}
    if m.get("hotelRef") in hot: r["hotelId"] = hot[m["hotelRef"]]
    mr_rows.append({k:v for k,v in r.items() if v is not None})
seed("meetingRooms", mr_rows)

# ---- corporate agreements ----
ca_rows = []
for a in load("corporateAgreements"):
    r = {k:a.get(k) for k in ("name","agreementYear","negotiatedRoomRate","roomNightCommitment","roomNightsActualised","discountPct","status")}
    r["renewalDate"] = D(a.get("renewalDate"))
    if a.get("accountRef") in acc: r["accountId"] = acc[a["accountRef"]]
    ca_rows.append({k:v for k,v in r.items() if v is not None})
seed("corporateAgreements", ca_rows)

# ---- enquiries (Opportunities) ----
enq_rows = []
for e in load("enquiries"):
    r = {k:e.get(k) for k in ("name","stage","segment","source","syncStatus","enquiryType","numberOfDelegates","roomNights","numberOfBedrooms","dayDelegateRate","meetingRoomRevenue","fbRevenue","bedroomRevenue","winLossReason","competitorHotel","operaBlockCode","operaConfirmationNo")}
    if r.get("enquiryType") is None: r["enquiryType"] = "FULL_MICE"  # default; gate refines later
    if e.get("totalValue"): r["amount"] = {"amountMicros": int(e["totalValue"])*1_000_000, "currencyCode": e.get("currencyCode","SEK")}
    for dk in ("eventStartDate","eventEndDate","tentativeHoldExpiry","decisionDate","cutOffDate"):
        if e.get(dk): r[dk] = D(e[dk])
    if e.get("hotelRef") in hot: r["hotelId"] = hot[e["hotelRef"]]
    if e.get("accountRef") in acc: r["companyId"] = acc[e["accountRef"]]
    enq_rows.append({k:v for k,v in r.items() if v is not None})
enq = seed("opportunities", enq_rows)

# ---- quotes ----
q_rows = []
for q in load("quotes"):
    r = {k:q.get(k) for k in ("name","version","totalValue","dayDelegateRateOffered","status")}
    r["validUntil"] = D(q.get("validUntil"))
    if q.get("enquiryRef") in enq: r["enquiryId"] = enq[q["enquiryRef"]]
    q_rows.append({k:v for k,v in r.items() if v is not None})
seed("quotes", q_rows)

# ---- room blocks ----
rb_rows = []
for b in load("roomBlocks"):
    r = {k:b.get(k) for k in ("name","roomsPerNight","nights","ratePerNight","pickup","operaBlockId")}
    r["cutOffDate"] = D(b.get("cutOffDate"))
    if b.get("hotelRef") in hot: r["hotelId"] = hot[b["hotelRef"]]
    if b.get("enquiryRef") in enq: r["enquiryId"] = enq[b["enquiryRef"]]
    rb_rows.append({k:v for k,v in r.items() if v is not None})
seed("roomBlocks", rb_rows)

# ---- event feedback ----
fb_rows = []
for f in load("eventFeedback"):
    r = {k:f.get(k) for k in ("name","npsScore","comments","wouldRebook")}
    if f.get("enquiryRef") in enq: r["enquiryId"] = enq[f["enquiryRef"]]
    fb_rows.append({k:v for k,v in r.items() if v is not None})
seed("eventFeedbacks", fb_rows)
print("SEED DONE")
