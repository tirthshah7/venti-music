"""
Venti web app — FastAPI skeleton + guardrails (build spec T3.1).

Wires up, in order of appearance: fail-fast settings, structured JSON
logging to stdout (Railway's log capture is the beta's entire analytics
system), a slowapi rate limiter keyed by client IP, an itsdangerous-signed
session cookie (HttpOnly, Secure, SameSite=Lax) hard-limited to four keys,
GET /healthz, the four T3.2 routers (vent, auth, playlist, rating), and
the static frontend at "/".

Privacy invariant (build rule 5): raw vent text never touches a log line
or disk on the server. The logger is event-shaped on purpose — handlers
log `log.info("<event>", extra={...fields})`, never request bodies.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from web.app.config import MissingConfigError, get_settings
from web.app.rate_limit import limiter

try:
    settings = get_settings()
except MissingConfigError as exc:
    # SystemExit prints the message without a traceback and exits 1.
    raise SystemExit(str(exc)) from None


# --- Structured JSON logging (one object per line, stdout) -----------------

# Attributes every LogRecord carries; anything else on the record came in
# via `extra=` and belongs in the JSON line. "color_message" is uvicorn's
# ANSI-formatted duplicate of the message — noise in JSON.
_LOG_RESERVED = frozenset(vars(logging.makeLogRecord({}))) | {
    "message", "asctime", "taskName", "color_message",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _LOG_RESERVED and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    # Route uvicorn's own loggers through the JSON handler too, so every
    # line Railway captures is parseable.
    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers[:] = []
        uv_logger.propagate = True
    # "uvicorn.access" is special: the production start command (T5.3a)
    # passes --no-access-log, which uvicorn implements by stripping the
    # logger's handlers AND its propagation before this module is imported.
    # Re-enabling propagation here would resurrect per-request lines — and
    # with them client IPs — in Railway's captured logs. Reroute it to the
    # JSON handler only when access logging is actually on.
    access = logging.getLogger("uvicorn.access")
    if access.handlers or access.propagate:
        access.handlers[:] = []
        access.propagate = True
    # slowapi's "ratelimit ... exceeded" warning embeds the rate-limit key —
    # the client IP — and would propagate into Railway's captured logs
    # (confirmed there, T5.5). Drop everything below ERROR so storage
    # failures still surface; the anonymous ratelimit_exceeded event below
    # replaces the warning.
    logging.getLogger("slowapi").setLevel(logging.ERROR)


configure_logging()
log = logging.getLogger("venti.web")


# --- Session cookie guardrail ----------------------------------------------

# The spec allows the session to contain AT MOST these keys. Anything else
# is a bug (or worse, vent text drifting into a cookie), so it is stripped
# before signing rather than trusted.
ALLOWED_SESSION_KEYS = frozenset({
    "spotify_access_token",
    "spotify_refresh_token",
    "expires_at",
    "oauth_state",
})


class SessionKeyAllowlistMiddleware:
    """Deletes non-allowlisted session keys just before the response
    starts, i.e. before the outer SessionMiddleware signs the cookie.
    Must sit INSIDE SessionMiddleware (be added to the app first)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def guarded_send(message):
            if message["type"] == "http.response.start":
                session = scope.get("session") or {}
                for key in set(session) - ALLOWED_SESSION_KEYS:
                    del session[key]
                    log.warning(
                        "session_key_stripped", extra={"key": key},
                    )
            await send(message)

        await self.app(scope, receive, guarded_send)


# --- App assembly -----------------------------------------------------------

app = FastAPI(title="Venti")

# Per-route limits (@limiter.limit) live on the routers; the limiter
# itself (web.app.rate_limit) and the 429 handler are wired here.
app.state.limiter = limiter


def rate_limit_handler(request, exc: RateLimitExceeded):
    # Anonymous by design (T5.5): the path and the limit that tripped,
    # never the client IP or any other identifying field. This replaces
    # slowapi's own warning, which is level-suppressed in
    # configure_logging because it embeds the IP.
    log.info(
        "ratelimit_exceeded",
        extra={"path": request.url.path, "limit": str(exc.detail)},
    )
    return _rate_limit_exceeded_handler(request, exc)


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Ordering: the allowlist guard is added FIRST so SessionMiddleware (added
# last = outermost) has already deserialized scope["session"] when the
# guard runs, and signs the guard-filtered dict on the way out.
app.add_middleware(SessionKeyAllowlistMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret,
    same_site="lax",
    https_only=True,  # Secure flag; browsers still accept it on 127.0.0.1
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


# Imported here, not at the top, so the fail-fast settings check above
# runs before the routers' import chain (venti_core, spotipy, anthropic).
from web.app.routers import admin, auth, playlist, rating, vent  # noqa: E402

app.include_router(vent.router)
app.include_router(auth.router)
app.include_router(playlist.router)
app.include_router(rating.router)
app.include_router(admin.router)

# Mounted last so the routes above win; everything else falls through
# to the single-page frontend (real UI lands in Phase 4).
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
