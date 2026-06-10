#!/usr/bin/env python3
"""Generate SQL to enrich TABLE/KANBAN view columns for the Scandic demo.
Hides noisy system columns; surfaces business + relationship fields. Pipe stdout to psql."""

APP = "2f43416d-1f60-47bf-99c2-9abaf953172e"  # workspace standard application id

# object nameSingular -> ordered list of field names to show as columns
COLS = {
 "company":     ["segment","domainName","employees","city","country"],
 "person":      ["jobTitle","contactRole","emails","company"],
 "opportunity": ["stage","amount","company","hotel","enquiryType","numberOfDelegates","eventStartDate","source","syncStatus"],
 "hotel":       ["city","country","brand","largestRoomCapacity","numberOfBedrooms","totalMeetingM2","meetingRooms","enquiries"],
 "meetingRoom": ["hotel","sizeM2","capacityTheatre","capacityClassroom","capacityBanquet","naturalDaylight","fullDayHire"],
 "roomBlock":   ["enquiry","hotel","roomsPerNight","nights","ratePerNight","pickup","cutOffDate","operaBlockId"],
 "quote":       ["enquiry","status","version","totalValue","dayDelegateRateOffered","quoteLines","validUntil"],
 "rateCard":    ["hotel","listDayDelegateRate","listRoomNightRate","currencyCode","validFrom"],
 "quoteLine":   ["quote","lineType","quantity","unitRate","lineTotal","basis"],
 "corporateAgreement": ["account","status","agreementYear","negotiatedRoomRate","roomNightCommitment","roomNightsActualised","discountPct","renewalDate"],
 "eventFeedback":["enquiry","npsScore","wouldRebook","comments"],
}

print("BEGIN;")
for obj, fields in COLS.items():
    # hide noisy system columns
    print(f"""update core."viewField" vf set "isVisible"=false
from core.view v join core."objectMetadata" o on o.id=v."objectMetadataId"
where vf."viewId"=v.id and o."nameSingular"='{obj}' and v.type in ('TABLE','KANBAN')
 and vf."fieldMetadataId" in (select id from core."fieldMetadata" fm where fm."objectMetadataId"=o.id and fm.name in ('createdBy','updatedBy','updatedAt'));""")
    # push createdAt to the end (keep visible)
    print(f"""update core."viewField" vf set position=90
from core.view v join core."objectMetadata" o on o.id=v."objectMetadataId"
where vf."viewId"=v.id and o."nameSingular"='{obj}' and v.type in ('TABLE','KANBAN')
 and vf."fieldMetadataId" in (select id from core."fieldMetadata" fm where fm."objectMetadataId"=o.id and fm.name='createdAt');""")
    for i, f in enumerate(fields, start=1):
        # if column already present -> make visible + position it
        print(f"""update core."viewField" vf set "isVisible"=true, position={i}
from core.view v join core."objectMetadata" o on o.id=v."objectMetadataId"
join core."fieldMetadata" fm on fm."objectMetadataId"=o.id and fm.name='{f}'
where vf."viewId"=v.id and vf."fieldMetadataId"=fm.id and o."nameSingular"='{obj}' and v.type in ('TABLE','KANBAN');""")
        # else insert it
        print(f"""insert into core."viewField" (id,"universalIdentifier","fieldMetadataId","isVisible",size,position,"viewId","workspaceId","isActive","applicationId")
select gen_random_uuid(),gen_random_uuid(),fm.id,true,160,{i},v.id,fm."workspaceId",true,'{APP}'
from core.view v join core."objectMetadata" o on o.id=v."objectMetadataId" and o."nameSingular"='{obj}'
join core."fieldMetadata" fm on fm."objectMetadataId"=o.id and fm.name='{f}'
where v.type in ('TABLE','KANBAN')
 and not exists (select 1 from core."viewField" x where x."viewId"=v.id and x."fieldMetadataId"=fm.id);""")
print("COMMIT;")
