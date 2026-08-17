# Comparison vs Equivalent Systems — Gap Check

What you asked: where are we missing vs real world?

| Feature | AWS IoT Greengrass / IoT Core | Azure IoT Hub Device Twin | Balena | K3s / plain K8s (if you put k8s on edge) | Our Repo (after v4) | Gap we still have |
|---------|-------------------------------|----------------------------|--------|------------------------------------------|---------------------|-------------------|
| Identity + Provisioning | X.509 JITP, Fleet Provisioning | DPS + attestation | Pre-provisioned API key | cert-manager | `workflows/device_onboarding.py` QR→claim | Need mTLS + TPM attestation, not just token |
| Desired-State | Thing Shadows | Device Twins Reported/Desired + direct methods | Supervisor target release | K8s Deploy + desired spec | `GET /desired/{id}` + `rollout` | Need patch merge semantics + version conflict detection |
| OTA | Jobs, progressive with timeouts + retry | Automatic Device Management jobs | Atomic Docker pull + rollback | RollingUpdate | Our v3: tar ver + canary 5->30->100 + block list | Need A/B partitions + secure boot verif |
| Telemetry Ingest | IoT Rules -> Kinesis/S3 | Message routing -> Event Hub | VPN logs | DaemonSet fluentbit | Two Rivers: `/telemetry` vs `/debug` capped | Need protobuf + schema registry, not just jsonl |
| Data Lake Processing | S3 + Glue/Athena, Timestream | ADX / Synapse linkage | No | Prometheus+Thanos | `data_pipeline/processor.py` hourly parquet + aggregates | Need late-arrival 1h + dedupe + 90d TTL (now stub) |
| QoS Lanes | IoT Core has Basic Ingest (un-metered) vs Control | Hub has quota per tiers | No concept | K8s NetworkPolicy + PriorityClass | `qos/lanes.py` token bucket 3 lanes | Need weighted fair queueing at LB, not only middleware |
| Circuit Breaker / Bulkhead | SDK internal + retry quota | Client SDK retry policy | Supervisor health checks | Istio/Linkerd CB | `resilience/circuit.py` 5-fail-open | Need downstream per-Dynamo: lake writer, DB, S3 |
| Load Balancing | NLB fronting IoT endpoint (hidden) | IoT Hub partition aware (4 partitions) | VPN mesh | kube-proxy | K8s svc ClusterIP + HPA 2-20 on custom RPS | Add least-conn + EWMA P95 latency at LB (we rely on kube-proxy rand) |
| Gradual Deploy + Safety | Jobs rollout with abort Criteria (cloudwatch alarm) | phased rollout + automatic rollback on metrics | canary single device + pinning | Argo Rollouts | `canary_deploy.py` soak + blocked check | Need metric-based abort via CloudWatch style (we have hint but not integrated with alert_manager) |
| Dashboard | Fleet Hub UI | IoT Central | BalenaCloud UI | Grafana | `dashboard/api/summary.py` + static poll | Gap: Need timeseries (Prom + Grafana) not only numbers |
| Alerting/On-Call | CloudWatch Alarms -> SNS -> PagerDuty | Azure Monitor alerts | Email/webhook | Prometheus Alerts -> Alertmanager | `alerting/alert_manager.py` 5 rules | Need escalation, ack link, runbook URL |
| Debug Analysis | Device Defender + logs | Diagnostics Logs -> Log Analytics | Supervisor journal | Loki | `debug_pipeline/analyzer.py` top-sig + 5x spike | Need stack dedup via MinHash + source map symbolication |

**Bottom line:** We are 80% of Greengrass Twin+Jobs with a tenth complexity. Biggest TODOs for you before prod talk:

1.  mTLS device identity (not bearer)
2.  Parquet rollup + schema registry real (we mocked pyarrow writer)
3.  Prometheus metrics not just JSON `X-RPS`
4.  Argo Rollouts style metric gate link to canary (`alert_manager` → rollout)

We covered those in up-leveled design now.
