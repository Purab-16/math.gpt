"""Simple per-IP rate limiter to protect the Gemini and YouTube API quota."""

import time
from collections import deque
from typing import Deque, Dict

from fastapi import Request

from app.exceptions import TooManyRequestsError

# Allowed solve requests per IP address in each time window
MAX_REQUESTS_PER_WINDOW = 10
WINDOW_SECONDS = 60

# Clean up old IP entries when this many IPs are being tracked
CLEANUP_THRESHOLD = 10_000


class RateLimiter:
    """Allow at most `max_requests` per `window_seconds` for each key (IP address)."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Record a request for this key and return False if the limit is exceeded."""
        now = time.monotonic()
        window_start = now - self.window_seconds

        if len(self._hits) > CLEANUP_THRESHOLD:
            self._remove_idle_keys(window_start)

        hits = self._hits.setdefault(key, deque())

        # Drop requests that are outside the current window
        while hits and hits[0] <= window_start:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False

        hits.append(now)
        return True

    def _remove_idle_keys(self, window_start: float) -> None:
        """Forget IPs with no recent requests so memory does not grow forever."""
        idle_keys = [key for key, hits in self._hits.items() if not hits or hits[-1] <= window_start]
        for key in idle_keys:
            del self._hits[key]

    def clear(self) -> None:
        """Reset all counters."""
        self._hits.clear()


solve_rate_limiter = RateLimiter(MAX_REQUESTS_PER_WINDOW, WINDOW_SECONDS)


def check_rate_limit(request: Request) -> None:
    """FastAPI dependency that blocks an IP after too many solve requests.

    On Render, uvicorn must run with --proxy-headers so request.client.host is
    the real user IP and not the proxy IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not solve_rate_limiter.is_allowed(client_ip):
        raise TooManyRequestsError()
