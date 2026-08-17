#!/usr/bin/env python3
"""Rebuild the compact evidence table for study 006.

The CSV is a deliberately small, public evidence extract. It contains the
frozen final metrics needed for this synthesis, not private features, signals,
timestamps, or executable strategy parameters.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence.csv"
RESULTS = ROOT / "results"


def optional_int(value: str) -> int | None:
    return int(value) if value.strip() else None


def main() -> int:
    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    normalized = []
    for row in rows:
        normalized.append(
            {
                "experiment": row["experiment"],
                "promising_metric": row["promising_metric"],
                "promising_value": float(row["promising_value"]),
                "final_net_ev_bps": float(row["final_net_ev_bps"]),
                "walk_forward": {
                    "positive": optional_int(row["wf_positive"]),
                    "total": optional_int(row["wf_total"]),
                },
                "cross_asset": {
                    "positive": optional_int(row["cross_asset_positive"]),
                    "total": optional_int(row["cross_asset_total"]),
                },
                "decision": row["decision"],
            }
        )

    negative = [row for row in normalized if row["final_net_ev_bps"] < 0]
    summary = {
        "experiments": normalized,
        "experiment_count": len(normalized),
        "negative_final_ev_count": len(negative),
        "best_final_net_ev_bps": max(row["final_net_ev_bps"] for row in normalized),
        "worst_final_net_ev_bps": min(row["final_net_ev_bps"] for row in normalized),
        "verdict": "REJECTED" if len(negative) == len(normalized) else "MIXED",
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "experiment                      final net EV     robustness",
        "------------------------------  ---------------  ------------------------",
    ]
    for row in normalized:
        wf = row["walk_forward"]
        cross = row["cross_asset"]
        if wf["total"] is not None:
            robustness = f"WF {wf['positive']}/{wf['total']} positive"
        elif cross["total"] is not None:
            robustness = f"assets {cross['positive']}/{cross['total']} positive"
        else:
            robustness = "not reported"
        lines.append(
            f"{row['experiment'][:30]:30}  {row['final_net_ev_bps']:+10.2f} bps  {robustness}"
        )
    lines.extend(
        [
            "",
            f"verdict: {summary['verdict']}",
            f"negative final expectancy: {len(negative)}/{len(normalized)} experiments",
        ]
    )
    output = "\n".join(lines) + "\n"
    (RESULTS / "summary.txt").write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
