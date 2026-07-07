"""
POST /api/vent — the core loop, no auth: text in, strategy + reasoning +
trajectory + tracks out. Crisis-triaged vents (T5.1) get {"crisis": true}
back instead — no playlist, the frontend shows resources.

Privacy invariant (build rule 5): the vent text exists only in this
request's memory. The success log line carries strategy, n_tracks and
latency_ms; the failure line carries the exception class name; the crisis
line carries the event name alone. Never the text, never the IP beyond
what the rate limiter keys on.
"""
import logging
import time
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from venti_core.llm.base import LLMBackend, get_backend
from venti_core.llm.vent_pipeline import CrisisIndicated, run_vent
from venti_core.models import MMRStrategy

from web.app import store
from web.app.rate_limit import limiter
from web.app.spotify.app_client import AppSpotifyClient

log = logging.getLogger("venti.web.vent")

router = APIRouter()

MAX_VENT_CHARS = 1000

TOO_LONG_MESSAGE = (
    "that's a lot to carry — trim it to under 1,000 characters "
    "and let the rest out next round."
)
SERVER_ERROR_MESSAGE = (
    "something broke on our end. your words weren't stored — "
    "try again in a moment."
)


def strategy_label(strategy: MMRStrategy) -> str:
    """Human-facing label, e.g. mental_work → "Mental Work". Also what the
    frontend passes back to /api/playlist for the playlist name."""
    return strategy.value.replace("_", " ").title()


class VentRequest(BaseModel):
    text: str


@lru_cache
def get_llm_backend() -> LLMBackend:
    return get_backend()


@lru_cache
def get_app_client() -> AppSpotifyClient:
    return AppSpotifyClient()


@router.post("/api/vent")
@limiter.limit("5/hour;20/day")
def vent(request: Request, body: VentRequest) -> dict:
    if len(body.text) > MAX_VENT_CHARS:
        raise HTTPException(status_code=413, detail=TOO_LONG_MESSAGE)
    text = body.text.strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="say anything — even a few words help.",
        )

    started = time.perf_counter()
    try:
        result = run_vent(text, get_llm_backend())
        if isinstance(result, CrisisIndicated):
            # T5.1: event name + the record's own timestamp, nothing else —
            # no strategy, no latency, and (as everywhere here) never the text.
            log.info("crisis_declined")
            store.record_event("crisis_declined")
            return {"crisis": True}
        tracks = get_app_client().find_tracks_for_queries(result.queries)
    except Exception as exc:
        # Class name only: LLM error messages can quote model output,
        # and nothing derived from the vent may reach a log line.
        log.error("vent_failed", extra={"error_type": type(exc).__name__})
        raise HTTPException(status_code=502, detail=SERVER_ERROR_MESSAGE) from None

    latency_ms = round((time.perf_counter() - started) * 1000)
    log.info(
        "vent",
        extra={
            "strategy": result.strategy.value,
            "n_tracks": len(tracks),
            "latency_ms": latency_ms,
        },
    )
    store.record_event(
        "vent",
        strategy=result.strategy.value,
        n_tracks=len(tracks),
        latency_ms=latency_ms,
    )
    return {
        "strategy": result.strategy.value,
        "strategy_label": strategy_label(result.strategy),
        "reasoning": result.reasoning,
        "trajectory": [
            {"valence": w.valence, "arousal": w.arousal} for w in result.trajectory
        ],
        "tracks": [t.model_dump() for t in tracks],
    }
