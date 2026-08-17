# Edge Fleet Control Loop
### The Centralized Control Plane / Distributed Data Plane Pattern

> Most apps that touch the real world are the same app: 1M edge things doing work, one brain coordinating them.

This repo is an opinionated reference implementation of that pattern.

**Use cases:** Wi-Fi routers, Fitbits, BP monitors, home cameras, EV chargers, retail scanners — anything where software lives on a device proportional to households/people/things.

## The Pattern in One Sentence

> **A fleet of dumb-smart edge agents, a smart-central control plane that does OTA + config, a telemetry firehose, an analytics/ML pipeline, and a closed feedback loop that pushes intelligence back to the edge.**

### Why this pattern wins
1.  **Scale:** Edge count = O(population). You can't SSH into them.
2.  **Heterogeneity:** You need one control story for 10 hardware SKUs.
3.  **Data gravity:** Value is in the aggregate, not a single sample.
4.  **AI flywheel:** Collect → Train → Push → Better data.

## Architecture

```
[Edge Devices x N]  <--ota/config/model--  [Control Plane]
        |  telemetry (logs/metrics/events)        ^
        v                                         |
[Ingestor / Stream] --> [Lake / Warehouse] --> [Analytics/ML] --> (feeds back)
                                          \
                                           --> [Dashboard / Alerts / Ops]
```

6 components, 3 loops:
- **Deploy Loop:** Control Plane -> Edge (OTA, config rollout, A/B)
- **Data Loop:** Edge -> Ingestor -> Lake
- **Learning Loop:** Lake -> Model -> Control Plane -> Edge (this is where it gets interesting)

See `docs/architecture.md` and `docs/pattern.md` for deeper design.

## Repo Layout

- `control_plane/` - FastAPI central brain: device registry, OTA manifests, desired-state API
- `edge_agent/` - Lightweight Python agent that runs on device, does heartbeat, job execution, local buffering
- `ingestor/` - Fast consumer of telemetry (HTTP for MVP, plug Kafka/Kinesis later)
- `ml_loop/` - Batch job that pretends to train, produces a new `model.json` version
- `dashboard/` - Minimal API + static UI for fleet health
- `docker-compose.yml` - One-command local fleet sim

## Quickstart

```bash
git clone <this> && cd edge-fleet-control-loop
docker-compose up --build

# In another shell, add 5 virtual edge devices:
python3 edge_agent/sim_fleet.py --n 5

# Open dashboard:
open http://localhost:8000/dashboard

# Push a new config version:
curl -X POST http://localhost:8000/api/v1/rollout -d '{"version":"v2","pct":100}'
```

## Sanjay's Take (opinionated)

This is my default starter for any "real-world device" product:

1.  **Don't build MQTT day 1.** HTTPS + polling gets you to 10k devices. You can add MQTT/NATS when you need push.
2.  **Desired-state, not commands.** Edge pulls `desired_config`, reconciles locally. Way more resilient than RPC.
3.  **Treat OTA like Git.** Versions immutable, rollouts progressive with canary. `v1.2.3` not `latest`.
4.  **Buffer on edge.** If offline, spool to disk. Sync when back. Assume internet is flaky — because it is.
5.  **Telemetry is a firehose, not a DB query.** Use append-only log (S3/Kinesis) not Postgres for ingest.
6.  **Close the AI loop early, even if dumb.** Even a simple threshold model pushed back to edge proves the lifecycle.

I call this the `Central Brain / Thousand Little Brains` stack.

Future variants: WASM plugins for edge jobs, federated learning instead of central training, LoRA adapters pushed instead of full models.

MIT Licensed. PRs welcome.


## Scaling on Kubernetes (K8s)
Deploys 2->20 pods via HPA on CPU 65% + custom metric `http_requests_per_second` 500 rps/pod. Log processor scales 2->30 on queue depth.

```bash
kubectl apply -k k8s/
kubectl get hpa -w
```

See `docs/scaling.md` for capacity math: 10k devices @0.1 QPS = 1k RPS -> ~2-3 pods. HPA + onboarding workflow handles bursty joins.

## Cost Estimate + One-Liner Deploy (Option 2)

Real EKS test is **~$0.32 for 2-hr spot run**, ~$13 on-demand if you leave 3 days.

See `docs/cost_estimate_eks.md` for table.

One-liner deploy (after `aws sso login`):

```bash
./scripts/deploy_eks_one_liner.sh edge-fleet-test us-west-2
# then:
kubectl get hpa -w
kubectl port-forward svc/control-plane 8000:8000 &
python3 scale_test/harness.py --devices 500 --qps 0.2 --control http://localhost:8000
# tear down:
eksctl delete cluster --name edge-fleet-test --region us-west-2 --wait
```

Full options tracked in `scripts/deploy_eks_one_liner.sh`.
