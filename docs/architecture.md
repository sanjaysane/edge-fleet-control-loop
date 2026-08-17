# Architecture - Existence Level Design

## 1. Actors
- **Edge Device:** resource-constrained, runs `edge_agent`. Has: device_id, hardware sku, firmware version, local sensors/jobs.
- **Manufacturer/Ops:** uses Control Plane to rollout.
- **Data Consumer:** dashboard, alerts, ML.

## 2. Control Plane (Central Co-ordination)

REST: `FastAPI`. Postgres/SQLite for MVP.

Tables:
- `devices` (id, sku, last_heartbeat, current_version, desired_version)
- `rollouts` (version, artifact_url, pct, canary_tags, created_at)
- `desired_state` (device_id -> JSON blob: config, sampling_rate, model_version)

Endpoints:
- `POST /api/v1/heartbeat` edge -> control (id, version, health)
- `GET /api/v1/desired/{device_id}` edge pulls desired state
- `POST /api/v1/telemetry` bulk ingest proxy (for MVP)
- `POST /api/v1/rollout` ops creates rollout

Auth: mTLS or token per device. For MVP: `X-Device-Token`.

## 3. Edge Data Plane

Loop (Python async):
1. POST heartbeat every 30s
2. GET desired -> compare local version
3. If drift: download + verify checksum + atomic swap + restart job
4. Run local job: e.g., `collect_wifi_stats()` / `read_bp()` simulating sensor
5. Buffer readings to `spool.jsonl` if offline, flush on connectivity

On-device:
- Supervisor handles updates, main app is pluggable `job.py`.

## 4. Ingestor + Lake

MVP: HTTP -> local dir `lake/YYYY/MM/DD/device_id.jsonl`. At scale: replace with Kafka + S3 + Parquet.

Schema: `{ts, device_id, type, payload, fw_version, model_version}`

## 5. Analytics / ML Loop

Cron job `ml_loop/trainer.py`:
- Reads last 24h lake
- Computes aggregate: avg anomaly rate per sku
- Trains dumb model: `threshold = p99(value) * 0.9`
- Publishes `model_v{ts}.json` to control_plane artifacts dir
- Updates rollout to push new model_version

This is intentionally simple. Swap with PyTorch/LoRA training.

## 6. Observability / Dashboard

`GET /api/v1/fleet/health` returns: total, online (heartbeat <2m), by version, by model drift.

Frontend: single-page vanilla JS polls API.

## 7. Scale Knobs

- 1k devices: Single FastAPI + SQLite works
- 10-100k: Postgres + S3 + SQS/Kinesis
- 1M+: Regional ingest, CDN for artifacts, MQTT broker (EMQX/VerneMQ), device shadow tables.

## Failure Modes

- Edge offline 1d: spool, drop after 10MB cap
- Bad OTA: edge keeps previous version, reports `failed` heartbeat -> auto-pause rollout in control plane
- Ingestor down: edge backs off exponentially

Sequence for Feedback:
Edge --telemetry--> Lake --batch--> Trainer --model--> Control Plane --desired--> Edge (new inference)
