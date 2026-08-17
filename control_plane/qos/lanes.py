"""
QoS Lanes - Priority queuing so critical beats bulk

Lane0 critical: BP monitor panic, OTA ack, heartbeat
Lane1 default: router stats, normal telemetry
Lane2 bulk/debug: debug logs, batched old spool

Token bucket per lane, refreshed each second by middleware.

Usage in FastAPI:
  app.middleware("http")(qos_middleware)
"""
import time
from collections import defaultdict

class TokenBucket:
    def __init__(self, rate_per_sec, burst):
        self.rate=rate_per_sec
        self.burst=burst
        self.tokens=burst
        self.last=time.time()
    def allow(self, n=1):
        now=time.time()
        # refill
        elapsed=now-self.last
        self.tokens=min(self.burst, self.tokens+elapsed*self.rate)
        self.last=now
        if self.tokens>=n:
            self.tokens-=n
            return True
        return False

# 3 lanes
buckets={
    "critical": TokenBucket(500, 800),  # high quota
    "default": TokenBucket(300, 500),
    "bulk": TokenBucket(50, 100)  # debug, backfill
}

def sku_to_lane(sku: str, path: str):
    # heuristic
    if "bp-monitor" in sku or "panic" in path or "/heartbeat" in path:
        return "critical"
    if "/debug" in path:
        return "bulk"
    return "default"

stats=defaultdict(int) # drops per lane

async def qos_middleware(request, call_next):
    path=request.url.path
    sku=request.headers.get("X-Device-Sku","")
    lane=sku_to_lane(sku, path)
    if not buckets[lane].allow():
        stats[lane]+=1
        from fastapi.responses import JSONResponse
        # Tell bulk callers to back off hard
        headers={"Retry-After":"5","X-QOS-Lane":lane}
        if lane=="bulk":
            headers["X-Debug-Sampling"]="5"
        return JSONResponse(status_code=429, content={"error":"qos_limit", "lane":lane, "retry_after_sec":5}, headers=headers)
    resp=await call_next(request)
    resp.headers["X-QOS-Lane"]=lane
    return resp
