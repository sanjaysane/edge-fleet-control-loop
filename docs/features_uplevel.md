# Key Facets — Up-Leveled View of Edge Fleet Control Plane

You asked for the 30kft map, not just code. Here are the 9 facets any real control plane needs. We had 4, now adding 5.

## Already Built (v1-v3)
1. **Fleet Identity & Registry** — device_id, sku, claim flow
2. **Desired-State + OTA** — rollout, canary, block list
3. **Two Rivers Telemetry** — data lake vs debug_lake isolation
4. **K8s Compute + Autoscale** — HPA 2-20 control, 2-30 log, 2-10 debug

## Now Upleveled (v4)

### 5. QoS Lanes (Priority)
Not all devices equal. BP monitor critical > router stats.
- Lane0 `critical` : 100% quota, P95 SLO 200ms, retries 3
- Lane1 `default` : 70% quota
- Lane2 `bulk / debug` : 10% quota, best-effort, sampled 10% when overloaded
Implementation: `control_plane/qos/lanes.py` FastAPI middleware reads `X-Device-Priority` or sku -> routes to token bucket per lane. See code.

### 6. Resilience — Circuit Breakers + Load Balancing + Bulkheads
- **Circuit Breaker** per downstream (lake writer, DB): after 5 fails 30s, open 60s, returns 503 fast instead of hanging
- **Bulkhead** per lane: thread pool partition so debug can't starve telemetry
- **Load Balancer** in front of control plane pods: least-conn; readinessProbe ensures drained
File: `control_plane/resilience/circuit.py`

### 7. Data Lake + Processing
What you called out: we ignored processing.
- Raw: `data/lake/YYYY/MM/DD/*.jsonl` (append-only)
- Staged: hourly Parquet rollup to `data/warehouse/staged/` partitioned by sku+version (for Athena/BigQuery)
- Dedupe + late-arrival window 1h, TTL 90d
File: `data_pipeline/processor.py` cron every 10 min -> compacts jsonl to parquet (pyarrow), computes aggregates: avg_anomaly, p95 latency, error rate per fw.
- Exports metrics for alerting.

### 8. Dashboarding
Beyond `/fleet/health`. Now:
- `dashboard/api/summary.py` returns: by_version counts, by_sku, online %, RPS, blocked, QOS drops, circuit open flags, top debug sig
- Frontend polls same, shows 3 lanes, canary progress bar
- Data controls intact even if debug storms

### 9. Alerting + On-Call
- `alerting/alert_manager.py` — 5 standard rules:
  1. Canary crash spike >5x → page oncall, auto-pause rollout
  2. Data lake lag >30 min → warn
  3. Control-plane P95 >800ms 5 min → auto-scale + slack
  4. % devices offline >20% → infra issue
  5. Debug drop rate >50% (we are sampling too hard) → warn devs you're blind
- `oncall/rotation.py` — tiny round-robin (sim of PagerDuty): loads `oncall.yaml` rotation, posts to webhook / email stub.

Each facet has load balancing / circuit break built-in: QPS lanes have weighted fair queuing, not just FIFO.

## How they wire together

Edge -> [LB] -> Control (QOS filter -> Circuit -> Bulkhead per lane) -> Lake Writer (critical) vs Debug Writer (bulk) -> (Lake Compactor) -> Warnings -> Dashboard + Alerts -> Oncall + Rollout Gate
               \
                -> Blocked check -> can't 100% broken fw
```

