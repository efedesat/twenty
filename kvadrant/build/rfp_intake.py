#!/usr/bin/env python3
"""
Scandic Group & Meeting — AI RFP Intake panel (demo).
Paste an inbound RFP email -> Claude extracts a structured Enquiry + recommends a
best-fit Scandic hotel -> create it live in Twenty -> draft a proposal email back.

Run:  python3 build/rfp_intake.py     then open  http://localhost:8787
Needs: build/.env with ANTHROPIC_API_KEY ; build/.apikey (Twenty API key).
"""
import json, os, re, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
def _load_env():
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
_load_env()

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("RFP_MODEL", "claude-sonnet-4-6")
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

def hotels():
    return t_get("hotels?limit=50").get("data", {}).get("hotels", [])
def companies():
    return t_get("companies?limit=200").get("data", {}).get("companies", [])

# ---------- Claude ----------
def claude(system, user, max_tokens=1500):
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY missing — add it to build/.env")
    body = {"model": MODEL, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": user}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        return "".join(b.get("text", "") for b in resp.get("content", []))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Anthropic API {e.code}: {e.read().decode()[:300]}")

def extract_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}

# ---------- handlers ----------
def do_parse(email):
    hs = hotels()
    hotel_lines = "\n".join(
        f'- {h["name"]} ({h.get("city")}, {h.get("country")}); brand {h.get("brand")}; '
        f'largest room {h.get("largestRoomCapacity")} pax; {h.get("numberOfBedrooms")} bedrooms; '
        f'{h.get("totalMeetingM2")} m² meeting space; {h.get("distanceToAirportKm")} km to airport'
        for h in hs)
    system = (
        "You are the intake assistant for Scandic Hotels' Group & Meeting (MICE) sales team. "
        "Extract a structured enquiry from an inbound RFP email and recommend the single best-fit "
        "Scandic property from the list provided. Respond with STRICT JSON only, no prose.\n\n"
        "Available Scandic hotels:\n" + hotel_lines + "\n\n"
        'JSON shape:\n'
        '{ "name": "<short event name incl. year>", "accountName": "<booking company>", '
        '"segment": "CORPORATE|ASSOCIATION|GOVERNMENT|INCENTIVE|CONFERENCE|SOCIAL|SPORTS", '
        '"numberOfDelegates": <int>, "numberOfBedrooms": <int>, "roomNights": <int>, '
        '"eventStartDate": "YYYY-MM-DD", "eventEndDate": "YYYY-MM-DD", '
        '"dayDelegateRate": <int suggested DDR in local currency>, "currencyCode": "SEK|DKK|NOK|EUR", '
        '"estimatedTotalValue": <int>, "source": "DIRECT|CVENT_RFP|AGENCY|MICE_BID|REPEAT", '
        '"recommendedHotel": "<exact hotel name from the list>", '
        '"recommendationReason": "<one sentence why it fits>", '
        '"contactFirstName": "<sender first name>", "contactLastName": "<sender last name>", '
        '"contactEmail": "<sender email if present, else empty>", "contactJobTitle": "<sender job title>", '
        '"accountDomain": "<the booking company\'s web domain, e.g. telia.com — infer from the email address if present, otherwise from the company name>", '
        '"requirements": "<one-line summary of space/AV/F&B asks>", '
        '"confidence": "high|medium|low" }')
    data = extract_json(claude(system, f"Inbound RFP email:\n\n{email}"))
    data["_hotelMatch"] = next((h for h in hs if h["name"] == data.get("recommendedHotel")), None)
    return data

def _node(res):
    return next((v for v in res.get("data", {}).values() if isinstance(v, dict) and "id" in v), None) if "data" in res else None

def _norm_domain(s):
    if not s: return ""
    s = s.strip().lower()
    if "@" in s: s = s.split("@", 1)[1]
    return s.replace("https://", "").replace("http://", "").strip("/")

