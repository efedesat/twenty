#!/usr/bin/env python3
"""Idempotent schema builder for the Scandic Group & Meeting demo (metadata API)."""
import json, urllib.request, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, ".apikey")).read().strip()
META = "http://localhost:3000/metadata"

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(META, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def objects():
    d = gql("query{ objects(paging:{first:200}){ edges{ node{ id nameSingular fields(paging:{first:200}){ edges{ node{ name } } } } } } }")
    out = {}
    for e in d["data"]["objects"]["edges"]:
        n = e["node"]
        out[n["nameSingular"]] = {"id": n["id"],
            "fields": {f["node"]["name"] for f in n["fields"]["edges"]}}
    return out

def rename(obj_id, ls, lp):
    r = gql("mutation($id:UUID!,$u:UpdateObjectPayload!){ updateOneObject(input:{id:$id,update:$u}){ id labelSingular } }",
            {"id": obj_id, "u": {"labelSingular": ls, "labelPlural": lp}})
    print(("  rename->%s" % ls), "OK" if "data" in r and r["data"] else r.get("errors"))

def ensure_object(objs, ns, npl, ls, lp, icon):
    if ns in objs:
        print(f"object {ns}: exists"); return objs[ns]["id"]
    r = gql("mutation($o:CreateObjectInput!){ createOneObject(input:{object:$o}){ id } }",
            {"o": {"nameSingular": ns, "namePlural": npl, "labelSingular": ls, "labelPlural": lp, "icon": icon}})
    if "data" in r and r["data"]:
        print(f"object {ns}: CREATED"); return r["data"]["createOneObject"]["id"]
    print(f"object {ns}: ERROR", r.get("errors")); return None

def add_field(objs, obj_ns, obj_id, name, label, ftype, icon="IconTag", options=None, rel=None):
    if name in objs.get(obj_ns, {}).get("fields", set()):
        print(f"  {obj_ns}.{name}: exists"); return
    f = {"objectMetadataId": obj_id, "name": name, "label": label, "type": ftype, "icon": icon, "isNullable": True}
    if options:
        f["options"] = [{"label": l, "value": v, "color": c, "position": i} for i,(l,v,c) in enumerate(options)]
    if rel:
        f["relationCreationPayload"] = rel
    r = gql("mutation($f:CreateFieldInput!){ createOneField(input:{field:$f}){ id } }", {"f": f})
    print(f"  {obj_ns}.{name} ({ftype}):", "CREATED" if ("data" in r and r["data"]) else r.get("errors"))

def main():
    objs = objects()
    # --- rename standard objects (labels only) ---
    print("== renames ==")
    rename(objs["company"]["id"], "Account", "Accounts")
    rename(objs["person"]["id"], "Contact", "Contacts")
    rename(objs["opportunity"]["id"], "Enquiry", "Enquiries")
    # --- create custom objects ---
    print("== objects ==")
    ids = {ns: objs[ns]["id"] for ns in ("hotel","meetingRoom","opportunity","company","person") if ns in objs}
    ids["roomBlock"] = ensure_object(objs, "roomBlock","roomBlocks","Room Block","Room Blocks","IconBed")
    ids["quote"] = ensure_object(objs, "quote","quotes","Quote","Quotes","IconFileInvoice")
    ids["corporateAgreement"] = ensure_object(objs, "corporateAgreement","corporateAgreements","Corporate Agreement","Corporate Agreements","IconContract")
    ids["eventFeedback"] = ensure_object(objs, "eventFeedback","eventFeedbacks","Event Feedback","Event Feedbacks","IconStar")
    ids["rateCard"] = ensure_object(objs, "rateCard","rateCards","Rate Card","Rate Cards","IconReportMoney")
    ids["quoteLine"] = ensure_object(objs, "quoteLine","quoteLines","Quote Line","Quote Lines","IconListDetails")
    objs = objects()  # refresh after creating objects
    def F(ns, *a, **k): add_field(objs, ns, ids[ns], *a, **k)
    def REL(target): return {"type":"MANY_TO_ONE","targetObjectMetadataId":ids[target[0]],"targetFieldLabel":target[1],"targetFieldIcon":target[2]}

    print("== Enquiry fields ==")
    F("opportunity","source","Source","SELECT",icon="IconArrowDown",options=[("Direct","DIRECT","green"),("Cvent RFP","CVENT_RFP","blue"),("Agency","AGENCY","purple"),("MICE Bid","MICE_BID","orange"),("Repeat","REPEAT","turquoise")])
    F("opportunity","syncStatus","OPERA Sync","SELECT",icon="IconRefresh",options=[("Synced","SYNCED","green"),("Pending","PENDING","yellow"),("Not Synced","NOT_SYNCED","gray")])
    F("opportunity","enquiryType","Enquiry Type","SELECT",icon="IconCategory",options=[("Full MICE","FULL_MICE","blue"),("Accommodation Only","ACCOMMODATION_ONLY","green"),("Venue Only","VENUE_ONLY","purple")])
    for n,l in [("numberOfDelegates","Delegates (pax)"),("roomNights","Room Nights"),("numberOfBedrooms","Bedrooms"),("dayDelegateRate","Day Delegate Rate"),("meetingRoomRevenue","Meeting Room Revenue"),("fbRevenue","F&B Revenue"),("bedroomRevenue","Bedroom Revenue")]:
        F("opportunity",n,l,"NUMBER",icon="IconNumber")
    for n,l in [("eventStartDate","Event Start"),("eventEndDate","Event End"),("tentativeHoldExpiry","Tentative Hold Expiry"),("decisionDate","Decision Date"),("cutOffDate","Cut-off Date")]:
        F("opportunity",n,l,"DATE_TIME",icon="IconCalendar")
    for n,l in [("winLossReason","Win/Loss Reason"),("competitorHotel","Competitor Hotel"),("operaBlockCode","OPERA Block Code"),("operaConfirmationNo","OPERA Confirmation #")]:
        F("opportunity",n,l,"TEXT",icon="IconFileText")

    print("== Hotel fields ==")
    F("hotel","country","Country","TEXT",icon="IconFlag")
    for n,l in [("totalMeetingM2","Total Meeting m²"),("largestRoomCapacity","Largest Room Capacity"),("numberOfBedrooms","Bedrooms"),("numberOfMeetingRooms","Meeting Rooms"),("distanceToAirportKm","Distance to Airport (km)")]:
        F("hotel",n,l,"NUMBER",icon="IconNumber")
    F("hotel","sustainabilityCert","Sustainability Cert","TEXT",icon="IconLeaf")

    print("== Meeting Room fields ==")
    for n,l in [("sizeM2","Size m²"),("capacityTheatre","Theatre"),("capacityClassroom","Classroom"),("capacityBanquet","Banquet"),("capacityBoardroom","Boardroom"),("capacityReception","Reception"),("fullDayHire","Full-day Hire")]:
        F("meetingRoom",n,l,"NUMBER",icon="IconNumber")
    F("meetingRoom","naturalDaylight","Natural Daylight","BOOLEAN",icon="IconSun")

    print("== Room Block fields ==")
    F("roomBlock","hotel","Hotel","RELATION",icon="IconBuilding",rel=REL(("hotel","Room Blocks","IconBed")))
    F("roomBlock","enquiry","Enquiry","RELATION",icon="IconCalendarEvent",rel=REL(("opportunity","Room Blocks","IconBed")))
    for n,l in [("roomsPerNight","Rooms / Night"),("nights","Nights"),("ratePerNight","Rate / Night"),("pickup","Pickup")]:
        F("roomBlock",n,l,"NUMBER",icon="IconNumber")
    F("roomBlock","cutOffDate","Cut-off Date","DATE_TIME",icon="IconCalendar")
    F("roomBlock","operaBlockId","OPERA Block ID","TEXT",icon="IconFileText")

    print("== Quote fields ==")
    F("quote","enquiry","Enquiry","RELATION",icon="IconCalendarEvent",rel=REL(("opportunity","Quotes","IconFileInvoice")))
    for n,l in [("version","Version"),("totalValue","Total Value"),("dayDelegateRateOffered","DDR Offered")]:
        F("quote",n,l,"NUMBER",icon="IconNumber")
    F("quote","validUntil","Valid Until","DATE_TIME",icon="IconCalendar")
    F("quote","pricingSnapshot","Pricing Snapshot","TEXT",icon="IconJson")
    F("quote","status","Status","SELECT",icon="IconStatusChange",options=[("Draft","DRAFT","gray"),("Pending Approval","PENDING_APPROVAL","yellow"),("Approved","APPROVED","turquoise"),("Sent","SENT","blue"),("Accepted","ACCEPTED","green"),("Declined","DECLINED","red")])

    print("== Corporate Agreement fields ==")
    F("corporateAgreement","account","Account","RELATION",icon="IconBuilding",rel=REL(("company","Corporate Agreements","IconContract")))
    for n,l in [("agreementYear","Year"),("negotiatedRoomRate","Negotiated Room Rate"),("roomNightCommitment","Room-night Commitment"),("roomNightsActualised","Room Nights Actualised"),("discountPct","Discount %")]:
        F("corporateAgreement",n,l,"NUMBER",icon="IconNumber")
    F("corporateAgreement","renewalDate","Renewal Date","DATE_TIME",icon="IconCalendar")
    F("corporateAgreement","status","Status","SELECT",icon="IconStatusChange",options=[("Active","ACTIVE","green"),("Negotiating","NEGOTIATING","yellow"),("Expired","EXPIRED","gray")])

    print("== Event Feedback fields ==")
    F("eventFeedback","enquiry","Enquiry","RELATION",icon="IconCalendarEvent",rel=REL(("opportunity","Event Feedback","IconStar")))
    F("eventFeedback","npsScore","NPS Score","NUMBER",icon="IconStar")
    F("eventFeedback","comments","Comments","TEXT",icon="IconMessage")
    F("eventFeedback","wouldRebook","Would Rebook","BOOLEAN",icon="IconCheck")

    print("== Rate Card fields ==")
    F("rateCard","hotel","Hotel","RELATION",icon="IconBuilding",rel=REL(("hotel","Rate Cards","IconReportMoney")))
    for n,l in [("listDayDelegateRate","List DDR"),("listRoomNightRate","List Room-night Rate")]:
        F("rateCard",n,l,"NUMBER",icon="IconNumber")
    F("rateCard","currencyCode","Currency","SELECT",icon="IconCurrency",options=[("SEK","SEK","blue"),("DKK","DKK","green"),("NOK","NOK","purple"),("EUR","EUR","orange")])
    F("rateCard","validFrom","Valid From","DATE_TIME",icon="IconCalendar")

    print("== Quote Line fields ==")
    F("quoteLine","quote","Quote","RELATION",icon="IconFileInvoice",rel=REL(("quote","Quote Lines","IconListDetails")))
    F("quoteLine","lineType","Line Type","SELECT",icon="IconCategory",options=[("Day Delegate","DDR","blue"),("Room Night","ROOM_NIGHT","green"),("Room Hire","ROOM_HIRE","purple"),("F&B","FB","orange")])
    for n,l in [("quantity","Quantity"),("unitRate","Unit Rate"),("lineTotal","Line Total")]:
        F("quoteLine",n,l,"NUMBER",icon="IconNumber")
    F("quoteLine","basis","Pricing Basis","TEXT",icon="IconFileText")
    print("DONE")

main()
