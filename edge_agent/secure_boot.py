"""
Secure Verified Boot — edge side

Sim of real ROM -> bootloader -> OS -> app chain.

verify_artifact(path, sig_path, pubkey_path) -> True/False
- Tries Ed25519 if cryptography lib + real PEM present, else HMAC-SHA256 with shared placeholder key (dev only, marked insecure)

Called before loading driver: fails closed, raises SecureBootError
"""
import hashlib, pathlib, os

class SecureBootError(RuntimeError): pass

def _try_ed25519_verify(data: bytes, sig: bytes, pubpem: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        pub = serialization.load_pem_public_key(pubpem)
        pub.verify(sig, data)
        return True
    except Exception:
        return False

def _hmac_fallback(data: bytes, sig: bytes, key: bytes) -> bool:
    import hmac
    expected = hmac.new(key, data, hashlib.sha256).hexdigest().encode()
    return hmac.compare_digest(expected.strip(), sig.strip())

def verify_artifact(path: str, sig_path: str, pubkey_path: str="keys/device_pub.pem") -> bool:
    p = pathlib.Path(path)
    sigp = pathlib.Path(sig_path)
    pubp = pathlib.Path(pubkey_path)
    if pubp.exists() and pubp.parent.name=="edge_agent":
        pass
    else:
        # resolve relative to this file
        pubp = pathlib.Path(__file__).parent / "keys" / "device_pub.pem"
    if not p.exists() or not sigp.exists() or not pubp.exists():
        raise SecureBootError(f"missing {p}:{p.exists()} {sigp}:{sigp.exists()} {pubp}:{pubp.exists()}")
    data = p.read_bytes()
    sig = sigp.read_bytes()
    pubpem = pubp.read_bytes()
    # first try real Ed25519 if PEM looks like BEGIN PUBLIC KEY
    if b"BEGIN PUBLIC KEY" in pubpem:
        # ed25519 sig is 64 bytes binary; if sig file is base64? we handle both
        try:
            ok = _try_ed25519_verify(data, sig, pubpem)
            if ok: return True
        except: pass
        # also try sig as hex
        try:
            import binascii
            sig_raw = binascii.unhexlify(sig.strip())
            if _try_ed25519_verify(data, sig_raw, pubpem):
                return True
        except: pass
        # if ed25519 says no, fail — don't fallback to HMAC for real key (secure)
        raise SecureBootError(f"signature invalid for {path} (ed25519 check failed)")
    else:
        # placeholder HMAC mode (dev only)
        if _hmac_fallback(data, sig, pubpem):
            return True
        raise SecureBootError(f"HMAC check failed for {path} (dev key)")

def sign_artifact(path: str, privkey_path: str="keys/build_priv.pem", out_sig: str=None):
    """Factory side helper — sign artifact with build private key"""
    from pathlib import Path
    privp = Path(privkey_path)
    if not privp.is_absolute():
        privp = Path(__file__).parent / "keys" / "build_priv.pem"
    data = Path(path).read_bytes()
    # Ed25519 if possible
    if privp.read_bytes().startswith(b"-----BEGIN"):
        try:
            from cryptography.hazmat.primitives import serialization
            priv = serialization.load_pem_private_key(privp.read_bytes(), password=None)
            sig = priv.sign(data)
            Path(out_sig or f"{path}.sig").write_bytes(sig)
            return out_sig or f"{path}.sig"
        except Exception as e:
            raise RuntimeError(f"ed25519 sign failed {e}")
    else:
        import hmac, hashlib
        sig = hmac.new(privp.read_bytes(), data, hashlib.sha256).hexdigest()
        Path(out_sig or f"{path}.sig").write_text(sig)
        return out_sig or f"{path}.sig"
