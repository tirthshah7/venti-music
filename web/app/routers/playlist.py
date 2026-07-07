"""
POST /api/playlist — save the four tracks as a private playlist on the
connected Spotify account. Requires a Spotify session (tokens in the
signed cookie); refreshes the access token when expired.
"""
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints, field_validator

from venti_core.models import MMRStrategy

from web.app.rate_limit import limiter
from web.app.routers.auth import (
    clear_token_in_session,
    store_token_in_session,
    token_from_session,
)
from web.app.routers.vent import strategy_label as label_for_strategy
from web.app.spotify import user_client

log = logging.getLogger("venti.web.playlist")

router = APIRouter()

NOT_CONNECTED_MESSAGE = "connect spotify first — then saving works."
RECONNECT_MESSAGE = "your spotify connection expired — reconnect and try again."
FORBIDDEN_MESSAGE = (
    "spotify wouldn't allow the save — if your invite is new, your account "
    "may not be on the beta allowlist yet."
)
SAVE_FAILED_MESSAGE = "couldn't save the playlist — try again in a moment."

TrackUri = Annotated[str, StringConstraints(pattern=r"^spotify:track:[0-9A-Za-z]+$")]

# The playlist name interpolates strategy_label, and the name goes to
# Spotify — so the label must be one of OUR seven labels, byte-for-byte,
# never client free text (T5.6: no vent-derived text in Spotify artifacts).
VALID_STRATEGY_LABELS = frozenset(label_for_strategy(s) for s in MMRStrategy)


class PlaylistRequest(BaseModel):
    track_uris: list[TrackUri] = Field(min_length=1, max_length=10)
    strategy_label: str = Field(min_length=1, max_length=40)

    @field_validator("strategy_label")
    @classmethod
    def _canonical_label_only(cls, value: str) -> str:
        value = value.strip()
        if value not in VALID_STRATEGY_LABELS:
            raise ValueError("unknown strategy label")
        return value


@router.post("/api/playlist")
@limiter.limit("10/hour")
def playlist(request: Request, body: PlaylistRequest) -> dict:
    token = token_from_session(request.session)
    if token is None:
        raise HTTPException(status_code=401, detail=NOT_CONNECTED_MESSAGE)

    # T5.5 error semantics: 401 is reserved for "your session is no good"
    # (missing above, or the refresh below fails) — the frontend answers it
    # by re-authenticating. Spotify's own 403 passes through as 403: it's an
    # app-level denial that re-authenticating cannot fix.
    try:
        if token.is_expired():
            token = user_client.refresh(token.refresh_token)
            store_token_in_session(request.session, token)
    except httpx.HTTPStatusError as exc:
        log.error(
            "playlist_refresh_failed",
            extra={
                "error_type": type(exc).__name__,
                "spotify_status": exc.response.status_code,
            },
        )
        clear_token_in_session(request.session)
        raise HTTPException(status_code=401, detail=RECONNECT_MESSAGE) from None
    except Exception as exc:
        log.error("playlist_failed", extra={"error_type": type(exc).__name__})
        raise HTTPException(status_code=502, detail=SAVE_FAILED_MESSAGE) from None

    try:
        playlist_url = user_client.create_playlist(
            token,
            user_client.playlist_name(body.strategy_label.strip()),
            body.track_uris,
            user_client.PLAYLIST_DESCRIPTION,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 403:
            # Dev-mode allowlist miss or insufficient scope. Spotify's error
            # body here is app diagnostics (status + error JSON), never user
            # content — log it whole so the allowlist case is diagnosable
            # from Railway logs alone. The session stays: it's valid, just
            # not allowed, and clearing it would misdirect people to OAuth.
            error_body = exc.response.text
            log.error(
                "playlist_spotify_403",
                extra={"spotify_status": status, "spotify_error": error_body},
            )
            raise HTTPException(status_code=403, detail=FORBIDDEN_MESSAGE) from None
        log.error(
            "playlist_failed",
            extra={"error_type": type(exc).__name__, "spotify_status": status},
        )
        if status in (400, 401):
            # Token revoked/invalidated mid-save — the session is no good.
            clear_token_in_session(request.session)
            raise HTTPException(status_code=401, detail=RECONNECT_MESSAGE) from None
        raise HTTPException(status_code=502, detail=SAVE_FAILED_MESSAGE) from None
    except Exception as exc:
        log.error("playlist_failed", extra={"error_type": type(exc).__name__})
        raise HTTPException(status_code=502, detail=SAVE_FAILED_MESSAGE) from None

    log.info("playlist_created", extra={"n_tracks": len(body.track_uris)})
    return {"playlist_url": playlist_url}
