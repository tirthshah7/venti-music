"""
GET /api/admin/export — owner-only JSONL dump of the events table (T5.10).

Gated by the ADMIN_EXPORT_TOKEN env var + X-Admin-Token header: 404 when
the env var is unset (the route hides itself), 403 on a wrong token
(constant-time compare). The payload is event metadata only — the store
schema has no text columns — and each line parses directly with
tools/rating_report.py:

    curl -H "X-Admin-Token: $TOKEN" https://<domain>/api/admin/export > events.jsonl
    python tools/rating_report.py events.jsonl
"""
import json
import logging
import os
import secrets

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import PlainTextResponse

from web.app import store

log = logging.getLogger("venti.web.admin")

router = APIRouter()

TOKEN_ENV_VAR = "ADMIN_EXPORT_TOKEN"


@router.get("/api/admin/export", response_class=PlainTextResponse, include_in_schema=False)
def export(x_admin_token: str = Header(default="")) -> str:
    expected = os.environ.get(TOKEN_ENV_VAR, "")
    if not expected:
        # Feature off → indistinguishable from a route that doesn't exist.
        raise HTTPException(status_code=404, detail="Not Found")
    if not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Forbidden")

    events = store.export_events()
    log.info("admin_export", extra={"n_events": len(events)})
    return "\n".join(json.dumps(event) for event in events)
