#!/usr/bin/env python3
"""Rebuild the selection and robustness audit for study 009."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CONFIGS_SEARCHED = 200
ELIGIBLE_CONFIGS = 196
COST_SURVIVORS = 53
NOMINAL_ALPHA = 0.05
TOP_TEN_OVERLAP = 6
RANK_SPEARMAN = 0.938


def main() -> int:
    with (ROOT / "top_candidates.csv").open(newline="", encoding="utf-8") as handle:
        candidates = []
        for row in csv.DictReader(handle):
            item = {
                "candidate": row["candidate"],
                "wfe": float(row["wfe"]),
                "oos_positive": int(row["oos_positive"]),
                "oos_windows": int(row["oos_windows"]),
                "monte_carlo_p05_pct": float(row["monte_carlo_p05_pct"]),
            }
            item["majority_oos_positive"] = item["oos_positive"] > item["oos_windows"] / 2
            item["passes"] = (
                item["wfe"] >= 0.5
                and item["majority_oos_positive"]
                and item["monte_carlo_p05_pct"] > 0
            )
            candidates.append(item)

    payload = {
        "search": {
            "configs": CONFIGS_SEARCHED,
            "eligible_minimum_trade_count": ELIGIBLE_CONFIGS,
            "cost_survivors": COST_SURVIVORS,
            "cost_survival_pct": round(COST_SURVIVORS / ELIGIBLE_CONFIGS * 100, 2),
            "expected_nominal_false_winners_at_5pct": CONFIGS_SEARCHED * NOMINAL_ALPHA,
            "probability_at_least_one_nominal_false_winner_pct": round(
                (1 - (1 - NOMINAL_ALPHA) ** CONFIGS_SEARCHED) * 100, 4
            ),
        },
        "ranking": {
            "top_ten_overlap": TOP_TEN_OVERLAP,
            "top_ten_size": 10,
            "spearman_return_vs_breakeven": RANK_SPEARMAN,
        },
        "robustness": {
            "candidates": candidates,
            "passed": sum(item["passes"] for item in candidates),
            "tested": len(candidates),
            "gates": {
                "wfe_minimum": 0.5,
                "strict_majority_oos_positive": True,
                "monte_carlo_p05_above_zero": True,
            },
        },
        "verdict": "REJECTED",
        "reason": "COST_SURVIVAL_IS_NOT_OOS_VALIDATION",
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        f"search: {CONFIGS_SEARCHED} configs; {ELIGIBLE_CONFIGS} met the trade-count floor",
        f"cost survivors: {COST_SURVIVORS}/{ELIGIBLE_CONFIGS} ({payload['search']['cost_survival_pct']:.2f}%)",
        f"nominal 5% winners expected by chance: {payload['search']['expected_nominal_false_winners_at_5pct']:.1f}",
        f"P(at least one nominal false winner): {payload['search']['probability_at_least_one_nominal_false_winner_pct']:.4f}%",
        f"return/breakeven top-10 overlap: {TOP_TEN_OVERLAP}/10; Spearman {RANK_SPEARMAN:.3f}",
        "",
        "candidate   WFE   positive OOS   MC p05    passes all gates",
        "---------  ----  -------------  --------  ----------------",
    ]
    for item in candidates:
        lines.append(
            f"{item['candidate']:^9}  {item['wfe']:.2f}     "
            f"{item['oos_positive']:>2}/{item['oos_windows']:<2}       "
            f"{item['monte_carlo_p05_pct']:+6.2f}%       {'yes' if item['passes'] else 'no'}"
        )
    lines.extend(["", f"robust passes: {payload['robustness']['passed']}/{len(candidates)}", "verdict: REJECTED"])
    text = "\n".join(lines) + "\n"
    (RESULTS / "summary.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
