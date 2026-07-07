"""
Unit tests for the manual Authorization Code flow (build spec T2.2).
No network — httpx.MockTransport stands in for Spotify.
"""
import base64
import inspect
import json
import time
from datetime import date
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from web.app.spotify import user_client
from web.app.spotify.user_client import TokenSet


@pytest.fixture(autouse=True)
def spotify_env(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")


@pytest.fixture
def transport(monkeypatch):
    """Install a MockTransport wrapping `handler`; returns the list of
    requests it sees."""
    def install(handler):
        seen: list[httpx.Request] = []

        def recording_handler(request):
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(
            user_client, "_test_transport", httpx.MockTransport(recording_handler)
        )
        return seen

    return install


def _token_response(payload):
    return lambda request: httpx.Response(200, json=payload)


# --- authorize URL -----------------------------------------------------

def test_authorize_url_scope_is_exactly_playlist_modify_private():
    q = parse_qs(urlparse(user_client.build_authorize_url(state="abc123")).query)
    assert q["scope"] == ["playlist-modify-private"]


def test_authorize_url_shape_and_no_secret():
    url = user_client.build_authorize_url(state="abc123")
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.spotify.com"
    assert parsed.path == "/authorize"
    q = parse_qs(parsed.query)
    assert q["response_type"] == ["code"]
    assert q["client_id"] == ["test-client-id"]
    assert q["state"] == ["abc123"]
    assert "test-client-secret" not in url


def test_generate_state_is_urlsafe_and_unique():
    states = {user_client.generate_state() for _ in range(50)}
    assert len(states) == 50
    for s in states:
        assert len(s) >= 40  # token_urlsafe(32) -> 43 chars
        assert all(c.isalnum() or c in "-_" for c in s)


# --- token endpoint ----------------------------------------------------

def test_exchange_code_posts_basic_auth_to_accounts(transport):
    seen = transport(_token_response(
        {"access_token": "acc-1", "refresh_token": "ref-1", "expires_in": 3600}
    ))
    tokens = user_client.exchange_code("the-code")

    req = seen[0]
    assert req.url == user_client.TOKEN_URL
    expected = "Basic " + base64.b64encode(
        b"test-client-id:test-client-secret"
    ).decode()
    assert req.headers["Authorization"] == expected
    body = parse_qs(req.content.decode())
    assert body["grant_type"] == ["authorization_code"]
    assert body["code"] == ["the-code"]
    assert body["redirect_uri"] == ["http://127.0.0.1:8888/callback"]

    assert tokens.access_token == "acc-1"
    assert tokens.refresh_token == "ref-1"
    assert tokens.expires_at > time.time() + 3000
    assert not tokens.is_expired()


def test_refresh_keeps_old_refresh_token_when_response_omits_it(transport):
    transport(_token_response({"access_token": "acc-2", "expires_in": 3600}))
    tokens = user_client.refresh("ref-original")
    assert tokens.access_token == "acc-2"
    assert tokens.refresh_token == "ref-original"


def test_refresh_adopts_rotated_refresh_token_when_present(transport):
    transport(_token_response(
        {"access_token": "acc-3", "refresh_token": "ref-rotated", "expires_in": 3600}
    ))
    assert user_client.refresh("ref-original").refresh_token == "ref-rotated"


# --- playlist creation -------------------------------------------------

def test_create_playlist_is_private_and_returns_url(transport):
    def handler(request):
        path = request.url.path
        if path == "/v1/me/playlists":
            body = json.loads(request.content)
            assert body["public"] is False
            assert body["name"] == "Venti — Solace — Jul 6"
            assert body["description"] == user_client.PLAYLIST_DESCRIPTION
            return httpx.Response(201, json={
                "id": "pl-1",
                "external_urls": {"spotify": "https://open.spotify.com/playlist/pl-1"},
            })
        if path == "/v1/playlists/pl-1/items":
            body = json.loads(request.content)
            assert body["uris"] == ["spotify:track:a", "spotify:track:b"]
            return httpx.Response(201, json={"snapshot_id": "snap"})
        raise AssertionError(f"unexpected request: {path}")

    seen = transport(handler)
    token = TokenSet(
        access_token="acc", refresh_token="ref",
        expires_at=int(time.time()) + 3600,
    )
    url = user_client.create_playlist(
        token,
        name="Venti — Solace — Jul 6",
        track_uris=["spotify:track:a", "spotify:track:b"],
        description=user_client.PLAYLIST_DESCRIPTION,
    )
    assert url == "https://open.spotify.com/playlist/pl-1"
    assert len(seen) == 2  # create + add-tracks; no /me lookup needed
    assert all(r.headers["Authorization"] == "Bearer acc" for r in seen)
    # user-API calls never carry the client secret
    assert all("test-client-secret" not in str(r.headers) for r in seen)


def test_create_playlist_body_is_exactly_name_public_false_description(transport):
    # T5.6 (a): "public": False is always sent explicitly — never Spotify's
    # default (public, which 403s under playlist-modify-private) — and the
    # body carries nothing else.
    captured = {}

    def handler(request):
        path = request.url.path
        if path == "/v1/me/playlists":
            captured.update(json.loads(request.content))
            return httpx.Response(201, json={
                "id": "pl", "external_urls": {"spotify": "u"},
            })
        return httpx.Response(201, json={})

    transport(handler)
    token = TokenSet(
        access_token="acc", refresh_token="ref",
        expires_at=int(time.time()) + 3600,
    )
    user_client.create_playlist(
        token, "Venti — Discharge — Jul 7", ["spotify:track:a"],
        user_client.PLAYLIST_DESCRIPTION,
    )
    assert captured == {
        "name": "Venti — Discharge — Jul 7",
        "public": False,
        "description": user_client.PLAYLIST_DESCRIPTION,
    }


def test_create_playlist_uses_no_deprecated_endpoints(transport):
    # Spotify's Feb 2026 migration (403 for Development Mode apps since
    # 2026-03-09): POST /users/{user_id}/playlists → POST /me/playlists,
    # and /playlists/{id}/tracks → /playlists/{id}/items. Creation must
    # touch neither deprecated spelling, and needs no /me lookup at all.
    def handler(request):
        path = request.url.path
        if path.startswith("/v1/users/") or path == "/v1/me" or path.endswith("/tracks"):
            raise AssertionError(
                f"deprecated endpoint used (Feb 2026 migration): {path}"
            )
        if path == "/v1/me/playlists":
            return httpx.Response(201, json={
                "id": "pl", "external_urls": {"spotify": "u"},
            })
        if path == "/v1/playlists/pl/items":
            return httpx.Response(201, json={"snapshot_id": "snap"})
        raise AssertionError(f"unexpected request: {path}")

    seen = transport(handler)
    token = TokenSet(
        access_token="acc", refresh_token="ref",
        expires_at=int(time.time()) + 3600,
    )
    user_client.create_playlist(token, "n", ["spotify:track:a"], "d")
    assert [r.url.path for r in seen] == ["/v1/me/playlists", "/v1/playlists/pl/items"]


def test_exchange_code_logs_granted_scope_not_tokens(transport, caplog):
    import logging

    transport(_token_response({
        "access_token": "acc-secret", "refresh_token": "ref-secret",
        "expires_in": 3600, "scope": "playlist-modify-private",
    }))
    with caplog.at_level(logging.INFO):
        user_client.exchange_code("the-code")

    line = next(r for r in caplog.records if r.getMessage() == "token_granted")
    assert line.name == "venti.web.playlist"
    assert line.scope == "playlist-modify-private"
    assert "acc-secret" not in str(line.__dict__)
    assert "ref-secret" not in str(line.__dict__)


def test_fetch_identity_returns_me_json(transport):
    def handler(request):
        assert request.url.path == "/v1/me"
        assert request.headers["Authorization"] == "Bearer acc"
        return httpx.Response(200, json={"id": "user-9", "display_name": "T"})

    transport(handler)
    token = TokenSet(
        access_token="acc", refresh_token="ref",
        expires_at=int(time.time()) + 3600,
    )
    identity = user_client.fetch_identity(token)
    assert identity["id"] == "user-9"
    assert identity["display_name"] == "T"


def test_playlist_name_convention():
    assert user_client.playlist_name("Solace", on=date(2026, 7, 6)) == "Venti — Solace — Jul 6"
    assert user_client.playlist_name("Discharge", on=date(2026, 12, 25)) == "Venti — Discharge — Dec 25"


# --- token persistence invariant ---------------------------------------

def test_no_token_persistence_code_paths():
    """Grep-level paranoia per the build spec: tokens exist only as
    return values, so the module must contain no file-write machinery."""
    src = inspect.getsource(user_client)
    for forbidden in (
        "open(", "write(", "Path(", "pickle", "shelve",
        "makedirs", "tempfile", "NamedTemporary", "cache_path",
    ):
        assert forbidden not in src, f"file-write machinery found: {forbidden}"
