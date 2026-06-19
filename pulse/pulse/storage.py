"""
Session storage. Just JSON files in ./data — simple, inspectable, easy to migrate
to SQLite or Postgres later when we have real volume.

Each session is one file: data/sessions/YYYYMMDD_HHMMSS.json
This makes it trivial to grep, diff, manually edit, or import into pandas
for analysis when we want to study what's working.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import VentSession


DEFAULT_DATA_DIR = Path("data/sessions")


class SessionStore:
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: VentSession) -> Path:
        ts = session.timestamp.replace(":", "").replace("-", "").replace(" ", "_").split(".")[0]
        path = self.data_dir / f"{ts}.json"
        path.write_text(session.to_json())
        return path

    def load(self, path: Path) -> VentSession:
        return VentSession.from_json(Path(path).read_text())

    def all_sessions(self) -> list[VentSession]:
        return [self.load(p) for p in sorted(self.data_dir.glob("*.json"))]

    def latest(self) -> Optional[VentSession]:
        files = sorted(self.data_dir.glob("*.json"))
        return self.load(files[-1]) if files else None
