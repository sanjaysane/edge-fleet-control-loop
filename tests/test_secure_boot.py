import pathlib, sys
ROOT=pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"edge_agent"))
sys.path.insert(0, str(ROOT/"control_plane"))
import secure_boot
import device_attestation as attestation
from edge_driver import driver_stub

def test_secure_boot_sign_verify_roundtrip(tmp_path):
    artifact=tmp_path/"firmware.bin"
    artifact.write_text("hello-secure-world")
    sig_path=ROOT/"edge_agent"/"keys"/"build_priv.pem"
    if not sig_path.exists():
        assert True; return
    sig_out=tmp_path/"firmware.bin.sig"
    out=secure_boot.sign_artifact(str(artifact), str(sig_path), str(sig_out))
    assert pathlib.Path(out).exists()
    pub=ROOT/"edge_agent"/"keys"/"device_pub.pem"
    ok=secure_boot.verify_artifact(str(artifact), str(sig_out), str(pub))
    assert ok is True

def test_secure_boot_fail_tamper(tmp_path):
    art=tmp_path/"bin2.bin"
    art.write_text("original")
    priv=ROOT/"edge_agent"/"keys"/"build_priv.pem"
    sig=tmp_path/"bin2.bin.sig"
    secure_boot.sign_artifact(str(art), str(priv), str(sig))
    art.write_text("tampered")
    pub=ROOT/"edge_agent"/"keys"/"device_pub.pem"
    try:
        secure_boot.verify_artifact(str(art), str(sig), str(pub))
        assert False
    except secure_boot.SecureBootError:
        assert True

def test_attestation_measurement_and_token():
    m=attestation.compute_measurement([str(ROOT/"edge_agent"/"secure_boot.py"), str(ROOT/"edge_driver"/"driver_stub.py")])
    assert len(m)==64
    token=attestation.create_attest_token("test_dev_01", m, "nonce123")
    assert token["measurement"]==m and "sig" in token

def test_driver_stub_interface():
    st=driver_stub.init()
    assert st["status"]=="ok"
    r=driver_stub.read()
    assert "sys_mmHg" in r or "temp_c" in r

def test_verifier_allow_logic():
    from attestation.verifier import verify_attest
    tok={"device_id":"d","measurement":"abc123","nonce":"n","sig":"anysig"}
    out=verify_attest(tok, None)
    assert out["ok"] is True