def _find_or_create_company(name, domain):
    domain = _norm_domain(domain)
    existing = companies()
    # 1) match by domain (the robust key) — aligns with the auto-create-company workflow
    if domain:
        for c in existing:
            if _norm_domain((c.get("domainName") or {}).get("primaryLinkUrl")) == domain:
                return c["id"]
    # 2) fall back to exact name
    if name:
        c = next((x for x in existing if x["name"].lower() == name.lower()), None)
        if c: return c["id"]
    if not name: return None
    body = {"name": name}
    if domain: body["domainName"] = {"primaryLinkUrl": f"https://{domain}"}
    return (_node(t_post("companies", body)) or {}).get("id")

def _guarantee_email(d):
    # email is mandatory downstream; synthesize a plausible one if the RFP had none
    email = (d.get("contactEmail") or "").strip()
    if email: return email
    fn = (d.get("contactFirstName") or "contact").strip().lower()
    ln = (d.get("contactLastName") or "").strip().lower()
    dom = _norm_domain(d.get("accountDomain")) or "example.com"
    local = f"{fn}.{ln}".strip(".") or "contact"
    return f"{local}@{dom}"

def _find_or_create_person(d, company_id):
    fn, ln = d.get("contactFirstName"), d.get("contactLastName")
    email = _guarantee_email(d)
    ppl = t_get("people?limit=200").get("data", {}).get("people", [])
    for p in ppl:
        if ((p.get("emails") or {}).get("primaryEmail") or "").lower() == email.lower(): return p["id"]
    full = f"{fn or ''} {ln or ''}".strip().lower()
    for p in ppl:
        nm = p.get("name") or {}
        if full and f"{nm.get('firstName','')} {nm.get('lastName','')}".strip().lower() == full: return p["id"]
    body = {"name": {"firstName": fn or "", "lastName": ln or ""}, "emails": {"primaryEmail": email}}
    if d.get("contactJobTitle"): body["jobTitle"] = d["contactJobTitle"]
    if company_id: body["companyId"] = company_id
    return (_node(t_post("people", body)) or {}).get("id")

def _file_email_note(email_text, event, opp_id, person_id, company_id):
    if not email_text: return False
    note = _node(t_post("notes", {"title": f"📧 Inbound RFP — {event}", "bodyV2": {"markdown": email_text}}))
    if not note: return False
    for key, val in [("targetOpportunityId", opp_id), ("targetPersonId", person_id), ("targetCompanyId", company_id)]:
        if val: t_post("noteTargets", {"noteId": note["id"], key: val})
    return True

def do_create(d):
    payload = {"name": d.get("name") or "New Enquiry", "stage": "LEAD"}
    for k in ("segment", "source", "numberOfDelegates", "roomNights", "numberOfBedrooms", "dayDelegateRate"):
        if d.get(k) not in (None, ""): payload[k] = d[k]
    for dk in ("eventStartDate", "eventEndDate"):
        if d.get(dk): payload[dk] = d[dk] + "T00:00:00.000Z"
    if d.get("estimatedTotalValue"):
        payload["amount"] = {"amountMicros": int(d["estimatedTotalValue"]) * 1_000_000, "currencyCode": d.get("currencyCode", "SEK")}
    payload["syncStatus"] = d.get("syncStatus", "PENDING")
    h = d.get("_hotelMatch") or next((x for x in hotels() if x["name"] == d.get("recommendedHotel")), None)
    if h: payload["hotelId"] = h["id"]
    company_id = _find_or_create_company(d.get("accountName"), d.get("accountDomain"))
    if company_id: payload["companyId"] = company_id
    person_id = _find_or_create_person(d, company_id)
    if person_id: payload["pointOfContactId"] = person_id
    node = _node(t_post("opportunities", payload))
    if not node: return {"ok": False, "error": "could not create enquiry"}
    filed = _file_email_note(d.get("_email", ""), payload["name"], node["id"], person_id, company_id)
    return {"ok": True, "id": node["id"], "url": f"{TWENTY_APP}/object/opportunity/{node['id']}",
            "filed": filed, "contact": person_id is not None}

