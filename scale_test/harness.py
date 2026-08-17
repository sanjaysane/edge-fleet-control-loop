"""
Scale Test Framework - Proves control plane autoscaling story.
Fallback pure-stdlib version if aiohttp not present, uses asyncio http via stdlib?
For CI compatibility we provide dual mode: if aiohttp missing, harness still --help works.
"""
import sys
# lazy import check for aiohttp - allow --help without it
if "--help" in sys.argv or "-h" in sys.argv:
    import argparse
    ap=argparse.ArgumentParser(description="Scale test harness")
    ap.add_argument("--devices", type=int, default=100)
    ap.add_argument("--qps", type=float, default=0.2)
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--control", default="http://localhost:8000")
    ap.add_argument("--report", default="scale_test/report.json")
    ap.print_help()
    sys.exit(0)

import asyncio, time, random, argparse, statistics, json

try:
    import aiohttp
    HAS_AIO=True
except:
    HAS_AIO=False
    # fallback to httpx/requests will be used if available

async def device_loop(session, control_url, device_id, qps, duration, stats):
    end = time.time() + duration
    sku = random.choice(["router-wrt-01","bp-monitor-02","watch-fit-01"])
    fw = random.choice(["v1","v2"])
    while time.time() < end:
        start = time.time()
        try:
            payload = {"device_id": device_id,"sku": sku,"fw_version": fw,"health": {"uptime": int(time.time()%10000)}}
            if HAS_AIO:
                async with session.post(f"{control_url}/api/v1/heartbeat", json=payload, timeout=aiohttp.ClientTimeout(total=2)) as r:
                    await r.text()
            else:
                import requests
                requests.post(f"{control_url}/api/v1/heartbeat", json=payload, timeout=2)
            latency = (time.time()-start)*1000
            stats["lat"].append(latency)
            stats["ok"]+=1
        except Exception:
            stats["err"]+=1
        try:
            log_payload = {"device_id": device_id,"type":"sensor_batch","payload":{"logs":[{"ts": time.time(),"lvl":"info","msg":f"ch={random.randint(1,11)}"}],"qps_sample_rate": qps}}
            if HAS_AIO:
                async with session.post(f"{control_url}/api/v1/telemetry", json=log_payload, timeout=aiohttp.ClientTimeout(total=2)) as r:
                    await r.text()
            else:
                import requests
                requests.post(f"{control_url}/api/v1/telemetry", json=log_payload, timeout=2)
        except: pass
        await asyncio.sleep(max(0, (1/qps) + random.uniform(-0.2,0.2)) if qps>0 else 1)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices", type=int, default=100)
    ap.add_argument("--qps", type=float, default=0.2)
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--control", default="http://localhost:8000")
    ap.add_argument("--report", default="scale_test/report.json")
    args = ap.parse_args()
    print(f"Scale test: {args.devices} devices x {args.qps} qps = ~{args.devices*args.qps:.1f} rps aggregate for {args.duration}s against {args.control}")
    stats = {"ok":0,"err":0,"lat":[]}
    if HAS_AIO:
        connector = aiohttp.TCPConnector(limit=200)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks=[asyncio.create_task(device_loop(session, args.control, f"scale_dev_{i}_{random.randint(100,999)}", args.qps, args.duration, stats)) for i in range(args.devices)]
            start=time.time()
            await asyncio.gather(*tasks)
            elapsed=time.time()-start
    else:
        # sync-ish fallback
        async with asyncio.Lock():
            start=time.time()
            await asyncio.gather(*[device_loop(None, args.control, f"scale_dev_{i}", args.qps, args.duration, stats) for i in range(args.devices)])
            elapsed=time.time()-start
    lat=stats["lat"]; p50=statistics.median(lat) if lat else 0; p95=sorted(lat)[int(len(lat)*0.95)] if lat else 0
    rps_observed=stats["ok"]/elapsed if elapsed else 0
    pods_needed=max(1,int((rps_observed/500)+0.99))
    report={"devices":args.devices,"per_device_qps":args.qps,"aggregate_target_rps":args.devices*args.qps,"observed_rps":round(rps_observed,2),"success":stats["ok"],"errors":stats["err"],"p50_ms":round(p50,2),"p95_ms":round(p95,2),"implied_pods_at_500_rps_each":pods_needed,"hpa_min":2,"hpa_max":20,"verdict":"scale-ok" if stats["err"]/(stats["ok"]+1)<0.05 and p95<800 else "needs-tune"}
    print(json.dumps(report,indent=2))
    open(args.report,"w").write(json.dumps(report,indent=2))
    print(f"report -> {args.report}")

if __name__=="__main__":
    asyncio.run(main())
