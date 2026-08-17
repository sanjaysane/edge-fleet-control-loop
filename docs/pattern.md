# Pattern Spec — Edge Fleet Control Loop

## Name 
- Formal: Centralized Control / Distributed Data Plane with Closed Learning Loop
- Short: **Edge Fleet Control Loop**

## Context
> You have N devices at the edge (proportional to people/house/homes). Each runs software collecting signal. You need to operate them like a fleet, not pets.

## Forces
- Scale: O(10k-1M) devices
- Unreliable WAN
- Heterogeneous hardware / OS
- Need for OTA, compliance, rapid AI iteration
- Security: don't trust edge

## Solution Sketch

### 1. Desired-State Reconciliation (k8s-style for edge)
Control plane stores *desired*, edge reports *actual*. Edge's job is to converge. No direct command.

### 2. Artifact Distribution via Content-Addressed Store
OTA bundles are tar.gz + sha256. Served via CDN / simple static HTTP.

### 3. Telemetry Firehose with Edge Buffer
Append-only, schema-evolved (add fields, don't break). Use protobuf/avro for later versions.

### 4. Closed Learning Loop
Data from fleets -> aggregate -> model retrain -> new artifact version -> progressive rollout.

### 5. Progressive Delivery
Canary by sku / geo / cohort. Auto-rollback if error telemetry spikes.

## Variants

- **Wi-Fi Router Fleet:** Edge = OpenWrt package, job = channel scan, Control = TR-069 style but HTTP.
- **Wearables:** Edge = Fitbit BLE, job = HRV sample, ML = AFib detector model pushed.
- **Retail Camera:** Edge = Jetson Nano, model = yolo-tiny pushed as LoRA.

## When NOT to use
<10 devices collocated — just SSH. <1 telemetry sample/min — skip streaming complexity.

## Reference Links
- AWS IoT Greengrass Shadow, Azure IoT Hub Twin, k3s, Balena.io pattern — all are instantiations of this.