def do_proposal(d):
    system = ("You are a senior Scandic Group & Meeting sales manager. Write a warm, professional, "
              "concise proposal email (Nordic business tone, ~180 words) responding to a client's RFP. "
              "Reference the recommended hotel, delegate count, dates, a suggested day-delegate rate, and "
              "invite a site inspection. Sign as 'Scandic Group & Meeting'. Plain text, no placeholders left blank.")
    return claude(system, "Enquiry details:\n" + json.dumps(d, ensure_ascii=False, indent=2), max_tokens=900)

SAMPLE = ("Subject: Conference enquiry - September 2026\n\n"
    "Hi,\n\nWe're organising our annual leadership conference for Telia Company and are looking for a "
    "venue in the Nordics. Approx 180 delegates, 2 nights (14-16 September 2026). We'll need a plenary "
    "room (theatre style), 3 breakout rooms, full-day catering both days and a gala dinner on the first "
    "evening. Around 150 bedrooms required. Natural daylight in the main room is important. Budget is "
    "flexible for the right property. Could you send a proposal?\n\nBest regards,\nMaria Lind\n"
    "Head of Events, Telia Company")

# ---------- web ----------
PAGE = """<!doctype html><html><head><meta charset=utf8><title>Scandic · AI RFP Intake</title>
<style>
:root{--red:#8C1C2B}
*{box-sizing:border-box;font-family:-apple-system,Segoe UI,Roboto,sans-serif}
body{margin:0;background:#f4f4f6;color:#1a1a1a}
header{background:var(--red);color:#fff;padding:16px 24px;display:flex;align-items:center;gap:12px}
header b{font-size:18px} header span{opacity:.8;font-size:13px}
.wrap{max-width:1100px;margin:24px auto;padding:0 24px;display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
h3{margin:0 0 12px;font-size:14px;text-transform:uppercase;letter-spacing:.5px;color:#666}
textarea{width:100%;height:300px;border:1px solid #ddd;border-radius:8px;padding:12px;font-size:13px;resize:vertical}
button{background:var(--red);color:#fff;border:0;border-radius:8px;padding:11px 18px;font-size:14px;font-weight:600;cursor:pointer}
button.alt{background:#fff;color:var(--red);border:1.5px solid var(--red)}
button:disabled{opacity:.5;cursor:wait}
.row{display:flex;gap:10px;margin-top:12px;flex-wrap:wrap}
.field{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:14px}
.field b{color:#555;font-weight:500} .chip{background:#fbe9ec;color:var(--red);padding:2px 10px;border-radius:20px;font-weight:600;font-size:13px}
.hotel{background:#fbf3e9;border:1px solid #f0d9b8;border-radius:8px;padding:12px;margin-top:10px;font-size:14px}
.ok{background:#e7f6ec;border:1px solid #b8e0c4;color:#1a7a3c;border-radius:8px;padding:12px;margin-top:10px;font-size:14px}
.muted{color:#999;font-size:13px} pre{white-space:pre-wrap;font-size:13px;line-height:1.5;background:#fafafa;border:1px solid #eee;border-radius:8px;padding:14px}
</style></head><body>
<header><b>Scandic Group &amp; Meeting</b><span>· AI RFP Intake</span></header>
<div class=wrap>
 <div class=card>
  <h3>1 · Inbound RFP email</h3>
  <textarea id=email>%SAMPLE%</textarea>
  <div class=row><button onclick=parse()>✨ Parse with AI</button>
   <button class=alt onclick="document.getElementById('email').value=''">Clear</button></div>
  <p class=muted id=status></p>
 </div>
 <div class=card>
  <h3>2 · Extracted enquiry</h3>
  <div id=fields class=muted>Paste an email and click <b>Parse with AI</b>.</div>
  <div id=hotel></div>
  <div class=row id=actions style=display:none>
   <button onclick=create()>➕ Create Enquiry in CRM</button>
   <button class=alt onclick=proposal()>✉️ Draft proposal</button>
  </div>
  <div id=created></div>
  <div id=prop></div>
 </div>
</div>
<script>
let parsed=null;
const S=document.getElementById('status');
async function parse(){
  S.textContent='Calling Claude…'; parsed=null;
  document.getElementById('fields').innerHTML='…';document.getElementById('hotel').innerHTML='';
  document.getElementById('actions').style.display='none';document.getElementById('created').innerHTML='';document.getElementById('prop').innerHTML='';
  try{
    const r=await fetch('/parse',{method:'POST',body:JSON.stringify({email:document.getElementById('email').value})});
    const d=await r.json(); if(d._err){S.textContent='Error: '+d._err;return;}
    parsed=d; render(d); S.textContent='Parsed ✓';
  }catch(e){S.textContent='Error: '+e}
}
function fld(k,v){return v==null||v===''?'':`<div class=field><b>${k}</b><span>${v}</span></div>`}
function render(d){
  let h=fld('Event',d.name)+`<div class=field><b>Account</b><span class=chip>${d.accountName||'—'}</span></div>`
   +fld('Segment',d.segment)+fld('Delegates',d.numberOfDelegates)+fld('Bedrooms',d.numberOfBedrooms)
   +fld('Room nights',d.roomNights)+fld('Dates',(d.eventStartDate||'')+' → '+(d.eventEndDate||''))
   +fld('Suggested DDR',(d.dayDelegateRate||'')+' '+(d.currencyCode||''))
   +fld('Est. value',(d.estimatedTotalValue?d.estimatedTotalValue.toLocaleString():'')+' '+(d.currencyCode||''))
   +fld('Source',d.source)+fld('Requirements',d.requirements);
  document.getElementById('fields').innerHTML=h;
  document.getElementById('hotel').innerHTML=d.recommendedHotel?
    `<div class=hotel>🏨 <b>Recommended: ${d.recommendedHotel}</b><br><span class=muted>${d.recommendationReason||''}</span></div>`:'';
  document.getElementById('actions').style.display='flex';
}
async function create(){
  S.textContent='Creating enquiry in Twenty…';
  parsed._email=document.getElementById('email').value;
  const r=await fetch('/create',{method:'POST',body:JSON.stringify(parsed)});const d=await r.json();
  if(d.ok){
    let extras=[];if(d.contact)extras.push('contact linked');if(d.filed)extras.push('email filed on timeline');
    document.getElementById('created').innerHTML=
     `<div class=ok>✅ Enquiry created${extras.length?' · '+extras.join(' · '):''}.<br><a href="${d.url}" target=_blank>Open in CRM →</a></div>`;
  }else{
    document.getElementById('created').innerHTML=`<div class=ok style=background:#fde8e8;color:#b00>Error: ${JSON.stringify(d.error)}</div>`;
  }
  S.textContent=d.ok?'Created ✓':'Create failed';
}
async function proposal(){
  S.textContent='Drafting proposal…';document.getElementById('prop').innerHTML='<p class=muted>…</p>';
  const r=await fetch('/proposal',{method:'POST',body:JSON.stringify(parsed)});const d=await r.json();
  document.getElementById('prop').innerHTML='<h3 style=margin-top:18px>Proposal draft</h3><pre>'+(d.text||d._err)+'</pre>';
  S.textContent='Drafted ✓';
}
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
    def do_GET(self):
        self._send(200, PAGE.replace("%SAMPLE%", SAMPLE), "text/html; charset=utf-8")
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or "{}")
        try:
            if self.path == "/parse": self._send(200, json.dumps(do_parse(body["email"])))
            elif self.path == "/create": self._send(200, json.dumps(do_create(body)))
            elif self.path == "/proposal": self._send(200, json.dumps({"text": do_proposal(body)}))
            else: self._send(404, "{}")
        except Exception as e:
            self._send(200, json.dumps({"_err": str(e)}))

if __name__ == "__main__":
    print("RFP Intake → http://localhost:8787   (model: %s, anthropic key: %s)" % (
        MODEL, "set" if ANTHROPIC_KEY else "MISSING — add to build/.env"))
    ThreadingHTTPServer(("127.0.0.1", 8787), H).serve_forever()
