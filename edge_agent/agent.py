"""
Edge Agent - runs on device (WiFi router, Fitbit, BP monitor, etc)
Pull-based desired-state reconciliation + spool-on-fail.
"""
import time, json, pathlib, random, requests, os, sys
DEVICE_ID = os.getenv("DEVICE_ID", f"dev_{random.randint(1000,9999)}")
SKU = os.getenv("SKU", "router-wrt-01")
CONTROL = os.getenv("CONTROL_URL", "http://localhost:8000")
FW_VERSION = os.getenv("FW_VERSION", "v1")
MODEL_VERSION = os.getenv("MODEL_VERSION", "v0")
SPOOL = pathlib.Path("spool.jsonl")

def sensor_job():
    # Plug your real sensor here: read I2C, WiFi scan, BP UART...
    # Sim for generic app
    return {"rssi": random.randint(-80, -20), "cpu_temp": 40+random.random()*15, "anomaly_score": random.random()}

def heartbeat():
    try:
        r = requests.post(f"{CONTROL}/api/v1/heartbeat", json={
            "device_id": DEVICE_ID, "sku": SKU, "fw_version": FW_VERSION,
            "model_version": MODEL_VERSION,
            "health": {"uptime_sec": int(time.time()%100000)}
        }, timeout=5)
        desired = r.json().get("desired", {})
        return desired
    except Exception as e:
        print(f"[agent:{DEVICE_ID}] heartbeat fail {e}, will retry")
        return None

def flush_spool():
    if not SPOOL.exists(): return
    lines = SPOOL.read_text().strip().splitlines()
    ok = []
    for line in lines:
        try:
            requests.post(f"{CONTROL}/api/v1/telemetry", json=json.loads(line), timeout=3)
            ok.append(True)
        except:
            ok.append(False)
            break # stop on first fail
    if all(ok) and ok:
        SPOOL.unlink(missing_ok=True)

def loop_forever():
    print(f"Starting edge_agent {DEVICE_ID} -> {CONTROL}")
    while True:
        desired = heartbeat()
        if desired:
            # Reconcile: if desired fw differs, simulate OTA
            if desired.get("fw_version") and desired["fw_version"] != FW_VERSION:
                print(f"OTA needed {FW_VERSION} -> {desired['fw_version']}, downloading...")
                time.sleep(1) # simulate download + verify
                print("OTA applied (simulated), would reboot in real device")
                # In real device you'd exec self-update; here we just adopt in memory
                global FW_VERSION; FW_VERSION = desired["fw_version"]
            flush_spool()
        # run job
        payload = sensor_job()
        sample = {"device_id": DEVICE_ID, "type": "sensor", "payload": payload, "ts": time.time()}
        try:
            requests.post(f"{CONTROL}/api/v1/telemetry", json=sample, timeout=3)
        except:
            # spool to disk if offline
            with open(SPOOL, "a") as f:
                f.write(json.dumps(sample)+"\n")
        time.sleep(int((desired or {}).get("config", {}).get("sample_rate_sec", 15)))

if __name__ == "__main__":
    loop_forever()
