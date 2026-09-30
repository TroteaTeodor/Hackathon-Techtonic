"""Request limits against resource exhaustion: body size and a per-client rate limit on writes."""

import threading
import time
from collections import deque

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_TRACKED_CLIENTS = 10_000


class WriteRateLimiter:
    """Sliding one-minute window per client IP. In-memory, single process (like the login limiter)."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.get(client)
            if q is None:
                if len(self._hits) >= MAX_TRACKED_CLIENTS:  # bound memory: drop the stalest client
                    self._hits.pop(next(iter(self._hits)))
                q = self._hits[client] = deque()
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


write_limiter = WriteRateLimiter(settings.write_rate_limit_per_minute)


class RequestLimitsMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["method"] in WRITE_METHODS:
            client = scope.get("client")
            if not write_limiter.allow(client[0] if client else "unknown"):
                await JSONResponse({"detail": "Too many requests, slow down"}, status_code=429)(scope, receive, send)
                return

        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > self.max_body_bytes):
            await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
            return

        # Also guard streamed bodies without a Content-Length.
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise BodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except BodyTooLarge:
            await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)


class BodyTooLarge(Exception):
    pass
