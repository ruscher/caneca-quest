"""HTTP hardening: optional bearer token, body size limits, rate limiting, headers."""

from __future__ import annotations

import hmac
import json
import time
from collections import defaultdict
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from caneca.config import Settings


def _json_error(status: int, code: str) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    body = json.dumps({"error": {"code": code}}).encode()
    return (
        status,
        [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        body,
    )


async def _send_error(send: Send, status: int, code: str) -> None:
    status, headers, body = _json_error(status, code)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    """Pure ASGI middleware (does not buffer streaming responses)."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self.buckets: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope.get("path", "")
        method: str = scope.get("method", "GET")
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        is_api = path.startswith("/api/")

        if is_api and self.settings.api_token and path != "/api/health" and method != "OPTIONS":
            supplied = headers.get("authorization", "")
            expected = f"Bearer {self.settings.api_token}"
            if not hmac.compare_digest(supplied.encode(), expected.encode()):
                await _send_error(send, 401, "unauthorized")
                return

        if is_api and method in ("POST", "PUT", "PATCH", "DELETE") and not self._allow(scope):
            await _send_error(send, 429, "rate_limited")
            return

        limit = (
            self.settings.max_import_bytes if path == "/api/games/import" else self.settings.max_body_bytes
        )
        declared = headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _send_error(send, 413, "payload_too_large")
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _TooLarge()
            return message

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                hdrs = list(message.get("headers", []))
                hdrs += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (b"cross-origin-opener-policy", b"same-origin"),
                ]
                if not is_api:
                    hdrs.append((b"content-security-policy", CSP))
                message["headers"] = hdrs
            await send(message)

        try:
            await self.app(scope, limited_receive, send_with_headers)
        except _TooLarge:
            await _send_error(send, 413, "payload_too_large")

    def _allow(self, scope: Scope) -> bool:
        client: Any = scope.get("client") or ("local", 0)
        key = str(client[0])
        now = time.monotonic()
        window = [t for t in self.buckets[key] if now - t < 60.0]
        if len(window) >= self.settings.rate_limit_per_minute:
            self.buckets[key] = window
            return False
        window.append(now)
        self.buckets[key] = window
        return True


class _TooLarge(Exception):
    pass


CSP = (
    b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    b"img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    b"media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; "
    b"frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
)
