"""
ML Loop - reads lake, produces naive threshold model, publishes new version.
"""
import pathlib, json, time, glob
LAKE = pathlib.Path("../control_plane/data/lake")
ARTIFACTS = pathlib.Path("../control_plane/data/artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)

files = glob.glob(str(LAKE/"*/*/*/*.jsonl"), recursive=True)
vals = []
for f in files[-20:]:  # last 20 files for MVP
    try:
        for line in open(f):
            j = json.loads(line)
            v = j.get("payload", {}).get("rssi")
            if v: vals.append(v)
    except: pass

if not vals:
    threshold = -50
else:
    vals_sorted = sorted(vals)
    threshold = vals_sorted[int(len(vals_sorted)*0.95)]  # p95 as naive model

model_version = f"model_{int(time.time())}"
model = {"version": model_version, "threshold_rssi": threshold, "trained_on": len(vals), "ts": time.time()}
(ARTIFACTS / f"{model_version}.json").write_text(json.dumps(model, indent=2))
print(f"Trained {model_version} on {len(vals)} samples -> threshold {threshold}")

# Auto-publish rollout note (ops would do progressive via API)
print(f"To push: curl -X POST http://localhost:8000/api/v1/rollout -H 'Content-Type: application/json' -d '{{\"version\":\"v1\",\"model_version\":\"{model_version}\",\"config\":{{\"sample_rate_sec\":20}}}}'")
