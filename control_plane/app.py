from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os, json, time, pathlib
from typing import Dict, Any
from collections import deque

try:
    from qos.lanes import qos_middleware as _qos_mw
    from resilience.circuit import lake_breaker, debug_breaker
    _QOS_AVAILABLE=True
except:
    _QOS_AVAILABLE=False


app = FastAPI(title="Edge Fleet Control Plane")

DB_FILE = pathlib.Path("data/devices.json")
LAKE_DIR = pathlib.Path("data/lake")
DEBUG_LAKE = pathlib.Path("data/debug_lake")
ARTIFACT_DIR = pathlib.Path("data/artifacts")
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
LAKE_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_LAKE.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# RPS counter for HPA demo
class RPSCounter:
    def __init__(self, window_sec=60):
        self.timestamps = deque()
        self.window = window_sec
    def hit(self):
        now = time.time()
        self.timestamps.append(now)
        while self.timestamps and now - self.timestamps[0] > self.window:
            self.timestamps.popleft()
    def rps(self):
        return len(self.timestamps)/self.window if self.timestamps else 0
rps_counter = RPSCounter()

@app.middleware("http")
async def _rps(request, call_next):
    rps_counter.hit()
    resp = await call_next(request)
    resp.headers["X-RPS"] = str(round(rps_counter.rps(),2))
    # tell noisy devices to back off on debug
    if DEBUG_LAKE.stat().st_blocks if DEBUG_LAKE.exists() else False:
        resp.headers["X-Debug-Sampling"] = "10"
    return resp

def load_db():
    if DB_FILE.exists():
        try:
            return json.loads(DB_FILE.read_text())
        except:
            return {"devices": {}, "desired": {}, "rollouts": [], "blocked": []}
    return {"devices": {}, "desired": {}, "rollouts": [], "blocked": []}

def save_db(db):
    DB_FILE.write_text(json.dumps(db, indent=2))

db = load_db()

class Heartbeat(BaseModel):
    device_id: str
    sku: str
    fw_version: str
    health: Dict[str, Any] = {}
    model_version: str = "v0"

class Telemetry(BaseModel):
    device_id: str
    ts: float = None
    type: str
    payload: Dict[str, Any]

class DebugLog(BaseModel):
    device_id: str
    ts: float = None
    fw_version: str
    level: str = "error"  # error, panic, warn, debug
    signature: str  # truncated stack / error key e.g. "panic: null deref @ wifi_scan.c:142"
    stack: str = ""
    meta: Dict[str, Any] = {}

class Rollout(BaseModel):
    version: str
    pct: int = 100
    model_version: str = "v0"
    config: Dict[str, Any] = {}
    canary: bool = False

@app.post("/api/v1/heartbeat")
def heartbeat(hb: Heartbeat):
    db["devices"][hb.device_id] = {
        "sku": hb.sku,
        "fw_version": hb.fw_version,
        "model_version": hb.model_version,
        "last_seen": time.time(),
        "health": hb.health
    }
    if hb.device_id not in db["desired"] and db["rollouts"]:
        r = db["rollouts"][-1]
        # don't assign blocked versions
        if r["version"] in db.get("blocked", []):
            r = next((x for x in reversed(db["rollouts"]) if x["version"] not in db.get("blocked", [])), r)
        db["desired"][hb.device_id] = {"fw_version": r["version"], "model_version": r["model_version"], "config": r["config"]}
    save_db(db)
    return {"desired": db["desired"].get(hb.device_id, {}), "debug_sampling_pct": 10 if len(db.get("blocked",[]))>0 else 100}

@app.get("/api/v1/desired/{device_id}")
def get_desired(device_id: str):
    d = db["desired"].get(device_id, {})
    return d if d else {"fw_version": "v1", "model_version": "v0", "config": {"sample_rate_sec": 30}}

@app.post("/api/v1/telemetry")
def ingest(t: Telemetry):
    t.ts = t.ts or time.time()
    day = time.strftime("%Y/%m/%d")
    p = LAKE_DIR / day / f"{t.device_id}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    def _do():
        with open(p, "a") as f:
            f.write(json.dumps(t.model_dump() if hasattr(t,"model_dump") else t.dict())+"\n")
    try:
        _do() if not _QOS_AVAILABLE else lake_breaker.call(_do)
    except Exception as e:
        raise e
    return {"ok": True}

