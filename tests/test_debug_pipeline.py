import pathlib, json, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "control_plane"))
from fastapi.testclient import TestClient
import app as app_module
# reload to get fresh db
import importlib; importlib.reload(app_module)
from app import app

client=TestClient(app)

def test_debug_and_data_isolation():
    for i in range(5):
        client.post("/api/v1/debug", json={
            "device_id": f"bad_01",
            "fw_version": "v_bad",
            "level": "panic",
            "signature": "null deref @ wifi_scan.c:142",
            "stack": "trace..."
        })
    r=client.post("/api/v1/telemetry", json={"device_id":"good_01","type":"sensor","payload":{"temp":22}})
    assert r.status_code==200
    r2=client.get("/api/v1/debug/summary")
    assert r2.status_code==200
    j=r2.json()
    assert "reports" in j or "blocked_versions" in j

def test_blocked_version_cannot_full_rollout():
    # ensure device exists
    client.post("/api/v1/heartbeat", json={"device_id":"d1","sku":"x","fw_version":"v1"})
    # manipulate db directly in this process - app.db is module global
    app_module.db.setdefault("blocked",[])
    if "v_spike_blocked" not in app_module.db["blocked"]:
        app_module.db["blocked"].append("v_spike_blocked")
    app_module.save_db(app_module.db)
    r=client.post("/api/v1/rollout", json={"version":"v_spike_blocked","pct":100})
    assert r.status_code==409
    # cleanup
    if "v_spike_blocked" in app_module.db["blocked"]:
        app_module.db["blocked"].remove("v_spike_blocked")
        app_module.save_db(app_module.db)

