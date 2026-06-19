"""
Smoke tests for trajectory generation. These don't hit any API.
Run with: python -m pytest tests/ -v
Or just: python tests/test_trajectory.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse.models import EmotionState, MMRStrategy
from pulse.trajectory import generate_trajectory


def test_iso_principle_starts_at_current():
    """Iso principle must begin near the user's current state — that's the whole point."""
    current = EmotionState(valence=-0.7, arousal=0.6)  # frustrated
    target = EmotionState(valence=0.3, arousal=0.2)
    traj = generate_trajectory(current, target, MMRStrategy.SOLACE, n_waypoints=4)

    assert len(traj) == 4
    # First waypoint should match current (within rounding)
    assert abs(traj[0].valence - current.valence) < 0.01
    assert abs(traj[0].arousal - current.arousal) < 0.01
    # Last waypoint should match target
    assert abs(traj[-1].valence - target.valence) < 0.01
    print("✅ iso principle starts at current, ends at target")


def test_discharge_amplifies_first():
    """Discharge should peak the catharsis before easing — first waypoint
    should be at least as intense as current, not closer to target."""
    current = EmotionState(valence=-0.7, arousal=0.6)
    target = EmotionState(valence=0.2, arousal=0.0)
    traj = generate_trajectory(current, target, MMRStrategy.DISCHARGE, n_waypoints=4)

    # First waypoint should be more negative or equal, not moved toward positive
    assert traj[0].valence <= current.valence + 0.01
    print("✅ discharge amplifies before easing")


def test_diversion_is_orthogonal():
    """Diversion should NOT start near the current state — that's its whole purpose,
    to break the rumination by surprise."""
    current = EmotionState(valence=-0.6, arousal=0.5)
    target = EmotionState(valence=0.3, arousal=0.0)
    traj = generate_trajectory(current, target, MMRStrategy.DIVERSION, n_waypoints=4)

    # First waypoint should be FAR from current — that's the orthogonal jump
    distance = traj[0].distance(current)
    assert distance > 0.4, f"diversion first waypoint too close to current (d={distance})"
    print("✅ diversion jumps orthogonally")


def test_va_clamping():
    """Out-of-range VA values should be clamped, not crash."""
    s = EmotionState(valence=-2.0, arousal=3.5)
    assert s.valence == -1.0
    assert s.arousal == 1.0
    print("✅ VA values clamped to [-1, 1]")


def test_spotify_feature_mapping():
    """Our [-1, 1] should map to Spotify's [0, 1]."""
    s = EmotionState(valence=0.0, arousal=0.0)
    sf = s.to_spotify_features()
    assert sf["target_valence"] == 0.5
    assert sf["target_energy"] == 0.5

    s2 = EmotionState(valence=1.0, arousal=-1.0)
    sf2 = s2.to_spotify_features()
    assert sf2["target_valence"] == 1.0
    assert sf2["target_energy"] == 0.0
    print("✅ VA → Spotify feature mapping correct")


if __name__ == "__main__":
    test_iso_principle_starts_at_current()
    test_discharge_amplifies_first()
    test_diversion_is_orthogonal()
    test_va_clamping()
    test_spotify_feature_mapping()
    print("\n🎉 All trajectory tests passed.")
