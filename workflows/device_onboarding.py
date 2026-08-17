"""
Device Registration / Provisioning Workflow
How new edge devices come online and scale control plane.

Flow: Manufacture -> Claim -> Register -> Provision Desired State -> First Heartbeat -> Normal Ops

This is meant to be idempotent and audit logged.
"""
import time, json, pathlib, uuid
from typing import Dict
REGISTRY = pathlib.Path("../control_plane/data/devices.json")

class OnboardingWorkflow:
    def __init__(self, control_url="http://localhost:8000"):
        self.control_url = control_url

    def claim_device(self, serial: str, sku: str, owner_id: str) -> Dict:
        """Factory claims device for an owner (QR code scan)"""
        device_id = f"{sku}-{serial[-6:]}-{str(uuid.uuid4())[:4]}"
        token = uuid.uuid4().hex[:24]
        record = {
            "device_id": device_id,
            "serial": serial,
            "sku": sku,
            "owner_id": owner_id,
            "token": token,
            "claimed_at": time.time(),
            "status": "claimed"
        }
        print(f"[onboard] claimed {device_id} for {owner_id}")
        return record

    def register(self, claim: Dict):
        """Hit control plane to auto-create desired entry"""
        import requests
        try:
            r = requests.post(f"{self.control_url}/api/v1/heartbeat", json={
                "device_id": claim["device_id"],
                "sku": claim["sku"],
                "fw_version": "v1",
                "health": {"first_register": True}
            }, timeout=3)
            print(f"[onboard] registered {claim['device_id']} -> {r.status_code}")
        except Exception as e:
            print(f"[onboard] register fail (control offline?) {e}")
        claim["status"]="registered"
        return claim

    def provision(self, device_id: str, cohort="prod", geo="us-west"):
        """Set rollout cohort, config overrides"""
        import requests
        config = {
            "sample_rate_sec": 15 if cohort=="prod" else 5,
            "log_level": "info",
            "geo": geo,
            "cohort": cohort
        }
        # In real prod: this would be an internal API not public rollout
        try:
            requests.post(f"{self.control_url}/api/v1/rollout", json={
                "version":"v1","pct":100,"model_version":"v0","config":config
            }, timeout=3)
        except: pass
        print(f"[onboard] provisioned {device_id} cohort={cohort} geo={geo}")

if __name__ == "__main__":
    wf = OnboardingWorkflow()
    d1 = wf.claim_device(serial="SN12345678", sku="bp-monitor-02", owner_id="hosp_wa_01")
    wf.register(d1)
    wf.provision(d1["device_id"])
