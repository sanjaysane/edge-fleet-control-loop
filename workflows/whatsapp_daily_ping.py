"""
Daily 8:30 AM PDT ping — what you asked "ask for imports from user"

Same cadence as your HA Build Yoga 8:30-9:30 AM block you keep as streak.

Runs via cron / manual: asks "bp-check" to all onboarded WhatsApp humans
Writes what it sends to cron log, sim send if Companion offline (same as connector)

Set up: 30 15 * * * (15:30 UTC == 8:30 AM PDT)
"""
import pathlib, sys, json, time
ROOT=pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from connector import wa_device_id, simulate_desired, send_whatsapp

ONBOARD=ROOT/"control_plane"/"data"/"whatsapp_onboarded.json"
PING_LOG=ROOT/"control_plane"/"data"/"wa_ping_log.jsonl"
PING_LOG.parent.mkdir(parents=True, exist_ok=True)

def ping_all(dry_run=True, campaign="bp-check"):
    if not ONBOARD.exists():
        print("no onboarded WA contacts — add one via /api/v1/whatsapp/onboard first")
        return []
    db=json.loads(ONBOARD.read_text())
    sent=[]
    for dev_id, meta in db.items():
        who=meta.get("wa_name") or dev_id
        d=simulate_desired(who)
        text=f"[Daily {campaign} {time.strftime('%Y-%m-%d')}] {d['prompt']}"
        res=send_whatsapp(who, text, dry_run=dry_run)
        sent.append({"wa":who,"dev":dev_id,"sent_at":time.time(),"res":res,"campaign":campaign})
        with open(PING_LOG,"a") as f:
            f.write(json.dumps(sent[-1])+"\n")
    print(f"Pinged {len(sent)} contacts dry_run={dry_run}")
    return sent

if __name__=="__main__":
    # default sim so you see without spamming real people while Companion is offline
    ping_all(dry_run=True)
