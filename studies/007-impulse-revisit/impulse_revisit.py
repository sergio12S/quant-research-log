#!/usr/bin/env python3
"""Test whether a bullish impulse bar's open acts as support on first revisit.

The parameters are fixed in this file. Signals are known at the impulse close;
the revisit is observed later; execution begins at the following bar's open.
"""

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
ROUND_TRIP_COST = FEE_PER_SIDE * 2
REVISIT_DELAY = 3
MAX_REVISIT_BARS = 500
HOLD_BARS = 12
BARRIER_ATR = 0.5
TOLERANCE_ATR = 0.1
BOOTSTRAPS = 2000


def load_bars(path: Path) -> list[dict[str, float]]:
    bars = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            bars.append(
                {
                    "timestamp": int(row["timestamp"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
    return bars


def enrich(bars: list[dict[str, float]]) -> None:
    true_ranges: list[float] = []
    ranges: list[float] = []
    volumes: list[float] = []
    for i, bar in enumerate(bars):
        span = bar["high"] - bar["low"]
        previous_close = bars[i - 1]["close"] if i else bar["close"]
        true_range = max(
            span,
            abs(bar["high"] - previous_close),
            abs(bar["low"] - previous_close),
        )
        bar["range"] = span
        bar["atr14"] = statistics.fmean(true_ranges[-13:] + [true_range]) if i >= 13 else math.nan
        bar["median_range20"] = statistics.median(ranges[-20:]) if i >= 20 else math.nan
        bar["median_volume20"] = statistics.median(volumes[-20:]) if i >= 20 else math.nan
        true_ranges.append(true_range)
        ranges.append(span)
        volumes.append(bar["volume"])


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


def is_impulse(bar: dict[str, float], require_volume: bool) -> bool:
    span = bar["range"]
    if not math.isfinite(bar["atr14"]) or not math.isfinite(bar["median_range20"]):
        return False
    if span <= 0 or bar["median_range20"] <= 0 or bar["median_volume20"] <= 0:
        return False
    body_ratio = (bar["close"] - bar["open"]) / span
    close_position = (bar["close"] - bar["low"]) / span
    base = span / bar["median_range20"] >= 2.0 and body_ratio >= 0.60 and close_position >= 0.80
    if require_volume:
        base = base and bar["volume"] / bar["median_volume20"] >= 1.50
    return base


def collect_events(bars: list[dict[str, float]], require_volume: bool) -> list[dict[str, float | int | str]]:
    events = []
    used_entries: set[int] = set()
    total = len(bars)
    for anchor_index, anchor in enumerate(bars):
        if not is_impulse(anchor, require_volume):
            continue
        level = anchor["open"]
        tolerance = TOLERANCE_ATR * anchor["atr14"]
        last_revisit = min(anchor_index + MAX_REVISIT_BARS, total - HOLD_BARS - 2)
        revisit_index = None
        for index in range(anchor_index + REVISIT_DELAY, last_revisit + 1):
            bar = bars[index]
            if bar["low"] <= level + tolerance and bar["high"] >= level - tolerance:
                revisit_index = index
                break
        if revisit_index is None:
            continue

        entry_index = revisit_index + 1
        if entry_index in used_entries:
            continue
        part = partition(entry_index, total)
        end_index = entry_index + HOLD_BARS
        if end_index > partition_end(part, total):
            continue
        used_entries.add(entry_index)

        entry = bars[entry_index]["open"]
        distance = BARRIER_ATR * anchor["atr14"]
        target = entry + distance
        stop = entry - distance
        outcome = "timeout"
        gross = bars[end_index]["close"] / entry - 1.0
        exit_index = end_index
        for index in range(entry_index, end_index + 1):
            bar = bars[index]
            hit_up = bar["high"] >= target
            hit_down = bar["low"] <= stop
            if hit_down:
                outcome = "down"
                gross = stop / entry - 1.0
                exit_index = index
                break
            if hit_up:
                outcome = "up"
                gross = target / entry - 1.0
                exit_index = index
                break

        events.append(
            {
                "anchor_index": anchor_index,
                "entry_index": entry_index,
                "exit_index": exit_index,
                "partition": part,
                "outcome": outcome,
                "gross_return": gross,
                "net_return": gross - ROUND_TRIP_COST,
            }
        )
    return events


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_mean_ci(values: list[float], seed: int) -> tuple[float, float]:
    if not values:
        return math.nan, math.nan
    rng = random.Random(seed)
    means = []
    for _ in range(BOOTSTRAPS):
        means.append(statistics.fmean(rng.choice(values) for _ in values))
    return percentile(means, 0.025), percentile(means, 0.975)


def summarize(events: list[dict[str, float | int | str]], seed: int) -> dict[str, dict[str, float | int]]:
    output = {}
    for offset, name in enumerate(("discovery", "validation", "final")):
        rows = [row for row in events if row["partition"] == name]
        net = [float(row["net_return"]) for row in rows]
        gross = [float(row["gross_return"]) for row in rows]
        ci_low, ci_high = bootstrap_mean_ci(net, seed + offset)
        output[name] = {
            "events": len(rows),
            "up_first": sum(row["outcome"] == "up" for row in rows),
            "down_first": sum(row["outcome"] == "down" for row in rows),
            "timeouts": sum(row["outcome"] == "timeout" for row in rows),
            "mean_gross_bps": round(statistics.fmean(gross) * 10_000, 3) if gross else math.nan,
            "mean_net_bps": round(statistics.fmean(net) * 10_000, 3) if net else math.nan,
            "median_net_bps": round(statistics.median(net) * 10_000, 3) if net else math.nan,
            "positive_net_pct": round(sum(value > 0 for value in net) / len(net) * 100, 2) if net else math.nan,
            "mean_net_ci95_bps": [round(ci_low * 10_000, 3), round(ci_high * 10_000, 3)],
        }
    return output


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA
    bars = load_bars(path)
    enrich(bars)

    variants = {}
    for index, (name, require_volume) in enumerate(
        (("range_only", False), ("range_and_volume", True))
    ):
        events = collect_events(bars, require_volume)
        variants[name] = {
            "parameters": {"require_volume_confirmation": require_volume},
            "events_total": len(events),
            "partitions": summarize(events, seed=7000 + index * 100),
        }

    final_rows = [variants[name]["partitions"]["final"] for name in variants]
    rejected = all(row["mean_net_bps"] <= 0 or row["mean_net_ci95_bps"][0] <= 0 for row in final_rows)
    payload = {
        "dataset": {
            "bars": len(bars),
            "first_timestamp": bars[0]["timestamp"],
            "last_timestamp": bars[-1]["timestamp"],
        },
        "costs": {"commission_bps_per_side": FEE_PER_SIDE * 10_000, "slippage_bps": 0.0},
        "parameters": {
            "range_multiple": 2.0,
            "body_ratio": 0.60,
            "close_position": 0.80,
            "volume_multiple": 1.50,
            "revisit_delay_bars": REVISIT_DELAY,
            "max_revisit_bars": MAX_REVISIT_BARS,
            "entry": "next_open",
            "barrier_atr": BARRIER_ATR,
            "hold_bars": HOLD_BARS,
        },
        "variants": variants,
        "verdict": "REJECTED" if rejected else "REVIEW_REQUIRED",
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"dataset: {len(bars)} BTCUSDT 1h bars",
        f"cost: {FEE_PER_SIDE * 10_000:.3f} bps/side; slippage not modelled",
        "",
        "variant            partition    events   mean net bps   95% bootstrap CI",
        "-----------------  -----------  -------  -------------  ------------------",
    ]
    for variant, data in variants.items():
        for part, row in data["partitions"].items():
            low, high = row["mean_net_ci95_bps"]
            lines.append(
                f"{variant:17}  {part:11}  {row['events']:7d}  "
                f"{row['mean_net_bps']:+13.3f}  [{low:+.3f}, {high:+.3f}]"
            )
    lines.extend(["", f"verdict: {payload['verdict']}"])
    text = "\n".join(lines) + "\n"
    (RESULTS / "summary.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
