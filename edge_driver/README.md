# Edge Driver — Placeholder

This dir is where real HW driver code lives.

- `driver_stub.py` implements `init()` `read()` `write()` with fake values but same signature real driver will have.

In prod:
- `read()` → I2C/BLE sensor read (BP monitor, Wi-Fi chipset stats)
- Boot flow checks `driver_stub.py` signature via `secure_boot.verify_artifact()` before import. Tampered .so/.py blocks boot.
- OTA replaces driver file + `.sig` atomically, then secure_boot re-checks on next reboot.

Next steps you said you'd do later: drop your real vendor SDK / C extension `.so` here, add matching `driver_stub.py.sig`, and update `measurement_allowlist` in control plane so attestation passes.

No secrets in this dir — pub key only.
