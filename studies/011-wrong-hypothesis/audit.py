#!/usr/bin/env python3
"""Demonstrate a label/direction mismatch with deterministic synthetic events."""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SEED = 11011
EVENTS = 400
BOOTSTRAPS = 2000
FEE_PER_SIDE = 0.0004404


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize(values: list[float], seed: int) -> dict[str, float | int | list[float]]:
    rng = random.Random(seed)
    means = [statistics.fmean(rng.choice(values) for _ in values) for _ in range(BOOTSTRAPS)]
    return {
        "events": len(values),
        "mean_net_bps": round(statistics.fmean(values) * 10_000, 3),
        "median_net_bps": round(statistics.median(values) * 10_000, 3),
        "positive_pct": round(sum(value > 0 for value in values) / len(values) * 100, 2),
        "mean_ci95_bps": [
            round(percentile(means, 0.025) * 10_000, 3),
            round(percentile(means, 0.975) * 10_000, 3),
        ],
    }


def main() -> int:
    rng = random.Random(SEED)
    round_trip_cost = 2 * FEE_PER_SIDE
    shock_returns = [rng.gauss(-0.020, 0.008) for _ in range(EVENTS)]
    rebound_returns = [rng.gauss(0.007, 0.006) for _ in range(EVENTS)]

    # The precursor hypothesis is bearish from before the impulse through the
    # impulse. The invalid pipeline borrows a bullish direction from the later
    # response interval and applies it to the earlier execution interval.
    invalid_long = [value - round_trip_cost for value in shock_returns]
    corrected_short = [-value - round_trip_cost for value in shock_returns]
    post_event_long = [value - round_trip_cost for value in rebound_returns]

    contract = {
        "hypothesis": {
            "feature_window": "pre_event",
            "target_interval": "precursor_to_impulse",
            "direction": "short",
        },
        "label_used_by_invalid_run": {
            "interval": "impulse_to_response",
            "direction": "long",
        },
        "execution_in_invalid_run": {
            "interval": "precursor_to_impulse",
            "direction": "long",
        },
    }
    mismatches = []
    if contract["execution_in_invalid_run"]["direction"] != contract["hypothesis"]["direction"]:
        mismatches.append("execution direction contradicts hypothesis direction")
    if contract["label_used_by_invalid_run"]["interval"] != contract["hypothesis"]["target_interval"]:
        mismatches.append("direction label comes from a different interval")

    payload = {
        "synthetic_fixture": {
            "seed": SEED,
            "events": EVENTS,
            "shock_mean": -0.020,
            "rebound_mean": 0.007,
            "commission_bps_per_side": FEE_PER_SIDE * 10_000,
        },
        "contract": contract,
        "audit": {"valid": not mismatches, "mismatches": mismatches},
        "outcomes": {
            "invalid_long_before_impulse": summarize(invalid_long, 11100),
            "corrected_short_before_impulse": summarize(corrected_short, 11200),
            "separate_post_event_long": summarize(post_event_long, 11300),
        },
        "verdict": "INVALIDATED",
        "reason": "LABEL_DIRECTION_INTERVAL_MISMATCH",
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "audit: INVALID",
        *[f"- {message}" for message in mismatches],
        "",
        "run                              events   mean net bps   95% bootstrap CI",
        "-------------------------------  -------  -------------  ------------------",
    ]
    for name, result in payload["outcomes"].items():
        low, high = result["mean_ci95_bps"]
        lines.append(
            f"{name:31}  {result['events']:7d}  {result['mean_net_bps']:+13.3f}  "
            f"[{low:+.3f}, {high:+.3f}]"
        )
    lines.extend(["", "verdict: INVALIDATED"])
    text = "\n".join(lines) + "\n"
    (RESULTS / "summary.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