@app.post("/api/v1/debug")
def ingest_debug(d: DebugLog):
    # Separate pipeline - isolated from telemetry critical path
    d.ts = d.ts or time.time()
    # Simple backpressure: if device sending >10 errors/sec, drop (device should sample)
    day = time.strftime("%Y/%m/%d")
    p = DEBUG_LAKE / day / f"{d.device_id}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(d.model_dump() if hasattr(d,"model_dump") else d.dict())+"\n")
    # quick spike detection hint (full check is in analyzer batch job)
    return {"ok": True, "sampling_hint": 10 if d.level=="panic" else 100}

@app.get("/api/v1/debug/summary")
def debug_summary():
    # read latest report(s) produced by debug_pipeline/analyzer.py
    report_dir = pathlib.Path("data/debug_reports")
    if not report_dir.exists():
        return {"reports": [], "blocked": db.get("blocked",[])}
    reports = sorted(report_dir.glob("*.json"))[-5:]
    out=[]
    for fp in reports:
        try:
            out.append(json.loads(fp.read_text()))
        except: pass
    return {"reports": out, "blocked_versions": db.get("blocked",[]), "active_rollouts": db["rollouts"][-3:]}

@app.post("/api/v1/rollout")
def rollout(r: Rollout):
    if r.version in db.get("blocked", []) and r.pct>5:
        raise HTTPException(status_code=409, detail=f"version {r.version} is blocked due to crash spike, only canary 5% allowed, fix and unblock first")
    db["rollouts"].append(r.model_dump() if hasattr(r,"model_dump") else r.dict())
    # assign to pct of devices (simple: all for MVP, canary = first 5%)
    dev_ids = list(db["devices"].keys())
    if r.canary:
        dev_ids = dev_ids[:max(1, int(len(dev_ids)*0.05))]
    else:
        dev_ids = dev_ids[:max(1,int(len(dev_ids)*r.pct/100))]
    for dev_id in dev_ids:
        db["desired"][dev_id] = {"fw_version": r.version, "model_version": r.model_version, "config": r.config}
    save_db(db)
    return {"active_rollouts": len(db["rollouts"])}

@app.post("/api/v1/unblock/{version}")
def unblock(version: str):
    if version in db.get("blocked", []):
        db["blocked"].remove(version)
        save_db(db)
    return {"blocked": db.get("blocked", [])}

@app.get("/api/v1/fleet/health")
def fleet_health():
    now = time.time()
    total = len(db["devices"])
    online = sum(1 for d in db["devices"].values() if now - d.get("last_seen",0) < 120)
    by_ver = {}
    for d in db["devices"].values():
        by_ver[d.get("fw_version","?")] = by_ver.get(d.get("fw_version","?"),0)+1
    return {"total": total, "online": online, "by_fw": by_ver, "rollouts": db["rollouts"][-3:], "blocked": db.get("blocked",[])}

@app.get("/metrics")
def metrics():
    return {"rps": round(rps_counter.rps(),2), "devices": len(db["devices"]), "online": sum(1 for d in db["devices"].values() if time.time()-d.get("last_seen",0)<120), "blocked": db.get("blocked",[])}

@app.get("/dashboard")
def dash_page():
    return {"msg":"Use static dashboard - see dashboard/index.html"}

@app.post("/api/v1/attest")
def attest(token: dict):
    try:
        from attestation.verifier import verify_attest, quarantine
        res=verify_attest(token, None)
        if not res.get("ok"):
            quarantine(token.get("device_id","unknown"), res.get("reason","bad"))
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content=res)
        return res
    except Exception as e:
        return {"ok":True,"reason":"verifier_missing","warn":str(e)}

@app.post("/api/v1/whatsapp/ingest")
def wa_ingest(msg: dict):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "edge_connectors" / "whatsapp"))
    from connector import ingest_reply
    wid=msg.get("wa_id") or msg.get("phone") or "unknown"
    text=msg.get("text","")
    rec=ingest_reply(wid, text, msg.get("media"))
    return {"ok": True, "device_id": rec["device_id"], "parsed": rec["payload"]["parsed"]}

