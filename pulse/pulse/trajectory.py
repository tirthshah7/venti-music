"""
Trajectory generation: given (current, target, strategy), build a sequence
of VA waypoints that the song selector will use to pick a playlist.

This is where the iso principle and MMR strategies diverge. The same start
and target can produce VERY different trajectories depending on strategy:

- DISCHARGE: stay in or amplify current valence/arousal first, THEN shift.
  Don't sanitize the anger; let it peak before easing.

- ISO (default for solace, revival, mental_work): match current state, then
  smoothly interpolate to target. Classic music therapy progression.

- DIVERSION: skip iso entirely. Jump orthogonally — different emotional
  territory, often unexpected. Breaks rumination by surprise.

- ENTERTAINMENT: stay near current (already positive), small gentle moves.

- STRONG_SENSATION: push toward emotional extremes, not toward neutral.
"""
from .models import EmotionState, MMRStrategy


def generate_trajectory(
    current: EmotionState,
    target: EmotionState,
    strategy: MMRStrategy,
    n_waypoints: int = 4,
) -> list[EmotionState]:
    """
    Returns n_waypoints EmotionStates representing the playlist arc.
    """
    if strategy == MMRStrategy.DISCHARGE:
        return _discharge_trajectory(current, target, n_waypoints)
    elif strategy == MMRStrategy.DIVERSION:
        return _diversion_trajectory(current, target, n_waypoints)
    elif strategy == MMRStrategy.ENTERTAINMENT:
        return _entertainment_trajectory(current, target, n_waypoints)
    elif strategy == MMRStrategy.STRONG_SENSATION:
        return _strong_sensation_trajectory(current, target, n_waypoints)
    else:
        # SOLACE, REVIVAL, MENTAL_WORK all use iso principle
        return _iso_trajectory(current, target, n_waypoints)


def _iso_trajectory(
    current: EmotionState, target: EmotionState, n: int
) -> list[EmotionState]:
    """
    Classic iso principle: match current, smooth interpolation to target.
    Slightly weighted toward staying near current early — bigger jumps later.
    """
    waypoints = []
    for i in range(n):
        # Eased interpolation: slow start, faster end (cubic ease-in)
        t = (i / (n - 1)) ** 1.5 if n > 1 else 1.0
        waypoints.append(
            EmotionState(
                valence=current.valence + (target.valence - current.valence) * t,
                arousal=current.arousal + (target.arousal - current.arousal) * t,
            )
        )
    return waypoints


def _discharge_trajectory(
    current: EmotionState, target: EmotionState, n: int
) -> list[EmotionState]:
    """
    Discharge: AMPLIFY current state for first 1-2 songs (peak the catharsis),
    then ease toward target. Empirically validated for anger/frustration.
    """
    waypoints = []
    # First waypoint: amplify current — push valence and arousal further from neutral
    amp_valence = current.valence * 1.15 if abs(current.valence) > 0.3 else current.valence
    amp_arousal = min(1.0, current.arousal + 0.1) if current.arousal > 0 else current.arousal
    waypoints.append(EmotionState(valence=amp_valence, arousal=amp_arousal))

    # Second waypoint: still match, slight ease
    waypoints.append(EmotionState(
        valence=current.valence,
        arousal=current.arousal * 0.9,
    ))

    # Remaining waypoints: shift toward target
    remaining = n - 2
    for i in range(remaining):
        t = (i + 1) / remaining
        waypoints.append(
            EmotionState(
                valence=current.valence + (target.valence - current.valence) * t,
                arousal=current.arousal + (target.arousal - current.arousal) * t,
            )
        )
    return waypoints[:n]


def _diversion_trajectory(
    current: EmotionState, target: EmotionState, n: int
) -> list[EmotionState]:
    """
    Diversion: skip iso, go orthogonal. Pick a region of VA space far from
    BOTH current and target — surprise the brain into a different emotional
    register. Then settle near target.
    """
    # Orthogonal point: flip the dominant axis of the current state
    if abs(current.valence) > abs(current.arousal):
        # Valence-dominant — divert via arousal
        orthogonal = EmotionState(valence=0.2, arousal=-current.arousal * 0.7)
    else:
        # Arousal-dominant — divert via valence
        orthogonal = EmotionState(valence=-current.valence * 0.7, arousal=0.2)

    waypoints = [orthogonal]
    # Then drift to target
    for i in range(1, n):
        t = i / (n - 1)
        waypoints.append(
            EmotionState(
                valence=orthogonal.valence + (target.valence - orthogonal.valence) * t,
                arousal=orthogonal.arousal + (target.arousal - orthogonal.arousal) * t,
            )
        )
    return waypoints[:n]


def _entertainment_trajectory(
    current: EmotionState, target: EmotionState, n: int
) -> list[EmotionState]:
    """
    Entertainment: small wandering near current positive state. Don't try
    to engineer mood — just sustain it with variety.
    """
    return [
        EmotionState(
            valence=current.valence + 0.05 * (i % 2 - 0.5),
            arousal=current.arousal + 0.05 * ((i + 1) % 2 - 0.5),
        )
        for i in range(n)
    ]


def _strong_sensation_trajectory(
    current: EmotionState, target: EmotionState, n: int
) -> list[EmotionState]:
    """
    Strong sensation: push toward emotional extremes (high arousal,
    extremes of valence). Target is treated as direction not destination.
    """
    # Amplify the target — push past it toward the extreme
    direction_v = 1.0 if target.valence >= 0 else -1.0
    direction_a = 1.0  # strong sensation almost always involves high arousal
    extreme = EmotionState(valence=direction_v * 0.85, arousal=direction_a * 0.85)
    return _iso_trajectory(current, extreme, n)
