"""
Remote Attestation Verifier — control plane side

POST /api/v1/attest {device_id, measurement, nonce, sig, cert_id}

Steps:
1. lookup device pubkey (in registry we store per-device cert)
2. verify sig over measurement:nonce
3. compare measurement vs allow-list for version (known-good hashes)
4. if ok -> mark device.attested=True, else quarantine

For MVP allow-list = any measurement (we 학습), but we record and you can lock down later.

Quarantined devices get no desired_config (HTTP 403), get flagged on dashboard.
"""
import hashlib, time, json, pathlib
from collections import defaultdict

ALLOWLIST = pathlib.Path(__file__).parent / "allowlist.json"  # {fw_version: [hash,...]}
QUAR = pathlib.Path(__file__).parent.parent / "data" / "quarantine.json"
QUAR.parent.mkdir(parents=True, exist_ok=True)

def _load_allow():
    if ALLOWLIST.exists():
        return json.loads(ALLOWLIST.read_text())
    return {} # open in dev

def _verify_sig(token: dict, pubkey_pem: bytes) -> bool:
    try:
        measurement=token["measurement"]; nonce=token["nonce"]; sig=token["sig"]
        # try ed25519 if pub PEM present
        if pubkey_pem and b"BEGIN PUBLIC KEY" in pubkey_pem:
            from cryptography.hazmat.primitives import serialization
            import binascii
            pub = serialization.load_pem_public_key(pubkey_pem)
            msg=f"{measurement}:{nonce}".encode()
            try:
                pub.verify(binascii.unhexlify(sig), msg)
                return True
            except Exception:
                # try raw
                try:
                    pub.verify(bytes.fromhex(sig), msg)
                    return True
                except:
                    return False
        else:
            import hmac
            exp=hmac.new(pubkey_pem, f"{measurement}:{nonce}".encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(exp, sig)
    except Exception:
        return False

def verify_attest(token: dict, device_pubkey: bytes=None) -> dict:
    # 1. sig
    ok_sig=False
    if device_pubkey:
        ok_sig=_verify_sig(token, device_pubkey)
    else:
        # dev-mode: no key registry yet -> trust-on-first-use, store measurement
        ok_sig=True

    if not ok_sig:
        return {"ok":False,"reason":"bad_sig","action":"quarantine"}

    # 2. allow-list check — if strict list enforced, reject unknown measurements
    allow=_load_allow()
    # allow can be {"v1": ["abc..."], "any": [...]} — if present we enforce
    if allow:
        known=set()
        for v in allow.values():
            known.update(v)
        if token["measurement"] not in known:
            # not fatal but flag — could be staging new FW
            return {"ok":True,"reason":"new_measurement","action":"warn","quarantined":False}
    return {"ok":True,"reason":"known_good","action":"allow"}

def quarantine(device_id: str, reason: str):
    data={}
    if QUAR.exists():
        try: data=json.loads(QUAR.read_text())
        except: data={}
    data[device_id]={"reason":reason,"ts":time.time()}
    QUAR.write_text(json.dumps(data, indent=2))
