"""
Circuit Breaker - per downstream protection

Classic 3 states: CLOSED (normal), OPEN (fail fast 60s), HALF_OPEN (probe)

Use wrapping lake writer / DB write to not hang requests when S3 slow.

Example:
  breaker = CircuitBreaker(name="lake_writer", fail_threshold=5, open_sec=60)
  breaker.call(lambda: write_to_lake(...))
"""
import time, threading
from enum import Enum

class State(Enum):
    CLOSED=1
    OPEN=2
    HALF_OPEN=3

class CircuitBreaker:
    def __init__(self, name, fail_threshold=5, open_sec=60):
        self.name=name
        self.threshold=fail_threshold
        self.open_sec=open_sec
        self.fail_count=0
        self.state=State.CLOSED
        self.opened_at=None
        self.lock=threading.Lock()

    def call(self, fn, *args, **kwargs):
        with self.lock:
            if self.state==State.OPEN:
                if time.time()-self.opened_at>self.open_sec:
                    self.state=State.HALF_OPEN
                else:
                    raise RuntimeError(f"circuit {self.name} OPEN - fast-fail")
        try:
            out=fn(*args, **kwargs)
            with self.lock:
                self.fail_count=0
                if self.state==State.HALF_OPEN:
                    self.state=State.CLOSED
            return out
        except Exception as e:
            with self.lock:
                self.fail_count+=1
                if self.fail_count>=self.threshold:
                    self.state=State.OPEN
                    self.opened_at=time.time()
            raise e

# Singleton breakers for our two rivers
lake_breaker=CircuitBreaker("lake_writer")
debug_breaker=CircuitBreaker("debug_writer", fail_threshold=10, open_sec=30)
