"""Small production guards for the API: per-client rate limiting and client-IP detection."""

import threading
import time
from collections import defaultdict, deque

from starlette.requests import Request


class RateLimiter:
    """Sliding-window limiter: at most `per_minute` requests per key (client IP) in any 60 seconds."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls = 0

    def check(self, key: str) -> float | None:
        """Record one request. Returns None if allowed, else the seconds to wait before retrying."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return max(1.0, 60 - (now - hits[0]))
            hits.append(now)
            self._calls += 1
            if self._calls % 1000 == 0:  # forget clients that have gone quiet
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > 60]:
                    del self._hits[k]
            return None


def client_ip(request: Request, trust_proxy: bool) -> str:
    """The real client IP. Behind the web proxy, that is the first X-Forwarded-For entry."""
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
