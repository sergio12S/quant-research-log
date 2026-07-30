#!/usr/bin/env python3
"""Measure the screen against bisection, including the position-size correction.

The screen claims

    breakeven_fee = ln(1 + gross_return) / (2 · trades · position_size)

Bisecting the commission until the strategy's return crosses zero answers the
same question without the formula, so the two can be compared. Study 001 did
this at full size; the reason to do it again is the `position_size` term, which
001 could not test — the engine accepted the field and ignored it, so every
sizing produced identical results. Fixed in rlx 0.2.12.

    ./validate.py /path/to/rlx-cli
"""
import json
import math
import subprocess
import sys
from pathlib import Path

RLX = sys.argv[1] if len(sys.argv) > 1 else "rlx-cli"
DATA = "data/btc_1h_feat.csv"
OUT = Path("results/validation.json")

MAX_FEE = 0.05        # 500 bps/side — far past anything real
ITERATIONS = 24       # 0.05 / 2^24 ≈ 3e-9

ENTRY = {"condition": "warm > 0 && sma_fast > sma_slow", "direction": 1}

# Two rules with a genuine gross edge and very different trade counts, so the
# comparison is not a single accident. The 1% bracket is deliberately absent:
# it has no gross edge on this data, and a breakeven of zero tells you nothing
# about whether the formula works.
RULES = {
    "sma_bracket_3pct": {"entry_rules": [ENTRY],
                         "exit_rules": [{"condition": "sma_fast < sma_slow"}],
                         "take_profit_pct": 0.03, "stop_loss_pct": 0.03},
    "sma_no_bracket": {"entry_rules": [ENTRY],
                       "exit_rules": [{"condition": "sma_fast < sma_slow"}]},
}
SIZES = [1.0, 0.75, 0.5, 0.2]


def run(base: dict, size: float, fee: float) -> dict:
    strategy = dict(base, position_size=size)
    Path("results/_rules.json").write_text(json.dumps(strategy))
    p = subprocess.run(
        [RLX, "rules-backtest", "-d", DATA, "-r", "results/_rules.json",
         "--commission", f"{fee:.12f}",
         # Same-bar execution lets a signal trade on the bar that produced it.
         "--signal-execution-timing", "next_open",
         # Otherwise the engine overlays a bracket these rules never declared.
         "--dynamic-tp-sl", "false",
         "--json"],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"engine failed:\n{p.stderr[:600]}")
    return json.loads(p.stdout)


def measured_breakeven(base: dict, size: float) -> float:
    lo, hi = 0.0, MAX_FEE
    for _ in range(ITERATIONS):
        mid = (lo + hi) / 2
        if run(base, size, mid)["total_return"] > 0:
            lo = mid
        else:
            hi = mid
    return lo * 1e4


def main() -> int:
    Path("results").mkdir(exist_ok=True)
    out = []
    print(f"{'rule':18} {'size':>5} {'trades':>7} {'gross':>9} "
          f"{'formula':>9} {'measured':>9} {'ratio':>7}")
    for name, base in RULES.items():
        for size in SIZES:
            gross = run(base, size, 0.0)
            r, n = gross["total_return"], gross["total_trades"]
            if r <= 0 or n == 0:
                print(f"{name:18} {size:>5} {n:>7}   no gross edge — skipped")
                continue
            # The naive form, as study 001 stated it: no sizing term.
            naive = math.log(1 + r) / (2 * n) * 1e4
            meas = measured_breakeven(base, size)
            out.append({"rule": name, "position_size": size, "trades": n,
                        "gross_return": round(r, 8),
                        "naive_bps": round(naive, 4),
                        "corrected_bps": round(naive / size, 4),
                        "measured_bps": round(meas, 4),
                        "naive_over_measured": round(naive / meas, 5)})
            print(f"{name:18} {size:>5} {n:>7} {r*100:>8.2f}% "
                  f"{naive:>9.3f} {meas:>9.3f} {naive/meas:>7.4f}")

    OUT.write_text(json.dumps(out, indent=2))
    err = [abs(o["corrected_bps"] - o["measured_bps"]) / o["measured_bps"] for o in out]
    print(f"\n{len(out)} points. Corrected formula vs bisection: "
          f"max error {max(err)*100:.2f}%, median {sorted(err)[len(err)//2]*100:.2f}%")
    print("The `ratio` column is the uncorrected formula divided by the measured "
          "value.\nIt equals position_size, which is what the correction removes.")
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
