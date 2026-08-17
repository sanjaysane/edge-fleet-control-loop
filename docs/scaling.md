# Scaling + Compute Playbook

## How much compute for control plane?

Rule of thumb observed:

| Devices | per-dev QPS | Aggregate RPS | Pods (500 RPS/pod target) | CPU req |
|---------|-------------|---------------|---------------------------|---------|
| 1k      | 0.1         | 100           | 2 (min)                   | 400m    |
| 10k     | 0.1         | 1,000         | 2-3                       | 600m-1c |
| 100k    | 0.2         | 20,000        | 20 (max, add second shard)| 20c     |

* Sample QPS story:
  * WiFi router: heartbeat 30s (0.033) + telemetry batch 30s (0.033) = 0.066 qps
  * BP monitor: heartbeat 60s + reading 60s = 0.033 qps
  * Wearable: heartbeat 30s + HRV 10s = 0.13 qps
* So 0.05-0.2 qps per device is realistic.

## Autoscaling setup

- `k8s/hpa.yaml` scales control-plane 2->20 pods on 65% CPU + custom metric `http_requests_per_second` 500/pod
- `k8s/log-processor.yaml` scales separate pool 2->30 on queue depth (Kafka lag or S3 file count) — independent of heartbeat path
- Reserve: use `resources.requests` to guarantee; autoscaler only adds above min.

Deployment on Kubernetes:

```bash
kubectl apply -k k8s/
kubectl get hpa -w
```

## Workflows for New Devices

`workflows/device_onboarding.py`:

1. Manufacture encodes SERIAL+SKU in QR
2. Owner scans -> `claim_device()` creates device_id + token
3. `register()` hits POST /heartbeat (auto-registers)
4. `provision()` puts device into cohort (prod/beta/geo) for progressive rollout

Idempotent: same serial re-claimed returns same device_id.

## Scale Test Framework

Prove it before customers hit it:

```bash
# single machine smoke
python scale_test/harness.py --devices 500 --qps 0.2 --duration 60

# bigger: 2000 devices -> ~200 rps
python scale_test/harness.py --devices 2000 --qps 0.1 --duration 120
```

Report contains implied pods and p95. If p95 >800ms or error >5%, tune.

Use `tests/test_scale.py` in CI for 20-dev quick smoke.

## Central engine pull vs push

Current MVP is push (edge POSTs). For scale >10k, flip to pull-or-stream:
- Edge opens long-poll to receive desired? (control->edge push)
- Or move to MQTT/NATS to push configs (reduces heartbeat load 70%)
- Log path stays push to firehose (S3/Kinesis), processed by log-processor pool.

Kustomize `k8s/` is ready for Helm later.
