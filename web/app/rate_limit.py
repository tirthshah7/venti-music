"""
The slowapi Limiter, in its own module so both main.py (app wiring) and
the routers (per-route @limiter.limit decorators) can import it without
a circular import.

Keyed by client IP. Deploy note (T5.3): behind Railway's proxy, run
uvicorn with --proxy-headers --forwarded-allow-ips="*" so request.client
reflects the real client IP from X-Forwarded-For — otherwise every
visitor shares the proxy's IP and one rate-limit bucket.

T5.5 dev bypass: when the RATELIMIT_BYPASS_TOKEN env var is set, a request
carrying the same value in its X-Debug-Token header skips rate limiting on
every route. With the env var unset the bypass is inert. The token is
compared in constant time and never logged.
"""
import os
import secrets

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

BYPASS_ENV_VAR = "RATELIMIT_BYPASS_TOKEN"
BYPASS_HEADER = "x-debug-token"


def ratelimit_bypassed(request: Request) -> bool:
    """slowapi exempt_when hook (single parameter → called with the request).
    Exempted requests skip the limit check entirely and consume nothing."""
    expected = os.environ.get(BYPASS_ENV_VAR, "")
    if not expected:
        return False
    supplied = request.headers.get(BYPASS_HEADER, "")
    return secrets.compare_digest(supplied, expected)


class BypassableLimiter(Limiter):
    """Wires the dev bypass into every @limiter.limit(...) declaration so
    individual routers can't forget it (or wire it differently)."""

    def limit(self, *args, **kwargs):
        kwargs.setdefault("exempt_when", ratelimit_bypassed)
        return super().limit(*args, **kwargs)


limiter = BypassableLimiter(key_func=get_remote_address)
