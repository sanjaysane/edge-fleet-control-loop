"""
Workflow you asked: WhatsApp as interface to edge human — last Mile collection + ask for imports

Same as canary_deploy / device_onboarding patterns but for people.

Flow:
1. Onboard: list waits for "START" from real chat (existing chats only, no cold-messaging)
2. Canary: prompt v2 Marathi phrasing you prefer — test on 5% of contacts first (e.g., 1 of 20)
3. Daily ask: ask for BP photo/import -> ingest -> same pipeline as hardware
4. Telemetry dashboard sees both sku=bp-monitor-v1 (hw) and sku=whatsapp-human-v1 (people)
"""

import pathlib, json, sys, time, os
ROOT=pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from connector import wa_device_id, simulate_desired, send_whatsapp, ingest_reply, parse_human_bp

ONBOARD_FILE=ROOT/"control_plane"/"data"/"whatsapp_onboarded.json"

def onboard(wa_name: str):
    ONBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    db=json.loads(ONBOARD_FILE.read_text()) if ONBOARD_FILE.exists() else {}
    db[wa_device_id(wa_name)]={"wa_name":wa_name,"onboarded_at":time.time(),"sku":"whatsapp-human-v1"}
    ONBOARD_FILE.write_text(json.dumps(db, indent=2))
    return db

def push_campaign(wa_list, prompt_version="prompt-v2-marathi", dry_run=True, canary_pct=5):
    import math
    n_canary=max(1, math.ceil(len(wa_list)*canary_pct/100))
    canary=wa_list[:n_canary]
    print(f"Campaign {prompt_version} canary {canary_pct}% -> {len(canary)}/{len(wa_list)}: {canary}")
    for who in canary:
        d=simulate_desired(who)
        text=d["prompt"] if "marathi" in prompt_version or "marathi" in d["version"] else d["prompt_en"]
        send_whatsapp(who, text, dry_run=dry_run)
        # hint: progressive to rest after observing reply confusion <20% same as log-processor autoscale gate
    return canary

if __name__=="__main__":
    # demo sim you can run even Companion offline
    demo_contacts=["Sanjay Home","Test Contact A","Test Contact B"]
    onboard(demo_contacts[0])
    push_campaign(demo_contacts, dry_run=True, canary_pct=33)
    # simulate replies including Marathi numerals you care about preserving
    for reply in ["120/80 here", "आज १२२/७८", "photo of cuff.jpg (sim)", "my sys 118 dia 76"]:
        r=ingest_reply(demo_contacts[0], reply)
        print(f"ingest -> parsed={r['payload']['parsed']}")
