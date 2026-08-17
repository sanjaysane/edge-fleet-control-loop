"""Simple Prometheus-style metrics for HPA custom metric http_requests_per_second"""
import time
from collections import deque
from fastapi import Request

class RPSCounter:
    def __init__(self, window_sec=60):
        self.timestamps = deque()
        self.window = window_sec
    def hit(self):
        now = time.time()
        self.timestamps.append(now)
        # evict old
        while self.timestamps and now - self.timestamps[0] > self.window:
            self.timestamps.popleft()
    def rps(self):
        return len(self.timestamps) / self.window if self.timestamps else 0

rps_counter = RPSCounter()

async def track_rps(request: Request, call_next):
    rps_counter.hit()
    response = await call_next(request)
    response.headers["X-RPS"] = str(round(rps_counter.rps(),2))
    return response
