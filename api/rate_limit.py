import math
import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

class RateLimiter:
    def __init__(self, max_requests: int, window_s: float):
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int:
        """Trả 0 nếu cho phép, ngược lại trả số giây phải chờ."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return math.ceil(self.window_s - (now - hits[0]))
            hits.append(now)
            if len(self._hits) > 1000:
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window_s]:
                    del self._hits[k]

            return 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

limiter = RateLimiter(
    max_requests=int(os.getenv('RATE_LIMIT_PER_MIN', '10')),
    window_s=float(os.getenv('RATE_LIMIT_WINDOW_S', '60')),
)

def rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    wait = limiter.check(key)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests, please wait {wait} seconds.",
            headers={"Retry-After": str(wait)},
        )
