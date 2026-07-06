import os
import sys

import pytest

# repo root, so `web.app...` imports resolve
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

_REQUIRED_ENV = {
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "SPOTIFY_CLIENT_ID": "test-client-id",
    "SPOTIFY_CLIENT_SECRET": "test-client-secret",
    "SPOTIFY_REDIRECT_URI": "http://127.0.0.1:8000/api/auth/callback",
    "APP_SECRET": "test-app-secret-long-enough",
}


@pytest.fixture()
def required_env(monkeypatch):
    """The five required env vars, set to dummies. Returns name → value."""
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    return dict(_REQUIRED_ENV)


@pytest.fixture()
def main_module(required_env):
    from web.app import main  # module-level settings resolve on first import

    return main


@pytest.fixture()
def client(main_module):
    from fastapi.testclient import TestClient

    # https base URL so the TestClient cookie jar accepts Secure cookies.
    return TestClient(main_module.app, base_url="https://testserver")
