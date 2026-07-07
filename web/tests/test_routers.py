"""
T3.2 endpoint tests: char cap, rate limit trigger, OAuth state mismatch
rejection, token refresh, rating log line — and the privacy invariants:
no handler ever logs request body text (runtime check on success AND
error paths), and no code in web/app writes to files/DB or passes text
to a logger (grep-level static check).
"""
import logging
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from venti_core.llm.vent_pipeline import VentPipelineError, VentResult
from venti_core.models import EmotionState, MMRStrategy

# Distinctive vent text: if it shows up in any log line, we leaked.
MARKER = "XYZZY-my-cat-died-and-im-not-okay-XYZZY"

VALID_URI = "spotify:track:4uLU6hMCjMI75M1A2tKUQC"


@pytest.fixture(autouse=True)
def _reset_rate_limits(main_module):
    from web.app.rate_limit import limiter

    limiter.reset()


def _fake_tracks(n):
    from web.app.spotify.app_client import TrackInfo

    return [
        TrackInfo(
            id=f"track{i}",
            uri=f"spotify:track:{'a' * 21}{i}",
            name=f"Song {i}",
            artist=f"Artist {i}",
            album_art_url=None,
            preview_url=None,
            external_url=f"https://open.spotify.com/track/track{i}",
        )
        for i in range(n)
    ]


@pytest.fixture()
def vent_mocks(main_module, monkeypatch):
    """Stub the LLM pipeline and Spotify search so /api/vent runs offline."""
    from web.app.routers import vent as vent_router

    current = EmotionState(valence=-0.7, arousal=0.6)
    target = EmotionState(valence=0.4, arousal=0.0)
    result = VentResult(
        current_emotion=current,
        target_emotion=target,
        strategy=MMRStrategy.DIVERSION,
        reasoning="You're wound tight; a clean change of scenery helps.",
        trajectory=[current, EmotionState(-0.3, 0.4), EmotionState(0.1, 0.2), target],
        queries=["q1", "q2", "q3", "q4"],
    )

    class FakeAppClient:
        def find_tracks_for_queries(self, queries):
            return _fake_tracks(len(queries))

    monkeypatch.setattr(vent_router, "get_llm_backend", lambda: None)
    monkeypatch.setattr(vent_router, "get_app_client", lambda: FakeAppClient())
    monkeypatch.setattr(vent_router, "run_vent", lambda text, backend: result)
    return result


def _token(expires_at):
    from web.app.spotify.user_client import TokenSet

    return TokenSet(
        access_token="access-1", refresh_token="refresh-1", expires_at=expires_at
    )


