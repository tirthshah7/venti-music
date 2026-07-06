"""
Core data models for Pulse.

Grounded in two psychology frameworks:
- Russell's circumplex model (valence-arousal 2D space)
- Saarikallio's MMR (Music in Mood Regulation) seven strategies
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import json
import math


class MMRStrategy(Enum):
    """
    The seven mood-regulation strategies from Saarikallio (2008).
    Each implies a different trajectory shape, not just different songs.
    """
    ENTERTAINMENT = "entertainment"      # sustain/enhance an existing positive mood
    REVIVAL = "revival"                  # relax, recover, restore energy
    STRONG_SENSATION = "strong_sensation"  # seek intense emotional experience
    DIVERSION = "diversion"              # forget the negative — orthogonal escape
    DISCHARGE = "discharge"              # let negative emotion OUT (cathartic)
    MENTAL_WORK = "mental_work"          # contemplate, process, reappraise
    SOLACE = "solace"                    # comfort, feel understood, not alone


@dataclass
class EmotionState:
    """
    A point in valence-arousal space.

    valence:  -1.0 (very negative) to +1.0 (very positive)
    arousal:  -1.0 (very calm)     to +1.0 (very intense)

    Examples:
        frustrated debugging: valence=-0.7, arousal=+0.6
        sad/down:             valence=-0.6, arousal=-0.4
        focused calm:         valence=+0.3, arousal=-0.1
        excited shipping:     valence=+0.8, arousal=+0.7
    """
    valence: float
    arousal: float

    def __post_init__(self):
        # Clamp to [-1, 1] in case the LLM goes out of range
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(-1.0, min(1.0, self.arousal))

    def distance(self, other: "EmotionState") -> float:
        """Euclidean distance in VA space — used to match songs to waypoints."""
        return math.sqrt(
            (self.valence - other.valence) ** 2
            + (self.arousal - other.arousal) ** 2
        )

    def to_spotify_features(self) -> dict:
        """
        Map our [-1, 1] VA space to Spotify's [0, 1] audio features.
        Spotify 'valence' = our valence rescaled.
        Spotify 'energy'  = our arousal rescaled (energy is the closest proxy).
        """
        return {
            "target_valence": (self.valence + 1) / 2,
            "target_energy": (self.arousal + 1) / 2,
        }


@dataclass
class VentSession:
    """
    A single end-to-end session: trigger → inference → trajectory → playback → outcome.
    Everything stored is training data for the personal model.
    """
    timestamp: str
    trigger_type: str          # "manual" or "auto"
    vent_text: str
    context: str               # what the user is working on, recent topics
    current_emotion: EmotionState
    target_emotion: EmotionState
    strategy: MMRStrategy
    reasoning: str             # LLM's explanation — invaluable for debugging
    trajectory: list           # list of EmotionState waypoints
    track_ids: list = field(default_factory=list)
    skips: list = field(default_factory=list)  # track_ids that were skipped
    completions: list = field(default_factory=list)
    post_session_rating: Optional[int] = None  # -2 to +2, did mood shift?
    notes: Optional[str] = None

    def to_json(self) -> str:
        d = asdict(self)
        d["strategy"] = self.strategy.value
        return json.dumps(d, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "VentSession":
        d = json.loads(s)
        d["current_emotion"] = EmotionState(**d["current_emotion"])
        d["target_emotion"] = EmotionState(**d["target_emotion"])
        d["strategy"] = MMRStrategy(d["strategy"])
        d["trajectory"] = [EmotionState(**w) for w in d["trajectory"]]
        return cls(**d)
