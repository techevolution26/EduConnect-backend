"""
Lightweight in-process rate limiting.

WHY THIS EXISTS
----------------
The original codebase had zero rate limiting anywhere -- /auth/login and
/auth/register could be brute-forced or spammed without any friction, and
the M-Pesa callback endpoint (even once secret-gated, see routers/
partnerships.py) had no protection against being hammered.

WHAT THIS IS (AND ISN'T)
-------------------------
This is a simple in-memory sliding-window limiter keyed by client IP. It is
NOT a substitute for a proper rate limiter in front of multiple app
instances (e.g. Redis-backed, or handled at the load balancer / API
gateway level) -- state here is per-process and resets on restart, and
won't coordinate across horizontally-scaled replicas. For a single-instance
deployment (common for an early-stage platform like this one) it's a real,
functional improvement over having nothing. When  scaling to multiple
backend instances,i'll replace the in-memory store below with Redis (the
public interface -- `check_rate_limit` -- won't need to change at call
sites).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class _SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds

        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again shortly.",
            )

        hits.append(now)


_limiter = _SlidingWindowLimiter()


def _client_key(request: Request, *, scope: str) -> str:
    # Prefer X-Forwarded-For's first hop if present (common behind a
    # reverse proxy / load balancer); fall back to the direct client host.
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    return f"{scope}:{client_ip}"


def rate_limit(scope: str, *, max_requests: int, window_seconds: int):
    """FastAPI dependency factory. Usage:

    @router.post("/login", dependencies=[Depends(rate_limit("login", max_requests=10, window_seconds=60))])
    """

    def dependency(request: Request) -> None:
        key = _client_key(request, scope=scope)
        _limiter.check(key, max_requests=max_requests, window_seconds=window_seconds)

    return dependency
