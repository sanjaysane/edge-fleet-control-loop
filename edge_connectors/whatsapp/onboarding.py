"""
WhatsApp Edge Registration — parity to device_onboarding.py for hardware

You asked: same pipeline as device registration, but for people.

Hardware flow (existing):
  unclaimed device -> QR claim -> device_onboarding.py adds to devices.json -> sends desired fw v1 -> telemetry starts

WhatsApp flow (new, same steps):
  unknown WA -> says "START"/"HELLO"/"नमस्कार" -> onboard -> hello+welcome+commands -> desired prompt v1 -> collection
"""

import pathlib, json, time, sys
ROOT=pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from connector import wa_device_id, simulate_desired

ONBOARD=ROOT/"control_plane"/"data"/"whatsapp_onboarded.json"
ONBOARD.parent.mkdir(parents=True, exist_ok=True)

WELCOME_TEXT = """नमस्कार! 👋 Welcome to BP Check edge

You're now registered as a human edge device — same pipeline as a BP monitor, just on WhatsApp.

Sku: whatsapp-human-v1 | id: {dev_id}

What I collect (same lake as hardware):
- Your BP as 120/80 or १२०/८० or photo of cuff — stripped to numbers only
- Count + streak, nothing else leaves your chat

Commands (pull-based, works anytime):
STATUS / SUMMARY — your last reading, streak, trend, 7-day avg
GLOBAL — cohort avg last 7d (anon, {devices_seen} devices, {g_count} readings)
DASH — your personal page link (own numbers + global box)
HELP — this list

Push-based:
- Daily 8:30 AM PDT I'll push prompt (you can say STOP to pause, START to resume)
- You reply 120/80 -> I close loop same as device telemetry

Type STATUS to see sample.
"""

def is_onboarding_intent(text: str) -> bool:
    t=(text or "").strip().lower()
    return any(k in t for k in ("start","hello","hi","join","नमस्कार","सुरू","onboard"))

def onboard_contact(wa_name: str, consent=True):
    db=json.loads(ONBOARD.read_text()) if ONBOARD.exists() else {}
    did=wa_device_id(wa_name)
    if did in db:
        return {"ok":True,"device_id":did,"already":True,"wa_name":wa_name}
    db[did]={"wa_name":wa_name,"onboarded_at":time.time(),"sku":"whatsapp-human-v1","consent":consent,"status":"active"}
    ONBOARD.write_text(json.dumps(db, indent=2))
    return {"ok":True,"device_id":did,"already":False,"wa_name":wa_name}

def make_welcome(wa_name: str, dev_id: str, g_count=0, devices_seen=0):
    return WELCOME_TEXT.format(dev_id=dev_id[:12], g_count=g_count, devices_seen=devices_seen)

def handle_inbound(wa_name: str, text: str, dry_run=True):
    """
    Entry for control plane /api/v1/whatsapp/command when onboarding not yet done
    Returns dict with what would be sent
    """
    if not is_onboarding_intent(text) and wa_device_id(wa_name) not in (json.loads(ONBOARD.read_text()) if ONBOARD.exists() else {}):
        return {"type":"need_onboard","reply":"Say START / नमस्कार to join BP check edge — same as device claim."}
    # onboarding
    res=onboard_contact(wa_name)
    if not res["already"]:
        # fresh welcome
        welcome=make_welcome(wa_name, res["device_id"], g_count=6, devices_seen=2)
        # In live mode you'd send via hatch_wai_cli send
        return {"type":"welcome","device_id":res["device_id"],"reply":welcome,"should_send":welcome if not dry_run else None}
    # already onboarded — delegate to interactive handler
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from interactive import handle_whatsapp_command
    cmd=handle_whatsapp_command(wa_name, text)
    if cmd:
        return {"type":"command","reply":cmd}
    # else it's data
    from connector import ingest_reply
    rec=ingest_reply(wa_name, text)
    return {"type":"data","parsed":rec["payload"]["parsed"],"device_id":rec["device_id"]}

if __name__=="__main__":
    for msg in ["hello","STATUS","120/80"]:
        print("\nIN:", msg)
        print(handle_inbound("Demo WA", msg, dry_run=True))
