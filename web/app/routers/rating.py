"""
POST /api/rating — one structured log line + one event row per rating.

The SQLite event store (T5.10, web.app.store) is the durable record —
the beta's efficacy metric lives or dies on these rows. The log line
remains for live ops visibility. Strategy is validated against the MMR
enum so the analytics stream can't be polluted with arbitrary strings;
no free text exists anywhere in this path.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from venti_core.models import MMRStrategy

from web.app import store

log = logging.getLogger("venti.web.rating")

router = APIRouter()


class RatingRequest(BaseModel):
    rating: int = Field(ge=-2, le=2)
    strategy: MMRStrategy


@router.post("/api/rating")
def rating(body: RatingRequest) -> dict:
    # JsonLogFormatter adds ts; the line comes out as
    # {"ts": ..., "event": "rating", "strategy": ..., "rating": ...}.
    log.info(
        "rating",
        extra={"strategy": body.strategy.value, "rating": body.rating},
    )
    store.record_event("rating", strategy=body.strategy.value, rating=body.rating)
    return {"ok": True}
