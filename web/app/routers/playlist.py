"""
POST /api/playlist — save the four tracks as a private playlist on the
connected Spotify account. Requires a Spotify session (tokens in the
signed cookie); refreshes the access token when expired.
"""
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from web.app.rate_limit import limiter
from web.app.routers.auth import (
    clear_token_in_session,
    store_token_in_session,
    token_from_session,
)
from web.app.spotify import user_client

log = logging.getLogger("venti.web.playlist")

router = APIRouter()

NOT_CONNECTED_MESSAGE = "connect spotify first — then saving works."
RECONNECT_MESSAGE = "your spotify connection expired — reconnect and try again."
SAVE_FAILED_MESSAGE = "couldn't save the playlist — try again in a moment."

TrackUri = Annotated[str, StringConstraints(pattern=r"^spotify:track:[0-9A-Za-z]+$")]


class PlaylistRequest(BaseModel):
    track_uris: list[TrackUri] = Field(min_length=1, max_length=10)
    strategy_label: str = Field(min_length=1, max_length=40)


@router.post("/api/playlist")
@limiter.limit("10/hour")
def playlist(request: Request, body: PlaylistRequest) -> dict:
    token = token_from_session(request.session)
    if token is None:
        raise HTTPException(status_code=401, detail=NOT_CONNECTED_MESSAGE)

    try:
        if token.is_expired():
            token = user_client.refresh(token.refresh_token)
            store_token_in_session(request.session, token)
        playlist_url = user_client.create_playlist(
            token,
            user_client.playlist_name(body.strategy_label.strip()),
            body.track_uris,
            user_client.PLAYLIST_DESCRIPTION,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        log.error(
            "playlist_failed",
            extra={"error_type": type(exc).__name__, "spotify_status": status},
        )
        if status in (400, 401, 403):
            # invalid_grant on refresh, or a revoked/insufficient token —
            # the stored session is no good, make the user reconnect.
            clear_token_in_session(request.session)
            raise HTTPException(status_code=401, detail=RECONNECT_MESSAGE) from None
        raise HTTPException(status_code=502, detail=SAVE_FAILED_MESSAGE) from None
    except Exception as exc:
        log.error("playlist_failed", extra={"error_type": type(exc).__name__})
        raise HTTPException(status_code=502, detail=SAVE_FAILED_MESSAGE) from None

    log.info("playlist_created", extra={"n_tracks": len(body.track_uris)})
    return {"playlist_url": playlist_url}
