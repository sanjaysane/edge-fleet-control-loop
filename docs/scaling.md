# Scaling + Compute Playbook (updated for debug isolation)

| Devices | per-dev DATA QPS | DATA RPS | Debug normal RPS | Debug crash storm RPS (per device 5 rps) | Total pods DATA | Total pods DEBUG |
|---------|------------------|----------|------------------|------------------------------------------|-----------------|-------------------|
| 1k      | 0.1              | 100      | 10               | 5000 if un-capped but capped to 0.1 via client cap | 2 min | 2 |
| 10k     | 0.1              | 1000     | 100              | 50k -> but sampling cuts to 5k | 3 | 2-4 |
| 100k    | 0.2              | 20k      | 2k               | 500k -> sampling 10% + separate volume | 20 | 10 |

Key: Client-side cap (64KB/5min) + server `X-Debug-Sampling:10` + separate deployment prevents data lake stalls.

Runbook for gradual deploy:
1. `python workflows/canary_deploy.py v3` (5% -> soak -> 30% -> 100%)
2. Analyzer daemon checks `data/debug_lake` every 120s, auto-blocks if 5x spike
3. If blocked, data plane continues on previous stable version, no impact.

Coverage: `tests/test_debug_pipeline.py` verifies isolation + blocked full-rollout rejection.

Kustomize includes `debug-processor.yaml` separate HPA 2-10.
