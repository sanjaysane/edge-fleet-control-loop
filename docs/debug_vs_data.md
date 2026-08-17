# Debug / Error Logs vs Data Logs - Separate Pipelines

Real world lesson: new software is chatty when it crashes. If you put crash logs in same pipe as sensor data, you DDoS your own analytics.

## Two Rivers

### 1. Data Plane (user-facing value)
- Route: `POST /api/v1/telemetry` -> `data/lake/YYYY/MM/DD/device.jsonl` -> analytics/ML/model -> dashboard
- QPS: 0.05-0.2 per device, steady, high value, SLA sensitive
- Example: wifi channel util, BP reading, HRV
- Scaling: HPA on rps 500/pod, critical path

### 2. Debug Plane (developer-facing)
- Route: `POST /api/v1/debug` -> `data/debug_lake/YYYY/MM/DD/device.jsonl` -> failure-analyzer -> rollout gate -> dev portal
- QPS: spiky, 0.01 normal but 5-10 QPS per device when new fw crashes (log explosion)
- Example: stack traces, panic dumps, restart reason, core-lite, assert failures
- Scaling: Separate pool, backpressure + sampling, never blocks data plane

## Isolation tactics (so debug doesn't kill core)

1. **Different endpoints + tokens** - Can't mix. `/telemetry` vs `/debug` with separate rate limiters.
2. **Size cap** - Edge caps debug at say 64KB per 5 min, drops oldest if full. Prevents death-spiral.
3. **Backpressure header** - Control plane can say `X-Debug-Sampling: 10%` to tell faulty fleet to whisper.
4. **Bulk upload** - Edge spools debug to file, uploads when asked, rather than spamming.
5. **Separate K8s deployment** - `debug-processor` scales 2-20 independent of `log-processor`. See k8s/debug-processor.yaml.

## Failure analysis workflow for devs

Analyzer runs every 2 min, not realtime (to batch):

1. Reads last 15 min of debug_lake, groups by fw_version + sku + error_signature
2. Computes baseline: for vX, is error rate > 5x healthy cohort? 
3. If canary cohort (say 5% devices on v3) spikes -> auto-pause rollout + mark `blocked_for_devs`
4. Writes `debug_reports/report_{version}.json` with top crashes + affected devices + suggested action
5. Control plane /api/v1/debug/summary exposes it to devs

Dev workflow: push v3 to 5% -> check summary -> if clean, promote to 30% -> 100%. If not, file goes into `blocked/` and dev gets link.

Covers data locks too: if processing lake lags because debug flooded disk/network, data lake processor has isolated PV so not impacted.
