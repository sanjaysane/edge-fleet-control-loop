# Edge Driver — Placeholder for Real HW Work

This is where you will write the actual device code later. Everything else around it — secure boot chain, attestation, OTA, telemetry lake — is ready and gated.

## Current State (what's here now)
- `driver_stub.py` — fakes `init()`, `read() -> {sys_mmHg, dia_mmHg, temp_c}`, `write(cfg)`. Boots fine, signed as `driver_stub.py.sig`.
- Secure boot checks sig before import — tampered driver blocks boot, emits `boot_fail` debug report, never marks healthy.
- Attestation measurement `8f6792ac...32a1` already allow-listed in `control_plane/attestation/allowlist.json` as `v1-stub`.

## Where You Will Write Real Driver (HW TODO)

### 1. Replace the read path
```python
# In driver_stub.py replace read() body:
def read():
    # TODO(HW): open /dev/i2c-1 or BLE GATT handle, e.g.
    # import smbus2, bme280 etc
    # bus=smbus2.SMBus(1)
    # return real sensor values
```
- Example for BP monitor: vendor SDK C extension `.so` wrapped via ctypes, return same dict shape.
- Keep return shape `{"ts":..., "sys_mmHg":..., "dia_mmHg":..., "temp_c":...}` so upper layers (telemetry) don't change.

### 2. Burn public key — no file on prod
Dev uses `edge_agent/keys/device_pub.pem`. Prod:
- Flash Ed25519 pubkey into ROM / eFuse / ESP32 secure-boot block, not filesystem
- Change `secure_boot.verify_artifact(..., pubkey_path=None)` to read from eFuse driver
- NORE: file placeholder will refuse to verify if HMAC fallback — we intentionally fail ed25519 path so you know

### 3. Move private signing key to KMS/HSM
Dev uses `keys/build_priv.pem` file. Prod:
- Store build private key in AWS KMS / GCP KMS / YubiHSM
- Sign in CI only: `kms:sign(data) -> sig` not `cat priv.pem`
- CI writes `.sig` artifact, uploads to OTA bundle. Private key never leaves HSM.

### 4. Device cert in secure element
- `device_attestation.py` currently reuses build priv file as "TPM". Prod should read from ATECC608, TPM 2.0, or ESP secure element for `create_attest_token()`
- Mark `cert_id` as real cert serial from provisioning station

### 5. Seal the measurement
After you swap driver, recompute and lock allowlist:

```bash
python3 -c "
import sys; sys.path.insert(0,'edge_agent')
import device_attestation as da
m=da.compute_measurement(['edge_driver/driver_stub.py','edge_agent/secure_boot.py','edge_agent/device_attestation.py'])
print(m)
"
# paste that hash into control_plane/attestation/allowlist.json under your new fw version e.g. {"v1-real-hw":[\"<hash>\"]}
```

- Tighten verifier: delete `"any"` open mode, require match in allowlist, quarantine unknown.
- Add rollback protection: monotonic anti-rollback counter in NVS so old FW can't reflash.

### 6. OTA flow (secure)
1. You: build new `driver_stub.py` + driver.so → zip OTA bundle
2. CI: sign zip with KMS → OTA manifest `{version, sha256, sig}` pushed to control plane
3. Control plane: `POST /rollout` progressive 5%->30%->100% (already coded)
4. Edge: downloads, calls `verify_artifact(tmp.zip, tmp.zip.sig)` BEFORE swapping partition, then reboots, re-computes measurement, attests with new measurement

### 7. SBOM / Provenance (SLSA L2)
- Add `manifest.json` per OTA: builder, git SHA `fc2667a`, pip freeze, timestamp
- Sign manifest too — auditor can trace bad release back to build job

### 8. What we intentionally left insecure for dev
- HMAC fallback when PEM missing flagged `PLACEHOLDER-HMAC-KEY-CHANGE-IN-PROD`
- No eFuse read, file-based cert — replace with hardware reads before any PHI pilot
- Allowlist open if no `allowlist.json` — we added strict file now but you must not delete it before ФТГ

### 9. Checklist before field test with real BP monitor
- [ ] pub key in eFuse, verified ROM bootloader halts on wrong sig
- [ ] driver `.so` + `.py` both signed, verified in same boot step
- [ ] attestation token uses TPM priv, nonce from server checked for replay (we check fresh nonce already)
- [ ] quarantine path tested: flash bad driver → boot_fail → fleet health shows offline + quarantine.json has entry
- [ ] OTA rollback test: good → bad canary 5% → auto-blocked on crash spike (analyzer ready, already pushed)
- [ ] local telemetry still works when debug lake flooded (QoS lanes 3-tier already done, p95 13ms at 500 dev)

Ready for you to swap stub now. All plumbing waits in `secure_boot.py` + `verifier.py` for that first real `driver_stub.py real-hw` hash.

