"""
GET /api/auth/login and /api/auth/callback — the Spotify Authorization
Code dance around web.app.spotify.user_client.

CSRF state comes from user_client.generate_state() (Phase 2 provides it
precisely so this layer doesn't reinvent it); it is stored in the signed
session cookie and is single-use — the callback pops it before checking.
Tokens live only in the session cookie (main.ALLOWED_SESSION_KEYS), never
on disk.
"""
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from web.app.spotify import user_client
from web.app.spotify.user_client import TokenSet

log = logging.getLogger("venti.web.auth")
# T5.6: playlist-403 diagnostics (token_granted, spotify_identity) are
# grouped under the playlist logger even when emitted from the auth flow,
# so one logger name finds the whole story in Railway logs.
playlist_log = logging.getLogger("venti.web.playlist")

router = APIRouter()

STATE_MISMATCH_MESSAGE = (
    "that login link looks stale — head back and try connecting again."
)
EXCHANGE_FAILED_MESSAGE = "spotify didn't complete the connection — try again."

_TOKEN_SESSION_KEYS = ("spotify_access_token", "spotify_refresh_token", "expires_at")


def store_token_in_session(session: dict, token: TokenSet) -> None:
    session["spotify_access_token"] = token.access_token
    session["spotify_refresh_token"] = token.refresh_token
    session["expires_at"] = token.expires_at


def token_from_session(session: dict) -> Optional[TokenSet]:
    try:
        return TokenSet(
            access_token=session["spotify_access_token"],
            refresh_token=session["spotify_refresh_token"],
            expires_at=session["expires_at"],
        )
    except KeyError:
        return None


def clear_token_in_session(session: dict) -> None:
    for key in _TOKEN_SESSION_KEYS:
        session.pop(key, None)


@router.get("/api/auth/login")
def login(request: Request) -> RedirectResponse:
    state = user_client.generate_state()
    request.session["oauth_state"] = state
    return RedirectResponse(user_client.build_authorize_url(state), status_code=302)


@router.get("/api/auth/callback")
# Local-dev alias (T4.4): the Spotify app still has the CLI-era redirect
# URI http://127.0.0.1:8888/callback registered (see .env.example), so a
# dev pointing SPOTIFY_REDIRECT_URI at it lands on /callback instead of
# /api/auth/callback. Same function object → identical logic by
# construction; hidden from the OpenAPI schema because it isn't API
# surface, just a grandfathered path.
@router.get("/callback", include_in_schema=False)
def callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    expected = request.session.pop("oauth_state", None)
    if not state or not expected or not secrets.compare_digest(expected, state):
        log.warning("oauth_state_mismatch")
        raise HTTPException(status_code=403, detail=STATE_MISMATCH_MESSAGE)

    if error or not code:
        # The person declined on Spotify's consent screen (or Spotify
        # errored). Not a failure of ours — back to the page, unconnected.
        log.info("oauth_declined", extra={"error": error or "no_code"})
        return RedirectResponse("/?connected=0", status_code=302)

    try:
        token = user_client.exchange_code(code)
    except Exception as exc:
        log.error("oauth_exchange_failed", extra={"error_type": type(exc).__name__})
        raise HTTPException(status_code=502, detail=EXCHANGE_FAILED_MESSAGE) from None

    store_token_in_session(request.session, token)

    # T5.6 identity logging: which Spotify account just connected — the
    # fastest way to check a playlist 403 against the dev-mode allowlist.
    # Best-effort by design: a failed /me must never break the connect.
    try:
        identity = user_client.fetch_identity(token)
        playlist_log.info(
            "spotify_identity",
            extra={
                "spotify_user_id": identity.get("id"),
                "display_name": identity.get("display_name"),
            },
        )
    except Exception as exc:
        playlist_log.warning(
            "spotify_identity_failed", extra={"error_type": type(exc).__name__}
        )

    return RedirectResponse("/?connected=1", status_code=302)
