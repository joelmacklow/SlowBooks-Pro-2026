from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException
from starlette.requests import Request

_rate_limit_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_limit_lock = Lock()


def clear_rate_limits() -> None:
    with _rate_limit_lock:
        _rate_limit_buckets.clear()


def _client_host(request: Request | None) -> str:
    if request is None or request.client is None or not request.client.host:
        return "direct-call"
    return request.client.host


def enforce_rate_limit(
    request: Request | None,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    detail: str,
) -> None:
    if request is None:
        return

    now = monotonic()
    bucket_key = f"{scope}:{_client_host(request)}"

    with _rate_limit_lock:
        bucket = _rate_limit_buckets[bucket_key]
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail=detail)
        bucket.append(now)
