# Secured Verified Boot + Remote Attestation — Plumbing

You asked for the term: **Secure Boot / Verified Boot + Attestation**. This is the trust root.

## Problem you flagged
Edge driver code could be tampered on flash, or a cloned device could lie. We need to know the bits running are *our* bits.

## Chain (what we wired now)

### 1. Build side — Code Signing
```
source -> build (CI) -> sign with Ed25519 private key (offline/HSM) -> {firmware.bin + firmware.sig + manifest.json}
```
- manifest includes version, sha256 of bin, sig, sku
- Private key never on device — only CI / KMS holds it
- Public key burned into device ROM/eFuse (or in our sim, `edge_agent/keys/device_pub.pem`)

This term: **Code Signing**

### 2. Device side — Secure / Verified Boot (fails closed)
On power-on:
```
ROM bootloader (immutable) verifies 2nd-stage bootloader sig
  -> 2nd-stage verifies OS/kernel sig
  -> OS verifies app (edge_agent) sig via secure_boot.py
  -> edge_agent verifies driver blob sig before loading
```
If any check fails → halt, emit debug report `boot_fail`, don't phone home as healthy.

For us: `edge_agent/secure_boot.py` `verify_artifact(path, sig_path, pubkey_path)` checks Ed25519 (we fallback to HMAC-SHA256 in sim if no crypto lib).

### 3. Runtime — Measured Boot + Remote Attestation
After boot ok, we produce a PCR-like measurement:

```
measurement = SHA256(bootloader_hash || OS_hash || app_hash || driver_hash)
```
We sign measurement + nonce from server with device cert private key (TPM or secure element). Send to control plane as:

POST /api/v1/attest {device_id, measurement, nonce, cert_chain, signature}
```

Control plane (`control_plane/attestation/verifier.py`):
- Validates cert chain against root CA
- Checks sig matches measurement
- Compares measurement against allow-list of known-good measurements per fw_version
- If ok → marks device "attested", eligible for rollout config. If fail → quarantine list, no config, no OTA, optional block rollout.

Term: **Remote Attestation**

### 4. Where driver fits (placeholder)
Real driver is HW-specios: I2C/SPI sensor, BLE stack, etc. We leave `edge_driver/` as stub:
- `driver_stub.py` — does `init()` `read()` `write()` returning fake vitals
- In real HW, replace `read()` with real sensor read, but boot checks the .so/.bin sig before loading

Everything else (OTA, QoS lanes, data lake, dashboard) keeps working but now gated by attestation state.

### How this maps to equiv systems
- AWS IoT Greengrass: uses Code Signing for components + TPM attestation via Device Defender
- Azure Edge: measured boot via Defender-IoT
- Android Verified Boot: dm-verity + VBMeta chain

We implement same plumbing with pure Python / OpenSSL so you can run on laptop without TPM.

### Next steps for you (real HW)
1. Burn pubkey into ROM/eFuse — not filesystem
2. Move signing key to KMS/HSM, not plain pem
3. Store device private cert in ATECC608 / TPM, not file
4. Add SBOM + SLSA provenance in manifest (who built, when)

All placeholders marked `TODO(HW)`.
