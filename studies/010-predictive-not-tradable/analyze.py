#!/usr/bin/env python3
"""Summarize the raw-predictiveness to threshold-tradability bridge."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def optional_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return center - margin, center + margin


def main() -> int:
    rows = []
    with (ROOT / "evidence.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "candidate": row["candidate"],
                    "raw_score": optional_float(row["raw_score"]),
                    "probe_sharpe": optional_float(row["probe_sharpe"]),
                    "probe_return_pct": optional_float(row["probe_return_pct"]),
                    "max_drawdown_pct": optional_float(row["max_drawdown_pct"]),
                    "simple_threshold_pass": row["simple_threshold_pass"].lower() == "true",
                    "note": row["note"],
                }
            )

    passed = sum(row["simple_threshold_pass"] for row in rows)
    failed = len(rows) - passed
    low, high = wilson(failed, len(rows))
    scored = [row for row in rows if row["raw_score"] is not None]
    strongest = max(scored, key=lambda row: row["raw_score"])
    payload = {
        "candidates": rows,
        "summary": {
            "raw_leads": len(rows),
            "simple_threshold_passes": passed,
            "simple_threshold_failures": failed,
            "failure_rate_pct": round(failed / len(rows) * 100, 2),
            "failure_rate_wilson_ci95_pct": [round(low * 100, 2), round(high * 100, 2)],
            "strongest_raw_candidate": strongest["candidate"],
            "strongest_raw_score": strongest["raw_score"],
            "strongest_raw_probe_sharpe": strongest["probe_sharpe"],
        },
        "verdict": "REJECTED",
        "reason": "RAW_PREDICTIVENESS_DID_NOT_IMPLY_SIMPLE_TRADABILITY",
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "candidate   raw score   probe Sharpe   threshold conversion",
        "---------  ----------  -------------  --------------------",
    ]
    for row in rows:
        raw = "n/a" if row["raw_score"] is None else f"{row['raw_score']:.3f}"
        sharpe = "n/a" if row["probe_sharpe"] is None else f"{row['probe_sharpe']:+.3f}"
        lines.append(
            f"{row['candidate']:^9}  {raw:>10}  {sharpe:>13}  "
            f"{'pass' if row['simple_threshold_pass'] else 'fail'}"
        )
    lines.extend(
        [
            "",
            f"simple-threshold failures: {failed}/{len(rows)} ({failed / len(rows) * 100:.0f}%)",
            f"95% Wilson interval: [{low * 100:.2f}%, {high * 100:.2f}%]",
            f"strongest raw score: {strongest['raw_score']:.3f}; probe Sharpe {strongest['probe_sharpe']:+.3f}",
            "verdict: REJECTED",
        ]
    )
    text = "\n".join(lines) + "\n"
    (RESULTS / "summary.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
