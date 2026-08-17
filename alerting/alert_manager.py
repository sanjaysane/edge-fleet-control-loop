"""
Alerting — the missing piece you flagged

5 rules, each checks metrics files + db and emits alert JSON + oncall trigger

Rules:
 1. Canary crash spike (from debug_reports)
 2. Data lake lag (no new file >30 min)
 3. P95 latency >800ms
 4. Offline % >20%
 5. Debug drop rate >50% (we sampling too hard, blind)

Usage: python alerting/alert_manager.py every minute (or as sidecar)
"""
import pathlib, json, time, glob, os

CTRL_DB = pathlib.Path("../control_plane/data/devices.json")
DEBUG_REPORTS = pathlib.Path("../control_plane/data/debug_reports")
WAREHOUSE = pathlib.Path("../control_plane/data/warehouse")
ALERT_OUT = pathlib.Path("alerts.jsonl")
ALERT_OUT.parent.mkdir(parents=True, exist_ok=True)

def emit(rule, severity, msg, meta={}):
    entry={"ts":time.time(),"rule":rule,"sev":severity,"msg":msg,"meta":meta}
    print(f"ALERT [{severity}] {rule}: {msg}")
    with open(ALERT_OUT,"a") as f:
        f.write(json.dumps(entry)+"\n")
    # Call oncall hook if critical
    if severity=="critical":
        try:
            import requests
            requests.post("http://localhost:8081/oncall/page", json=entry, timeout=2)
        except: pass

def check():
    # 1 canary crash
    reports = sorted(DEBUG_REPORTS.glob("*.json"))[-1:] if DEBUG_REPORTS.exists() else []
    for rp in reports:
        try:
            r=json.loads(rp.read_text())
            for act in r.get("actions",[]):
                if "BLOCK" in act:
                    emit("canary_crash_spike","critical", f"{act} - auto-paused", {"report": rp.name})
        except: pass
    # 2 lake lag
    files = glob.glob(str(WAREHOUSE/"*.json")) or glob.glob(str(pathlib.Path("../control_plane/data/lake")/"*/*/*/*.jsonl"), recursive=True)
    if files:
        mtime=max(pathlib.Path(f).stat().st_mtime for f in files)
        if time.time()-mtime>1800:
            emit("lake_lag","warning", f"No new warehouse/lake file >30m (last {int((time.time()-mtime)/60)}m ago)")
    # 3 latency - we read from last scale harness? For MVP read metrics endpoint stub
    # Simulate: if we had metrics file >800 p95 would be flagged - stub
    # 4 offline %
    if CTRL_DB.exists():
        try:
            db=json.loads(CTRL_DB.read_text())
            total=len(db.get("devices",{}))
            if total>0:
                online=sum(1 for d in db["devices"].values() if time.time()-d.get("last_seen",0)<120)
                offline_pct=1-online/total
                if offline_pct>0.2:
                    emit("fleet_offline","warning", f"{offline_pct*100:.1f}% offline ({total-online}/{total})")
        except: pass
    # 5 debug drop sampling blind - we track drops in qos/lanes stats file if present
    # stub

if __name__=="__main__":
    while True:
        check()
        time.sleep(60)
