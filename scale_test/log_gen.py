"""
Realistic log generator for what edge devices log at QPS

Example you asked: imagine use case where each device logs at some QPS.

3 personas:
- WiFi router: every 30s channel utilization, client count, backhaul latency logs
- BP monitor: every 60s systolic/diastolic, cuff pressure waveform snippet
- Fitbit-style: every 10s HRV, steps delta

Aggregated at center and processed by log-processor.
"""
import random, time, json

def router_logs():
    return {"type":"wifi_scan","clients":random.randint(0,40),"ch_util":random.random(),"latency_ms":random.randint(5,120)}
def bp_logs():
    return {"type":"bp","systolic":110+random.randint(-10,25),"diastolic":70+random.randint(-8,12),"pulse":65+random.randint(-10,20)}
def wearable_logs():
    return {"type":"hr_hrv","hr":70+random.randint(-20,40),"hrv_ms":30+random.random()*60,"steps_delta":random.randint(0,30)}

generators = [router_logs, bp_logs, wearable_logs]

def batch(n=5):
    return [random.choice(generators)() for _ in range(n)]
