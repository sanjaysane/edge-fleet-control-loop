from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os, json, time, pathlib
from typing import Dict, Any
import time
from collections import deque

app = FastAPI(title="Edge Fleet Control Plane")

# --- simple RPS for HPA demo ---
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
    return resp


DB_FILE = pathlib.Path("data/devices.json")
LAKE_DIR = pathlib.Path("data/lake")
ARTIFACT_DIR = pathlib.Path("data/artifacts")
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
LAKE_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# In-mem DB for MVP - persisted to JSON
def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return {"devices": {}, "desired": {}, "rollouts": []}

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

class Rollout(BaseModel):
    version: str
    pct: int = 100
    model_version: str = "v0"
    config: Dict[str, Any] = {}

@app.post("/api/v1/heartbeat")
def heartbeat(hb: Heartbeat):
    db["devices"][hb.device_id] = {
        "sku": hb.sku,
        "fw_version": hb.fw_version,
        "model_version": hb.model_version,
        "last_seen": time.time(),
        "health": hb.health
    }
    # assign desired if not present
    if hb.device_id not in db["desired"] and db["rollouts"]:
        # latest rollout for now
        r = db["rollouts"][-1]
        db["desired"][hb.device_id] = {"fw_version": r["version"], "model_version": r["model_version"], "config": r["config"]}
    save_db(db)
    return {"desired": db["desired"].get(hb.device_id, {})}

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
    with open(p, "a") as f:
        f.write(json.dumps(t.dict())+"\n")
    return {"ok": True}

@app.post("/api/v1/rollout")
def rollout(r: Rollout):
    db["rollouts"].append(r.dict())
    # assign to pct of devices (simple: all for MVP)
    for dev_id in list(db["devices"].keys())[:max(1,int(len(db["devices"])*r.pct/100))]:
        db["desired"][dev_id] = {"fw_version": r.version, "model_version": r.model_version, "config": r.config}
    # if no devices yet, keep as default for new devices
    save_db(db)
    return {"active_rollouts": len(db["rollouts"])}

@app.get("/api/v1/fleet/health")
def fleet_health():
    now = time.time()
    total = len(db["devices"])
    online = sum(1 for d in db["devices"].values() if now - d.get("last_seen",0) < 120)
    by_ver = {}
    for d in db["devices"].values():
        by_ver[d.get("fw_version","?")] = by_ver.get(d.get("fw_version","?"),0)+1
    return {"total": total, "online": online, "by_fw": by_ver, "rollouts": db["rollouts"][-3:]}

@app.get("/metrics")
def metrics():
    return {"rps": round(rps_counter.rps(),2), "devices": len(db["devices"]), "online": sum(1 for d in db["devices"].values() if time.time()-d.get("last_seen",0)<120)}

@app.get("/dashboard")
def dash_page():
    return {"msg":"Use static dashboard - see dashboard/index.html"}
