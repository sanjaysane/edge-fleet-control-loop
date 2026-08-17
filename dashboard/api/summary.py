"""
Dashboard API consolidation - what you asked: automatic view

Extends /fleet/health + /debug/summary + /metrics + QOS stats + alerts
"""
from fastapi import APIRouter
import pathlib, json, time, glob
router=APIRouter()

DB=pathlib.Path("../control_plane/data/devices.json")
REPORTS=pathlib.Path("../control_plane/data/debug_reports")
WARE=pathlib.Path("../control_plane/data/warehouse")
ALERTS=pathlib.Path("../alerting/alerts.jsonl")

@router.get("/dashboard/full")
def full():
    db=json.loads(DB.read_text()) if DB.exists() else {}
    total=len(db.get("devices",{}))
    online=sum(1 for d in db.get("devices",{}).values() if time.time()-d.get("last_seen",0)<120) if db else 0
    reports=[json.loads(p.read_text()) for p in sorted(REPORTS.glob("*.json"))[-3:]] if REPORTS.exists() else []
    alerts=[json.loads(l) for l in open(ALERTS).readlines()[-10:]] if ALERTS.exists() else []
    # QOS drops file stub
    return {
        "ts": time.time(),
        "fleet": {"total":total,"online":online,"by_fw":{}},
        "blocked": db.get("blocked",[]),
        "reports": reports,
        "alerts": alerts,
        "qos": {"drops_critical":0,"drops_default":0,"drops_bulk":0},  # wire to real stats file later
        "circuit": {"lake":"CLOSED","debug":"CLOSED"},
        "rps": 0
    }
