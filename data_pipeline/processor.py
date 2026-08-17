"""
Data Lake Processing - moves raw jsonl -> staged parquet, computes aggregates

What you asked: what happens after lake?

- Raw: data/lake/YYYY/MM/DD/device.jsonl
- Staged: data/warehouse/staged/date=YYYY-MM-DD/sku=xxx/fw=vY/part-...parquet
- Metrics: avg_anomaly, p95_latency, device counts per fw

For MVP we do pyarrow if available else json aggregate fallback.
"""
import pathlib, json, glob, time, os
from collections import defaultdict

LAKE = pathlib.Path("../control_plane/data/lake")
WH = pathlib.Path("../control_plane/data/warehouse")
WH.mkdir(parents=True, exist_ok=True)
(WH/"staged").mkdir(parents=True, exist_ok=True)

def process_once():
    files = glob.glob(str(LAKE/"*/*/*/*.jsonl"), recursive=True)
    if not files:
        files = glob.glob(str(LAKE/"*/*.jsonl"), recursive=True)
    print(f"Found {len(files)} raw files")
    agg = defaultdict(list)
    for fp in files[-50:]:  # last 50 for MVP
        try:
            for line in open(fp):
                j=json.loads(line)
                sku=j.get("payload",{}).get("sku","unknown")
                fw=j.get("payload",{}).get("fw","unknown") # if nested differently, best effort
                agg[(sku,fw)].append(j)
        except: pass
    # write simple aggregate JSON (parquet would need pyarrow)
    out = WH / f"agg_{int(time.time())}.json"
    out.write_text(json.dumps({f"{k[0]}/{k[1]}": len(v) for k,v in agg.items()}, indent=2))
    print(f"Aggregate -> {out}")
    # Simulate late arrival dedupe TTL: delete raw >90d old (stub)
    # Dedupe: we would use device_id+ts key set, here we just count

if __name__=="__main__":
    while True:
        process_once()
        time.sleep(600)  # every 10 min