def _connect_spotify(client, monkeypatch, token, callback_path="/api/auth/callback"):
    """Run the real login/callback flow with a stubbed code exchange, so
    the client's session cookie ends up holding `token`."""
    from web.app.spotify import user_client

    login = client.get("/api/auth/login", follow_redirects=False)
    assert login.status_code == 302
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    monkeypatch.setattr(user_client, "exchange_code", lambda code: token)
    callback = client.get(
        f"{callback_path}?code=fake-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert callback.headers["location"] == "/?connected=1"
    return state


# --- POST /api/vent ----------------------------------------------------------


def test_vent_returns_full_payload(client, vent_mocks):
    response = client.post("/api/vent", json={"text": "ugh, everything today"})
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "diversion"
    assert data["strategy_label"] == "Diversion"
    assert data["reasoning"] == vent_mocks.reasoning
    assert len(data["trajectory"]) == 4
    assert all(set(w) == {"valence", "arousal"} for w in data["trajectory"])
    assert len(data["tracks"]) == 4
    assert data["tracks"][0]["name"] == "Song 0"


def test_vent_char_cap(client, vent_mocks):
    over = client.post("/api/vent", json={"text": "a" * 1001})
    assert over.status_code == 413
    assert "1,000" in over.json()["detail"]  # friendly, not a pydantic dump

    at_cap = client.post("/api/vent", json={"text": "a" * 1000})
    assert at_cap.status_code == 200


def test_vent_empty_text_rejected(client, vent_mocks):
    assert client.post("/api/vent", json={"text": "   "}).status_code == 400


def test_vent_rate_limit_5_per_hour(client, vent_mocks):
    for _ in range(5):
        assert client.post("/api/vent", json={"text": "hi"}).status_code == 200
    assert client.post("/api/vent", json={"text": "hi"}).status_code == 429


def test_ratelimit_bypass_honored_when_env_set(client, vent_mocks, monkeypatch):
    # T5.5: matching X-Debug-Token skips the limit entirely (and consumes
    # nothing); a wrong token is just a normal, limited request.
    monkeypatch.setenv("RATELIMIT_BYPASS_TOKEN", "open-sesame")

    for _ in range(8):  # well past the 5/hour limit
        response = client.post(
            "/api/vent", json={"text": "hi"},
            headers={"X-Debug-Token": "open-sesame"},
        )
        assert response.status_code == 200

    # Bypassed requests consumed nothing: five clean ones still fit...
    for _ in range(5):
        assert client.post("/api/vent", json={"text": "hi"}).status_code == 200
    # ...and a WRONG token does not bypass the now-tripped limit.
    blocked = client.post(
        "/api/vent", json={"text": "hi"}, headers={"X-Debug-Token": "wrong"},
    )
    assert blocked.status_code == 429


def test_ratelimit_bypass_noop_when_env_unset(client, vent_mocks, monkeypatch):
    monkeypatch.delenv("RATELIMIT_BYPASS_TOKEN", raising=False)
    headers = {"X-Debug-Token": "open-sesame"}
    for _ in range(5):
        assert client.post("/api/vent", json={"text": "hi"}, headers=headers).status_code == 200
    assert client.post("/api/vent", json={"text": "hi"}, headers=headers).status_code == 429


def test_ratelimit_trip_logs_anonymous_event_only(client, vent_mocks, caplog):
    # T5.5: slowapi's own warning embeds the rate-limit key (the client IP —
    # "testclient" under TestClient) and must not surface; our replacement
    # event carries the path and limit, nothing identifying.
    with caplog.at_level(logging.DEBUG):
        for _ in range(5):
            assert client.post("/api/vent", json={"text": "hi"}).status_code == 200
        blocked = client.post("/api/vent", json={"text": "hi"})

    assert blocked.status_code == 429
    assert not [r for r in caplog.records if r.name == "slowapi"]
    for record in caplog.records:
        assert "testclient" not in str(record.__dict__)  # the would-be leaked key

    event = next(r for r in caplog.records if r.getMessage() == "ratelimit_exceeded")
    assert event.path == "/api/vent"
    assert event.limit  # e.g. "5 per 1 hour"
    assert not hasattr(event, "key")


def test_vent_success_never_logs_text(client, vent_mocks, caplog):
    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/vent", json={"text": MARKER})
    assert response.status_code == 200
    for record in caplog.records:
        assert MARKER not in str(record.__dict__)
    # The success line carries exactly what the spec allows.
    vent_line = next(r for r in caplog.records if r.getMessage() == "vent")
    assert vent_line.strategy == "diversion"
    assert vent_line.n_tracks == 4
    assert isinstance(vent_line.latency_ms, int)


def test_vent_crisis_declines_playlist_and_logs_only_the_event(
    client, main_module, monkeypatch, caplog
):
    # T5.1: crisis triage → distinct response, no Spotify contact, and a log
    # line carrying nothing but the event name (the record brings its own ts).
    from venti_core.llm.vent_pipeline import CrisisIndicated
    from web.app.routers import vent as vent_router

    class MustNotSearch:
        def find_tracks_for_queries(self, queries):
            raise AssertionError("crisis path must never reach Spotify")

    monkeypatch.setattr(vent_router, "get_llm_backend", lambda: None)
    monkeypatch.setattr(vent_router, "get_app_client", lambda: MustNotSearch())
    monkeypatch.setattr(vent_router, "run_vent", lambda text, backend: CrisisIndicated())

    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/vent", json={"text": MARKER})

    assert response.status_code == 200
    assert response.json() == {"crisis": True}

    crisis_line = next(r for r in caplog.records if r.getMessage() == "crisis_declined")
    # Only the event: no strategy, no latency, and never the text.
    assert not hasattr(crisis_line, "strategy")
    assert not hasattr(crisis_line, "latency_ms")
    assert not any(r.getMessage() == "vent" for r in caplog.records)
    for record in caplog.records:
        assert MARKER not in str(record.__dict__)


def test_vent_error_path_never_leaks_text(client, main_module, monkeypatch, caplog):
    from web.app.routers import vent as vent_router

    def exploding_run_vent(text, backend):
        # Worst case: the pipeline error message quotes the vent text
        # (LLMError messages can embed model output echoing it).
        raise VentPipelineError(f"could not parse: {MARKER}")

    monkeypatch.setattr(vent_router, "get_llm_backend", lambda: None)
    monkeypatch.setattr(vent_router, "run_vent", exploding_run_vent)

    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/vent", json={"text": MARKER})
    assert response.status_code == 502
    assert MARKER not in response.text
    assert response.json()["detail"] == vent_router.SERVER_ERROR_MESSAGE
    for record in caplog.records:
        assert MARKER not in str(record.__dict__)
    error_line = next(r for r in caplog.records if r.getMessage() == "vent_failed")
    assert error_line.error_type == "VentPipelineError"


# --- GET /api/auth/login and /api/auth/callback ------------------------------


def test_login_redirects_to_spotify(client):
    response = client.get("/api/auth/login", follow_redirects=False)
    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert location.netloc == "accounts.spotify.com"
    query = parse_qs(location.query)
    assert query["client_id"] == ["test-client-id"]
    assert query["scope"] == ["playlist-modify-private"]
    assert query["state"][0]  # non-empty, from user_client.generate_state()


def test_login_sets_secure_session_cookie(client):
    response = client.get("/api/auth/login", follow_redirects=False)
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=lax" in set_cookie


def test_callback_state_mismatch_rejected(client):
    client.get("/api/auth/login", follow_redirects=False)
    response = client.get(
        "/api/auth/callback?code=fake-code&state=not-the-state",
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_callback_without_login_rejected(client):
    response = client.get(
        "/api/auth/callback?code=fake-code&state=anything",
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_callback_success_redirects_connected(client, monkeypatch):
    _connect_spotify(client, monkeypatch, _token(int(time.time()) + 3600))


def test_callback_state_is_single_use(client, monkeypatch):
    state = _connect_spotify(client, monkeypatch, _token(int(time.time()) + 3600))
    replay = client.get(
        f"/api/auth/callback?code=fake-code&state={state}",
        follow_redirects=False,
    )
    assert replay.status_code == 403


def test_callback_alias_is_the_same_handler(main_module):
    # T4.4: /callback (grandfathered local-dev redirect URI) must be the
    # SAME function object as /api/auth/callback — not a copy. Asserted
    # on auth.router (stable across FastAPI's include_router internals);
    # the alias flow tests below prove the app actually serves both.
    from web.app.routers import auth

    endpoints = {
        route.path: route.endpoint
        for route in auth.router.routes
        if route.path in ("/callback", "/api/auth/callback")
    }
    assert set(endpoints) == {"/callback", "/api/auth/callback"}
    assert endpoints["/callback"] is endpoints["/api/auth/callback"]


def test_callback_alias_full_flow(client, monkeypatch):
    _connect_spotify(
        client, monkeypatch, _token(int(time.time()) + 3600),
        callback_path="/callback",
    )


def test_callback_alias_rejects_state_mismatch(client):
    client.get("/api/auth/login", follow_redirects=False)
    response = client.get(
        "/callback?code=fake-code&state=not-the-state",
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_callback_user_declined(client):
    login = client.get("/api/auth/login", follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    response = client.get(
        f"/api/auth/callback?error=access_denied&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/?connected=0"


# --- POST /api/playlist -------------------------------------------------------


def test_playlist_requires_spotify_session(client):
    response = client.post(
        "/api/playlist",
        json={"track_uris": [VALID_URI], "strategy_label": "Diversion"},
    )
    assert response.status_code == 401


def test_playlist_creates_and_returns_url(client, monkeypatch):
    from web.app.spotify import user_client

    _connect_spotify(client, monkeypatch, _token(int(time.time()) + 3600))

    created = {}

    def fake_create_playlist(token, name, track_uris, description):
        created.update(name=name, track_uris=track_uris, description=description)
        return "https://open.spotify.com/playlist/abc123"

    monkeypatch.setattr(user_client, "create_playlist", fake_create_playlist)
    response = client.post(
        "/api/playlist",
        json={"track_uris": [VALID_URI], "strategy_label": "Diversion"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "playlist_url": "https://open.spotify.com/playlist/abc123"
    }
    assert created["name"].startswith("Venti — Diversion — ")
    assert created["track_uris"] == [VALID_URI]


def test_playlist_refreshes_expired_token(client, monkeypatch):
    from web.app.spotify import user_client
    from web.app.spotify.user_client import TokenSet

    _connect_spotify(client, monkeypatch, _token(expires_at=100))  # long expired

    fresh = TokenSet(
        access_token="refreshed-access",
        refresh_token="refresh-1",
        expires_at=int(time.time()) + 3600,
    )
    used = {}
    monkeypatch.setattr(user_client, "refresh", lambda refresh_token: fresh)
    monkeypatch.setattr(
        user_client,
        "create_playlist",
        lambda token, name, track_uris, description: used.update(token=token)
        or "https://open.spotify.com/playlist/xyz",
    )
    response = client.post(
        "/api/playlist",
        json={"track_uris": [VALID_URI], "strategy_label": "Solace"},
    )
    assert response.status_code == 200
    assert used["token"].access_token == "refreshed-access"


def _spotify_error(status, body=None):
    """An httpx.HTTPStatusError as raise_for_status would produce it."""
    api_request = httpx.Request("POST", "https://api.spotify.com/v1/me")
    response = httpx.Response(status, json=body or {}, request=api_request)
    return httpx.HTTPStatusError("boom", request=api_request, response=response)


def test_playlist_spotify_403_passes_through_and_logs_body(
    client, monkeypatch, caplog
):
    # T5.5: Spotify's app-level 403 (dev-mode allowlist, scopes) is NOT a
    # session problem — it returns 403 with the full Spotify error body
    # logged, and the session survives (re-auth can't fix an allowlist miss).
    from web.app.routers import playlist as playlist_router
    from web.app.spotify import user_client

    _connect_spotify(client, monkeypatch, _token(int(time.time()) + 3600))

    spotify_body = {"error": {"status": 403, "message": "User not registered in the Developer Dashboard"}}

    def raise_403(token, name, track_uris, description):
        raise _spotify_error(403, spotify_body)

    monkeypatch.setattr(user_client, "create_playlist", raise_403)
    payload = {"track_uris": [VALID_URI], "strategy_label": "Diversion"}

    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/playlist", json=payload)

    assert response.status_code == 403
    assert response.json()["detail"] == playlist_router.FORBIDDEN_MESSAGE

    line = next(r for r in caplog.records if r.getMessage() == "playlist_spotify_403")
    assert line.name == "venti.web.playlist"
    assert line.spotify_status == 403
    assert "User not registered in the Developer Dashboard" in line.spotify_error

    # Session not cleared: the retry is another 403, not 401 not-connected.
    retry = client.post("/api/playlist", json=payload)
    assert retry.status_code == 403


def test_playlist_refresh_failure_is_401_and_clears_session(client, monkeypatch):
    # T5.5: 401 is reserved for session problems — a failed token refresh
    # (Spotify's invalid_grant is a 400) sends the user back through OAuth.
    from web.app.routers import playlist as playlist_router
    from web.app.spotify import user_client

    _connect_spotify(client, monkeypatch, _token(expires_at=100))  # expired

    def failing_refresh(refresh_token):
        raise _spotify_error(400, {"error": "invalid_grant"})

    monkeypatch.setattr(user_client, "refresh", failing_refresh)
    payload = {"track_uris": [VALID_URI], "strategy_label": "Solace"}

    response = client.post("/api/playlist", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == playlist_router.RECONNECT_MESSAGE

    # Session cleared: the retry fails as not-connected, before any refresh.
    retry = client.post("/api/playlist", json=payload)
    assert retry.status_code == 401
    assert retry.json()["detail"] == playlist_router.NOT_CONNECTED_MESSAGE


def test_playlist_rejects_malformed_uris(client):
    response = client.post(
        "/api/playlist",
        json={
            "track_uris": ["https://evil.example/x"],
            "strategy_label": "Diversion",
        },
    )
    assert response.status_code == 422


# --- POST /api/rating ---------------------------------------------------------


def test_rating_emits_structured_log_line(client, caplog):
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/rating", json={"rating": 2, "strategy": "diversion"}
        )
    assert response.status_code == 200
    line = next(r for r in caplog.records if r.getMessage() == "rating")
    assert line.strategy == "diversion"
    assert line.rating == 2


def test_rating_validates_bounds_and_strategy(client):
    assert (
        client.post("/api/rating", json={"rating": 3, "strategy": "diversion"})
        .status_code
        == 422
    )
    assert (
        client.post("/api/rating", json={"rating": -3, "strategy": "diversion"})
        .status_code
        == 422
    )
    assert (
        client.post("/api/rating", json={"rating": 1, "strategy": "yolo"})
        .status_code
        == 422
    )


# --- Privacy invariant (grep-level, per build spec Phase 3) -------------------


def test_privacy_no_file_writes_and_no_text_in_logger_calls():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    file_or_db_writes = [
        r"\bopen\(",
        r"\.write_text\(",
        r"\.write_bytes\(",
        r"\bsqlite",
        r"\bpickle\b",
        r"\bshelve\b",
        r"json\.dump\(",
    ]
    # A logger call whose arguments mention anything named *text*.
    logger_call_with_text = (
        r"log\.(?:debug|info|warning|error|critical|exception)\([^)]*text"
    )
    checked = 0
    for path in sorted(app_dir.rglob("*.py")):
        source = path.read_text()
        for pattern in file_or_db_writes:
            assert not re.search(pattern, source), f"{pattern!r} found in {path}"
        assert not re.search(logger_call_with_text, source), (
            f"logger call referencing text in {path}"
        )
        checked += 1
    assert checked >= 8  # main, config, rate_limit, 2 spotify, 4 routers-ish
