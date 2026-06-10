#!/usr/bin/env python3
import json, urllib.request, urllib.error, time, os
HERE=os.path.dirname(os.path.abspath(__file__))
KEY=open(os.path.join(HERE,".apikey")).read().strip()
BASE="http://localhost:3000/rest"; H={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"}
def req(method,path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    for _ in range(6):
        time.sleep(0.7)
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=H,method=method)) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(20); continue
            return {"_error":e.code,"_msg":e.read().decode()[:160]}
    return {"_error":429}
# company name->id
acc={}
d=req("GET","/companies?limit=200")
for c in d.get("data",{}).get("companies",[]): acc[c["name"]]=c["id"]
# wipe people, reseed without forced country code
while True:
    d=req("GET","/people?limit=200"); recs=d.get("data",{}).get("people",[])
    if not recs: break
    for r in recs: req("DELETE",f"/people/{r['id']}")
ok=err=0
for c in json.load(open(os.path.join(HERE,"..","demo-data","contacts.json"))):
    r={"name":{"firstName":c["firstName"],"lastName":c["lastName"]},"jobTitle":c.get("jobTitle"),"contactRole":c.get("role")}
    if c.get("email"): r["emails"]={"primaryEmail":c["email"]}
    if c.get("phone"): r["phones"]={"primaryPhoneNumber":c["phone"]}  # let country infer
    if c.get("accountRef") in acc: r["companyId"]=acc[c["accountRef"]]
    r={k:v for k,v in r.items() if v is not None}
    res=req("POST","/people",r)
    node=None
    if isinstance(res.get("data"),dict):
        for v in res["data"].values():
            if isinstance(v,dict) and "id" in v: node=v;break
    if node: ok+=1
    else: err+=1; print("ERR",c["firstName"],c["lastName"],res.get("_msg",res))
print(f"people: {ok} created, {err} errors")
