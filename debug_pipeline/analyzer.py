"""
Failure / Debug Log Analyzer - Runs as separate service (debug-processor)

What it does for developers:
- Scans debug_lake (not telemetry lake) - so even if data pipeline is healthy, we still catch crashing fw
- Groups by error_signature + fw_version
- Detects spike vs baseline (5x)
- If canary version spikes, auto-blocks rollout + writes report
- Keeps data pipeline SLAs untouched because it reads separate disk queue
"""
import pathlib, json, time, glob
from collections import Counter, defaultdict

DEBUG_LAKE = pathlib.Path("../control_plane/data/debug_lake")
REPORT_DIR = pathlib.Path("../control_plane/data/debug_reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = pathlib.Path("../control_plane/data/devices.json")

def load_db():
    if DB_FILE.exists():
        try:
            return json.loads(DB_FILE.read_text())
        except:
            return {"rollouts":[], "blocked":[]}
    return {"rollouts":[], "blocked":[]}

def analyze():
    # last 15 min files - for MVP just look at today's files
    files = glob.glob(str(DEBUG_LAKE/"*/*/*/*.jsonl"), recursive=True) or glob.glob(str(DEBUG_LAKE/"*/*/*.jsonl"), recursive=True) or glob.glob(str(DEBUG_LAKE/"*/*.jsonl"), recursive=True)
    if not files:
        print("No debug logs yet (good)")
        return
    by_version = defaultdict(list)
    sig_by_version = defaultdict(Counter)
    for fp in files[-30:]:
        try:
            for line in open(fp):
                j=json.loads(line)
                if time.time() - j.get("ts", time.time()) > 900: # 15 min window
                    continue
                v=j.get("fw_version","unknown")
                sig=j.get("signature","unknown")
                by_version[v].append(j)
                sig_by_version[v][sig]+=1
        except: pass

    # Find latest rollout version (likely canary)
    db=load_db()
    versions = [r["version"] for r in db.get("rollouts",[])]
    if not versions:
        versions=list(by_version.keys())
    latest = versions[-1] if versions else None

    report={
        "ts": time.time(),
        "window_sec": 900,
        "by_version_counts": {v: len(l) for v,l in by_version.items()},
        "top_signatures": {v: dict(c.most_common(5)) for v,c in sig_by_version.items()},
        "actions": []
    }

    # Spike detection: if latest version's error count > 5x avg of others
    if latest and latest in by_version:
        others_avg = sum(len(by_version[v]) for v in by_version if v!=latest) / max(1, len(by_version)-1) if len(by_version)>1 else 0
        latest_cnt = len(by_version[latest])
        if others_avg>0 and latest_cnt > 5*others_avg and latest_cnt>10:
            print(f"SPIKE: {latest} {latest_cnt} vs baseline {others_avg:.1f} -> BLOCK")
            report["actions"].append(f"BLOCK {latest}: {latest_cnt} errors vs baseline {others_avg:.1f}")
            # block it
            if "blocked" not in db: db["blocked"]=[]
            if latest not in db["blocked"]:
                db["blocked"].append(latest)
                DB_FILE.write_text(json.dumps(db, indent=2))
        elif others_avg==0 and latest_cnt>20 and len(by_version)==1:
            # Only one version seen lately, but high volume could be new beta on few devices
            print(f"NOTE: single version {latest} high {latest_cnt} - needs baseline data")

    # Write report for devs
    rp = REPORT_DIR / f"report_{int(time.time())}_{latest or 'nover'}.json"
    rp.write_text(json.dumps(report, indent=2))
    print(f"Report written {rp}")

if __name__=="__main__":
    while True:
        analyze()
        time.sleep(120)
