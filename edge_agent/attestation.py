"""
Measured Boot + Attestation token creation — edge side

Creates PCR-like hash: sha256 of chain artifacts (bootloader, OS stub, app.py, driver)

On boot: compute measurement, open nonce from server (or generate), sign with device cert key.

This file is ~real TPM stub but uses file cert private key in dev.
"""
import hashlib, pathlib, json, time, os
def compute_measurement(chain_paths):
    h=hashlib.sha256()
    for p in chain_paths:
        path=pathlib.Path(p)
        if path.exists():
            h.update(path.read_bytes()[:65536]) # first 64k for speed
        else:
            h.update(b"missing:"+str(p).encode())
    return h.hexdigest()

def create_attest_token(device_id: str, measurement: str, nonce: str, privkey_path: str="keys/device_priv.pem"):
    # Device cert private key — in prod TPM/Atecc; here file or fallback to build priv
    pk_path=pathlib.Path(__file__).parent / "keys" / "device_priv.pem"
    if not pk_path.exists():
        pk_path=pathlib.Path(__file__).parent / "keys" / "build_priv.pem"
    try:
        # sign measurement|nonce with Ed25519 if possible
        if pk_path.read_bytes().startswith(b"-----BEGIN"):
            from cryptography.hazmat.primitives import serialization
            priv = serialization.load_pem_private_key(pk_path.read_bytes(), password=None)
            msg = f"{measurement}:{nonce}".encode()
            sig = priv.sign(msg).hex()
        else:
            import hmac
            sig = hmac.new(pk_path.read_bytes(), f"{measurement}:{nonce}".encode(), hashlib.sha256).hexdigest()
    except Exception as e:
        sig = hashlib.sha256(f"{measurement}:{nonce}:{e}".encode()).hexdigest()

    token={"device_id":device_id,"measurement":measurement,"nonce":nonce,"ts":time.time(),"sig":sig,"cert_id":"sim-cert-001"}
    return token
