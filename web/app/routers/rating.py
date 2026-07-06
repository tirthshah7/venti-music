"""
POST /api/rating — one structured log line per rating, nothing stored.

This log line IS the beta's entire analytics system; Railway log export
is the query interface. Deliberate: no database until the beta proves we
need one. Strategy is validated against the MMR enum so the analytics
stream can't be polluted with arbitrary strings.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from venti_core.models import MMRStrategy

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
    return {"ok": True}
