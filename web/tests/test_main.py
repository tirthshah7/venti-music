"""
T3.1 skeleton tests: fail-fast config, /healthz, static frontend, session
cookie guardrails, JSON logging. Endpoint behavior lives in
test_routers.py (T3.2).
"""
import json
import logging

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

# --- config.py ---------------------------------------------------------------


def test_missing_env_vars_listed_in_startup_error(required_env, monkeypatch):
    from web.app import config

    for key in required_env:
        monkeypatch.delenv(key)
    with pytest.raises(config.MissingConfigError) as exc_info:
        config.load_settings()
    message = str(exc_info.value)
    for key in required_env:
        assert key in message


def test_empty_env_var_treated_as_missing(required_env, monkeypatch):
    from web.app import config

    monkeypatch.setenv("APP_SECRET", "")
    with pytest.raises(config.MissingConfigError, match="APP_SECRET"):
        config.load_settings()


def test_optional_defaults(required_env, monkeypatch):
    from web.app import config

    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    settings = config.load_settings()
    assert settings.llm_backend == "api"
    assert settings.anthropic_model is None


def test_invalid_llm_backend_rejected(required_env, monkeypatch):
    from pydantic import ValidationError

    from web.app import config

    monkeypatch.setenv("LLM_BACKEND", "carrier-pigeon")
    with pytest.raises(ValidationError):
        config.load_settings()


# --- main.py -----------------------------------------------------------------


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_static_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_rate_limiter_wired(main_module):
    assert main_module.app.state.limiter is main_module.limiter


def test_session_middleware_flags(main_module):
    sm = next(
        m for m in main_module.app.user_middleware if m.cls is SessionMiddleware
    )
    assert sm.kwargs["https_only"] is True  # Secure
    assert sm.kwargs["same_site"] == "lax"


def test_session_guard_strips_unexpected_keys(main_module):
    async def write_session(request):
        request.session["oauth_state"] = "abc"
        request.session["vent_text"] = "must never survive"
        return JSONResponse({"ok": True})

    async def read_session(request):
        return JSONResponse(dict(request.session))

    # Same middleware geometry as the real app: SessionMiddleware
    # outermost, allowlist guard inside it.
    tiny_app = Starlette(
        routes=[Route("/write", write_session), Route("/read", read_session)],
        middleware=[
            Middleware(
                SessionMiddleware,
                secret_key="test-secret",
                https_only=True,
                same_site="lax",
            ),
            Middleware(main_module.SessionKeyAllowlistMiddleware),
        ],
    )
    tiny_client = TestClient(tiny_app, base_url="https://testserver")

    write_response = tiny_client.get("/write")
    set_cookie = write_response.headers["set-cookie"]
    assert "httponly" in set_cookie.lower()
    assert "secure" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()

    assert tiny_client.get("/read").json() == {"oauth_state": "abc"}


def test_configure_logging_respects_no_access_log(main_module):
    # T5.3a: the production start command passes --no-access-log, which
    # uvicorn implements by stripping uvicorn.access's handlers AND its
    # propagation BEFORE our module imports. configure_logging() must not
    # resurrect the logger (access lines carry client IPs into Railway's
    # captured logs) — but must still reroute it to JSON when it's on.
    access = logging.getLogger("uvicorn.access")
    saved = (access.handlers[:], access.propagate)
    try:
        # Disabled state (as uvicorn leaves it under --no-access-log).
        access.handlers[:] = []
        access.propagate = False
        main_module.configure_logging()
        assert access.propagate is False
        assert not access.handlers
        assert not access.hasHandlers()  # what uvicorn's protocol checks

        # Enabled state (uvicorn's default: own handler, no propagation) —
        # rerouted to the root JSON handler.
        access.handlers[:] = [logging.NullHandler()]
        access.propagate = False
        main_module.configure_logging()
        assert access.propagate is True
        assert not access.handlers
    finally:
        access.handlers[:], access.propagate = saved
        main_module.configure_logging()


def test_json_log_formatter(main_module):
    record = logging.LogRecord(
        name="venti.web",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="rating",
        args=(),
        exc_info=None,
    )
    record.strategy = "diversion"
    record.rating = 2
    parsed = json.loads(main_module.JsonLogFormatter().format(record))
    assert parsed["event"] == "rating"
    assert parsed["level"] == "info"
    assert parsed["strategy"] == "diversion"
    assert parsed["rating"] == 2
    assert "ts" in parsed
