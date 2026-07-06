"""
The slowapi Limiter, in its own module so both main.py (app wiring) and
the routers (per-route @limiter.limit decorators) can import it without
a circular import.

Keyed by client IP. Deploy note (T5.3): behind Railway's proxy, run
uvicorn with --proxy-headers --forwarded-allow-ips="*" so request.client
reflects the real client IP from X-Forwarded-For — otherwise every
visitor shares the proxy's IP and one rate-limit bucket.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
