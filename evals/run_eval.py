"""
Run the 15 eval-pack scenarios through Pulse's inference + trajectory pipeline.
No Spotify contact — just LLM emotion inference and deterministic trajectory generation.
"""
import json
import sys
import os
from pathlib import Path

# Add pulse/ to the Python path so we can import pulse.pulse modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pulse"))

from pulse.inference import EmotionInference
from pulse.trajectory import generate_trajectory

SCENARIOS = [
    {
        "id": 1,
        "title": "Sustained work frustration",
        "vent": "third hour debugging this kafka thing and i can't even tell what's broken anymore",
        "context": "backend work",
        "expected": "discharge",
    },
    {
        "id": 2,
        "title": "Acute grief",
        "vent": "my dad died last night. flying home tomorrow morning. i don't know what to do with myself right now.",
        "context": "",
        "expected": "solace",
    },
    {
        "id": 3,
        "title": "Performance anxiety",
        "vent": "presentation in 20 minutes, hands shaking, can't remember any of my opening lines",
        "context": "important client meeting",
        "expected": "revival / mental_work",
    },
    {
        "id": 4,
        "title": "Sustained low energy",
        "vent": "i don't know, just tired. nothing's really wrong. just kind of going through motions.",
        "context": "tuesday afternoon",
        "expected": "revival",
    },
    {
        "id": 5,
        "title": "Productive flow",
        "vent": "got the schema migration working, feeling like i can take on the rest of this sprint",
        "context": "good momentum, mid-afternoon",
        "expected": "entertainment",
    },
    {
        "id": 6,
        "title": "Existential rumination",
        "vent": "i keep thinking about whether i should be doing something more meaningful with my life. been on this for weeks. can't shake it.",
        "context": "late evening, alone",
        "expected": "mental_work / solace",
    },
    {
        "id": 7,
        "title": "New parent overwhelm",
        "vent": "haven't slept more than three hours in a row in a month. baby just went down. i should be sleeping but i'm staring at the ceiling.",
        "context": "2am, kid asleep",
        "expected": "revival / solace",
    },
    {
        "id": 8,
        "title": "Social rejection",
        "vent": "she said she just wants to be friends. it's fine. it's not fine.",
        "context": "",
        "expected": "solace",
    },
    {
        "id": 9,
        "title": "Hindi loneliness",
        "vent": "मुझे आज बहुत अकेलापन लग रहा है, घर वालों की बहुत याद आ रही है",
        "context": "missing home",
        "expected": "solace",
    },
    {
        "id": 10,
        "title": "Saturday boredom",
        "vent": "saturday afternoon, nothing planned, brain feels empty",
        "context": "weekend",
        "expected": "entertainment / strong_sensation",
    },
    {
        "id": 11,
        "title": "Pre-firing dread",
        "vent": "have to fire someone in an hour. logically i know it's the right call. i feel sick.",
        "context": "management duties",
        "expected": "revival / mental_work",
    },
    {
        "id": 12,
        "title": "Joyful pre-wedding nerves",
        "vent": "wedding in two days. happy but also losing my mind. can't sit still.",
        "context": "personal milestone",
        "expected": "revival / entertainment",
    },
    {
        "id": 13,
        "title": "Post-burnout return",
        "vent": "first day back after a week off. don't want to be here. don't want to be anywhere else either.",
        "context": "back at work",
        "expected": "mental_work / solace",
    },
    {
        "id": 14,
        "title": "Rage at vendor",
        "vent": "stripe just held our payouts again, third time this quarter, support is useless",
        "context": "founder, cash flow stressed",
        "expected": "discharge",
    },
    {
        "id": 15,
        "title": "Caregiver depletion",
        "vent": "mom's chemo round three tomorrow. i'm holding it together for her but i'm not really holding it together.",
        "context": "caregiver",
        "expected": "solace / mental_work",
    },
]


def run_scenario(inference: EmotionInference, scenario: dict) -> str:
    """Run a single scenario and return formatted output text."""
    sid = scenario["id"]
    lines = []
    lines.append(f"=== Scenario {sid}: {scenario['title']} ===")
    lines.append(f"Vent: {scenario['vent']}")
    lines.append(f"Context: {scenario['context'] or '(none)'}")
    lines.append(f"Expected strategy: {scenario['expected']}")
    lines.append("")

    try:
        result = inference.infer(scenario["vent"], scenario["context"])

        cur = result["current_emotion"]
        tgt = result["target_emotion"]
        strat = result["strategy"]
        reasoning = result["reasoning"]

        lines.append(f"Current emotion:  valence={cur.valence:+.2f}, arousal={cur.arousal:+.2f}")
        lines.append(f"Target emotion:   valence={tgt.valence:+.2f}, arousal={tgt.arousal:+.2f}")
        lines.append(f"Strategy chosen:  {strat.value}")
        lines.append(f"Reasoning:        {reasoning}")
        lines.append("")

        trajectory = generate_trajectory(cur, tgt, strat, n_waypoints=4)
        lines.append("Trajectory waypoints:")
        for i, wp in enumerate(trajectory):
            lines.append(f"  [{i+1}] valence={wp.valence:+.2f}, arousal={wp.arousal:+.2f}")

    except Exception as e:
        lines.append(f"ERROR: {type(e).__name__}: {e}")

    lines.append("")
    return "\n".join(lines)


def main():
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(exist_ok=True)

    inference = EmotionInference()
    all_outputs = []

    for scenario in SCENARIOS:
        sid = scenario["id"]
        print(f"Running scenario {sid}/15: {scenario['title']}...", flush=True)

        output = run_scenario(inference, scenario)
        all_outputs.append((scenario, output))

        # Save individual result
        out_file = results_dir / f"scenario_{sid:02d}.txt"
        out_file.write_text(output)
        print(output)
        print("---")

    print(f"\nDone. Results saved to {results_dir}/")


if __name__ == "__main__":
    main()