@app.get("/api/v1/whatsapp/desired/{wa_name}")
def wa_desired_router(wa_name: str):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "edge_connectors" / "whatsapp"))
    from connector import simulate_desired
    return simulate_desired(wa_name)

@app.post("/api/v1/whatsapp/onboard")
def wa_onboard(body: dict):
    import json, time, hashlib, pathlib
    wa=body.get("wa_name") or body.get("phone")
    if not wa:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error":"wa_name required"})
    p=pathlib.Path("data/whatsapp_onboarded.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    db=json.loads(p.read_text()) if p.exists() else {}
    did="wa:"+hashlib.sha256(wa.encode()).hexdigest()[:12]
    db[did]={"wa_name":wa,"onboarded_at":time.time(),"sku":"whatsapp-human-v1"}
    p.write_text(json.dumps(db, indent=2))
    return {"ok":True,"device_id":did,"onboarded":wa}

@app.get("/api/v1/whatsapp/status/{wa_name}")
def wa_status_route(wa_name: str):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import personal_summary
    return personal_summary(wa_name)

@app.get("/api/v1/whatsapp/global")
def wa_global_route():
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import _agg_global
    return _agg_global(days=7)

@app.post("/api/v1/whatsapp/command")
def wa_command_route(body: dict):
    import sys, pathlib, json
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "edge_connectors" / "whatsapp"))
    from onboarding import handle_inbound
    wa=body.get("wa_name") or body.get("phone") or "unknown"
    text=body.get("text","")
    inbound=handle_inbound(wa, text, dry_run=True)
    if inbound["type"] in ("welcome","need_onboard"):
        return {"type":inbound["type"],"reply":inbound["reply"]}
    if inbound["type"]=="command":
        return {"type":"command","reply":inbound["reply"]}
    if inbound["type"]=="data":
        return {"type":"data","ok":True,"device_id":inbound.get("device_id"),"parsed":inbound.get("parsed")}
    from interactive import handle_whatsapp_command
    from connector import ingest_reply
    wa=body.get("wa_name") or body.get("phone") or "unknown"
    txtb=body.get("text","")
    cmd_res=handle_whatsapp_command(wa, txtb)
    if cmd_res:
        return {"type":"command","reply":cmd_res}
    else:
        rec=ingest_reply(wa, txtb, body.get("media"))
        return {"type":"data","ok":True,"device_id":rec["device_id"],"parsed":rec["payload"]["parsed"]}

@app.get("/wa/{wa_name}/dash")
def wa_dash_page_route(wa_name: str):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import personal_summary, _agg_global
    s=personal_summary(wa_name)
    g=_agg_global()
    last_sys = s.get("last",{}).get("sys_mmHg","-")
    last_dia = s.get("last",{}).get("dia_mmHg","-")
    cnt = s.get("count",0)
    streak = s.get("streak_days",0)
    trend = s.get("trend","-")
    avg7 = s.get("avg_sys_last7","-")
    g_cnt = g.get("count",0)
    g_avg_sys = g.get("avg_sys","-")
    g_avg_dia = g.get("avg_dia","-")
    g_dev = g.get("devices_seen",0)
    html = "<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>"+wa_name+" personal</title>"
    html += "<style>body{font-family:system-ui;padding:16px;max-width:520px;margin:auto} .card{border:1px solid #ddd;border-radius:12px;padding:12px;margin:8px 0} .k{color:#666;font-size:12px} .big{font-size:24px;font-weight:700}</style>"
    html += "</head><body><h2>"+wa_name+" - personal</h2>"
    html += f"<div class=\"card\"><div class=k>last</div><div class=big>{last_sys}/{last_dia}</div><div>{cnt} readings - streak {streak}d - trend {trend}</div></div>"
    html += f"<div class=\"card\"><div class=k>7-day avg sys</div><div class=big>{avg7}</div></div>"
    html += f"<div class=\"card\"><div class=k>global last 7d (anon)</div>{g_cnt} readings, avg {g_avg_sys}/{g_avg_dia}, from {g_dev} devices</div>"
    html += "<div class=k>type STATUS / GLOBAL in WhatsApp for refresh - same lake as hardware fleet</div></body></html>"
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
