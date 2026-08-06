#!/usr/bin/env python3
"""Rank a set of candidates by return and by breakeven fee, and compare.

Screen 1 of a private research programme reads: *report the return, never rank
on it — it inverted the true ordering here*. That claim is checkable. Build a
grid of candidate strategies on public data, rank it both ways, and see whether
the orderings agree.

    ./screens.py /path/to/rlx-cli

Breakeven fee is `ln(1 + gross_return) / (2 × trades)` — the per-side commission
at which the gross edge is exactly consumed. Derived and validated against
bisection in study 001; generalised to fractional sizing in study 003. Nothing
here needs a particular engine: the two inputs are numbers every backtester
already reports.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

RLX = sys.argv[1] if len(sys.argv) > 1 else "rlx-cli"
OUT = Path("results")
COST_BPS = 4.404          # the live per-side cost used across this log

# A grid, not a search. Every cell is reported; nothing is selected on its
# result, because selecting is the failure this study is about.
# The `_feat` files carry sma_fast/sma_slow/warm; the plain ones are raw OHLCV
# and would silently produce zero trades, since a missing column evaluates false.
TIMEFRAMES = [("1h", "data/btc_1h_feat.csv"),
              ("4h", "data/btc_4h_feat.csv"),
              ("1D", "data/btc_1d_feat.csv")]
TAKE_PROFITS = [0.005, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08, 0.10]

# Structurally different entries, not one rule with a swept parameter. Turnover
# has to vary independently of the family for the two rankings to be able to
# disagree at all — a single family's return and trade count move together.
ENTRIES = {
    "trend":  ("warm > 0 && sma_fast > sma_slow", "sma_fast < sma_slow"),
    "fast":   ("warm > 0 && close > sma_fast",    "close < sma_fast"),
    "slow":   ("warm > 0 && close > sma_slow",    "close < sma_slow"),
    "narrow": ("warm > 0 && close > open && sma_fast > sma_slow",
               "close < open || sma_fast < sma_slow"),
}


def run(data: str, tp: float, entry: str, exit_: str) -> dict:
    """One frictionless backtest. Costs are applied afterwards, analytically."""
    rules = {
        "entry_rules": [{"condition": entry, "signal": "Long", "direction": 1}],
        "exit_rules": [{"condition": exit_, "reason": "RegimeExit"}],
        "take_profit_pct": tp,
        "stop_loss_pct": tp,
    }
    OUT.mkdir(exist_ok=True)
    Path("results/_rules.json").write_text(json.dumps(rules))
    p = subprocess.run(
        [RLX, "rules-backtest", "-d", data, "-r", "results/_rules.json",
         "--commission", "0",
         # Same-bar execution is a look-ahead; the overlay adds a bracket the
         # rules never declared. Both are engine defaults and both flatter.
         "--signal-execution-timing", "next_open",
         "--dynamic-tp-sl", "false",
         "--json"],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"engine failed:\n{p.stderr[:600]}")
    return json.loads(p.stdout)


def breakeven_bps(gross: float, trades: int) -> float:
    if trades <= 0 or gross <= 0:
        return 0.0
    return math.log(1 + gross) / (2 * trades) * 1e4


def spearman(a: list[float], b: list[float]) -> float:
    """Rank correlation, computed here so the study has no extra dependency."""
    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0.0


def main() -> int:
    OUT.mkdir(exist_ok=True)
    rows = []
    for tf, data in TIMEFRAMES:
        if not Path(data).exists():
            print(f"  skipping {tf}: {data} not found", file=sys.stderr)
            continue
        for name, (entry, exit_) in ENTRIES.items():
          for tp in TAKE_PROFITS:
            r = run(data, tp, entry, exit_)
            gross, n = r["total_return"], r["total_trades"]
            rows.append({"candidate": f"{name} tp={tp*100:g}% {tf}",
                         "entry": name, "timeframe": tf, "take_profit": tp,
                         "gross_return": round(gross, 6), "trades": n,
                         "breakeven_bps": round(breakeven_bps(gross, n), 4)})
            print(f"  {rows[-1]['candidate']:28} {gross*100:>9.2f}%  {n:>6} trades  "
                  f"{rows[-1]['breakeven_bps']:>8.2f} bps", flush=True)

    live = [r for r in rows if r["gross_return"] > 0]
    by_return = sorted(live, key=lambda r: -r["gross_return"])
    by_breakeven = sorted(live, key=lambda r: -r["breakeven_bps"])

    rho = spearman([r["gross_return"] for r in live], [r["breakeven_bps"] for r in live])
    k = min(5, len(live))
    top_r = {r["candidate"] for r in by_return[:k]}
    top_b = {r["candidate"] for r in by_breakeven[:k]}
    overlap = len(top_r & top_b)

    survivors = [r for r in live if r["breakeven_bps"] > COST_BPS]
    dead_but_top = [r for r in by_return[:k] if r["breakeven_bps"] <= COST_BPS]

    summary = {
        "cost_bps": COST_BPS,
        "candidates": len(rows),
        "with_gross_edge": len(live),
        "survive_cost": len(survivors),
        "spearman_return_vs_breakeven": round(rho, 4),
        f"top{k}_overlap": overlap,
        "top_by_return": [r["candidate"] for r in by_return[:k]],
        "top_by_breakeven": [r["candidate"] for r in by_breakeven[:k]],
        "ranked_top_by_return_but_dead_at_cost":
            [{"candidate": r["candidate"], "gross_return": r["gross_return"],
              "breakeven_bps": r["breakeven_bps"]} for r in dead_but_top],
        "rows": rows,
    }
    (OUT / "screens.json").write_text(json.dumps(summary, indent=2))

    print(f"\n{len(rows)} candidates, {len(live)} with a gross edge, "
          f"{len(survivors)} survive {COST_BPS} bps/side")
    print(f"Spearman(return, breakeven) = {rho:+.4f}")
    print(f"top-{k} by return vs by breakeven: {overlap} of {k} in common")
    if dead_but_top:
        print("\nRanked in the top by return, dead at real cost:")
        for r in dead_but_top:
            print(f"  {r['candidate']:28} {r['gross_return']*100:>9.2f}% gross, "
                  f"breakeven {r['breakeven_bps']:.2f} bps")
    else:
        print("\nNo candidate in the return-ranked top is dead at cost on this grid.")
    print(f"\nwritten to {OUT / 'screens.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
