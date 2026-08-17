#!/usr/bin/env python3
"""Test whether an ordered state chain adds value beyond its final state."""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "btc_1h.csv"
RESULTS = ROOT / "results"
FEE_PER_SIDE = 0.0004404
LOOKBACK = 8
BREAKOUT_WINDOW = 24
VOLUME_WINDOW = 168
HOLD_BARS = 6
BOOTSTRAPS = 2000


def load_bars(path: Path) -> list[dict[str, float | int]]:
    output = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            output.append(
                {
                    "timestamp": int(row["timestamp"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
    return output


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def partition(index: int, total: int) -> str:
    if index < int(total * 0.60):
        return "discovery"
    if index < int(total * 0.80):
        return "validation"
    return "final"


def partition_end(name: str, total: int) -> int:
    if name == "discovery":
        return int(total * 0.60) - 1
    if name == "validation":
        return int(total * 0.80) - 1
    return total - 1


def classify_events(bars: list[dict[str, float | int]]) -> list[dict[str, float | int | str]]:
    volume_expansion = [False] * len(bars)
    buy_pressure = [False] * len(bars)
    failed_breakout = [False] * len(bars)
    for index, bar in enumerate(bars):
        span = float(bar["high"]) - float(bar["low"])
        if span > 0:
            body_ratio = (float(bar["close"]) - float(bar["open"])) / span
            close_position = (float(bar["close"]) - float(bar["low"])) / span
            buy_pressure[index] = body_ratio >= 0.60 and close_position >= 0.80
        if index >= VOLUME_WINDOW:
            threshold = percentile(
                [float(item["volume"]) for item in bars[index - VOLUME_WINDOW : index]],
                0.80,
            )
            volume_expansion[index] = float(bar["volume"]) > threshold
        if index >= BREAKOUT_WINDOW:
            prior_high = max(float(item["high"]) for item in bars[index - BREAKOUT_WINDOW : index])
            failed_breakout[index] = float(bar["high"]) > prior_high and float(bar["close"]) <= prior_high

    events = []
    last_exit = -1
    total = len(bars)
    for index in range(max(VOLUME_WINDOW, BREAKOUT_WINDOW), total - HOLD_BARS - 1):
        if not failed_breakout[index] or index <= last_exit:
            continue
        entry_index = index + 1
        part = partition(entry_index, total)
        exit_index = entry_index + HOLD_BARS
        if exit_index > partition_end(part, total):
            continue

        start = max(0, index - LOOKBACK)
        volume_indices = [i for i in range(start, index) if volume_expansion[i]]
        pressure_indices = [i for i in range(start, index) if buy_pressure[i]]
        ordered = any(a < b for a in volume_indices for b in pressure_indices)
        reversed_order = any(b < a for a in volume_indices for b in pressure_indices)
        if ordered:
            cohort = "ordered"
        elif reversed_order:
            cohort = "reversed"
        else:
            cohort = "failure_only"

        entry = float(bars[entry_index]["open"])
        exit_price = float(bars[exit_index]["close"])
        gross_short = (entry - exit_price) / entry
        events.append(
            {
                "partition": part,
                "cohort": cohort,
                "gross_return": gross_short,
                "net_return": gross_short - 2 * FEE_PER_SIDE,
            }
        )
        last_exit = exit_index
    return events


def bootstrap_mean(values: list[float], seed: int) -> tuple[float, float]:
    if not values:
        return math.nan, math.nan
    rng = random.Random(seed)
    means = [statistics.fmean(rng.choice(values) for _ in values) for _ in range(BOOTSTRAPS)]
    return percentile(means, 0.025), percentile(means, 0.975)


def bootstrap_difference(left: list[float], right: list[float], seed: int) -> tuple[float, float]:
    if not left or not right:
        return math.nan, math.nan
    rng = random.Random(seed)
    diffs = []
    for _ in range(BOOTSTRAPS):
        lmean = statistics.fmean(rng.choice(left) for _ in left)
        rmean = statistics.fmean(rng.choice(right) for _ in right)
        diffs.append(lmean - rmean)
    return percentile(diffs, 0.025), percentile(diffs, 0.975)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA
    bars = load_bars(path)
    events = classify_events(bars)
    partitions = {}
    for part_index, part in enumerate(("discovery", "validation", "final")):
        part_rows = [row for row in events if row["partition"] == part]
        cohorts = {}
        for cohort_index, cohort in enumerate(("ordered", "reversed", "failure_only")):
            rows = [row for row in part_rows if row["cohort"] == cohort]
            net = [float(row["net_return"]) for row in rows]
            low, high = bootstrap_mean(net, 8000 + part_index * 100 + cohort_index)
            cohorts[cohort] = {
                "events": len(rows),
                "mean_net_bps": round(statistics.fmean(net) * 10_000, 3) if net else None,
                "positive_net_pct": round(sum(value > 0 for value in net) / len(net) * 100, 2) if net else None,
                "mean_net_ci95_bps": [round(low * 10_000, 3), round(high * 10_000, 3)] if net else None,
            }
        ordered_net = [float(row["net_return"]) for row in part_rows if row["cohort"] == "ordered"]
        baseline_net = [float(row["net_return"]) for row in part_rows if row["cohort"] == "failure_only"]
        diff_low, diff_high = bootstrap_difference(ordered_net, baseline_net, 9000 + part_index)
        partitions[part] = {
            "cohorts": cohorts,
            "ordered_minus_failure_only_ci95_bps": (
                [round(diff_low * 10_000, 3), round(diff_high * 10_000, 3)]
                if ordered_net and baseline_net
                else None
            ),
        }

    final = partitions["final"]["cohorts"]["ordered"]
    final_diff = partitions["final"]["ordered_minus_failure_only_ci95_bps"]
    if final["events"] < 30:
        verdict = "INCONCLUSIVE"
        reason = "LOW_SUPPORT"
    elif final["mean_net_ci95_bps"][0] > 0 and final_diff and final_diff[0] > 0:
        verdict = "REVIEW_REQUIRED"
        reason = "POSITIVE_UNTOUCHED_RESULT"
    else:
        verdict = "REJECTED"
        reason = "NO_INCREMENTAL_OOS_EDGE"

    payload = {
        "dataset": {
            "bars": len(bars),
            "first_timestamp": bars[0]["timestamp"],
            "last_timestamp": bars[-1]["timestamp"],
        },
        "parameters": {
            "volume_threshold": "past 168-bar 80th percentile",
            "buy_pressure": "body/range >= 0.60 and close in top 20%",
            "failed_breakout": "high exceeds prior 24-bar high and close returns below it",
            "sequence_window_bars": LOOKBACK,
            "entry": "next_open",
            "hold_bars": HOLD_BARS,
            "commission_bps_per_side": FEE_PER_SIDE * 10_000,
        },
        "partitions": partitions,
        "verdict": verdict,
        "reason": reason,
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "cohort       partition    events   mean net bps   95% bootstrap CI",
        "-----------  -----------  -------  -------------  ------------------",
    ]
    for part, part_data in partitions.items():
        for cohort, row in part_data["cohorts"].items():
            ci = row["mean_net_ci95_bps"]
            if ci is None:
                rendered = "[n/a, n/a]"
                mean = "n/a"
            else:
                rendered = f"[{ci[0]:+.3f}, {ci[1]:+.3f}]"
                mean = f"{row['mean_net_bps']:+.3f}"
            lines.append(f"{cohort:11}  {part:11}  {row['events']:7d}  {mean:>13}  {rendered}")
    lines.extend(["", f"verdict: {verdict} ({reason})"])
    text = "\n".join(lines) + "\n"
    (RESULTS / "summary.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if verdict != "REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
