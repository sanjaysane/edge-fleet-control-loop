"""Edge agent variant showing how to cap debug logs to not kill data pipe"""
import time, json, pathlib, random, requests, os
DEVICE_ID=os.getenv("DEVICE_ID","dev_01")
CONTROL=os.getenv("CONTROL_URL","http://localhost:8000")
DEBUG_SPOOL=pathlib.Path("debug_spool.jsonl")
DEBUG_CAP_KB=64
DEBUG_WINDOW_SEC=300
last_window=time.time()
debug_bytes=0

def send_debug(signature, level="error"):
    global debug_bytes, last_window
    now=time.time()
    if now-last_window>DEBUG_WINDOW_SEC:
        debug_bytes=0
        last_window=now
    payload_size=200
    if debug_bytes+payload_size>DEBUG_CAP_KB*1024:
        # Drop oldest - protect data pipe
        return
    try:
        requests.post(f"{CONTROL}/api/v1/debug", json={
            "device_id":DEVICE_ID, "fw_version": os.getenv("FW_VERSION","v1"),
            "level": level, "signature": signature, "stack": "sim trace"
        }, timeout=2)
        debug_bytes+=payload_size
    except: pass

# Example: if new fw crashes 10 times, we only send first ~64KB
for i in range(10):
    send_debug(f"crash loop {i} @ main.c:{100+i}")
