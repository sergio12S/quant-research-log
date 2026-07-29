#!/usr/bin/env python3
"""Find the breakeven fee for one rule across a grid of take-profit distances.

Breakeven fee is the per-side commission at which the strategy's gross edge is
exactly consumed. It is the honest way to rank candidates, because it is
scale-invariant — position sizing cannot flatter it — and because it answers the
question that actually matters: how much execution cost can this survive?

The engine charges commission on entry and exit separately (see position.rs),
so the figure below is per side.
"""
import json
import subprocess
import sys
from pathlib import Path

RLX = sys.argv[1] if len(sys.argv) > 1 else "rlx-cli"
OUT = Path("results/breakeven.json")

# Two moving averages on closes, long only, symmetric bracket. Chosen because
# it is public domain, has a small but real gross edge on this data, and is
# nobody's proprietary rule — the study is about cost geometry, not about a signal.
FAST, SLOW = 24, 168

TAKE_PROFITS = [0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.04, 0.06, 0.08, 0.10]
TIMEFRAMES = [("5m", None), ("1h", "data/btc_1h.csv"), ("4h", "data/btc_4h.csv"), ("1D", "data/btc_1d.csv")]

MAX_FEE = 0.02          # 200 bps/side — far past anything real
ITERATIONS = 20         # 0.02 / 2^20 ≈ 2e-8, well below reporting precision


def run(data: str, tp: float, commission: float) -> dict:
    rules = {
        "entry_rules": [
            {"condition": "warm > 0 && sma_fast > sma_slow", "signal": "Long", "direction": 1}
        ],
        "exit_rules": [{"condition": "sma_fast < sma_slow", "reason": "RegimeExit"}],
        "take_profit_pct": tp,
        "stop_loss_pct": tp,
    }
    Path("results/_rules.json").write_text(json.dumps(rules))
    proc = subprocess.run(
        [
            RLX, "rules-backtest",
            "-d", data,
            "-r", "results/_rules.json",
            "--commission", f"{commission:.10f}",
            # Same-bar execution would let a signal trade on the bar that
            # produced it. Next open is the weakest assumption that is not a
            # look-ahead.
            "--signal-execution-timing", "next_open",
            # The engine defaults this to true, which synthesises take-profit and
            # stop-loss levels for strategies that specified none — and perturbs
            # them even for strategies that did. This study is about the bracket
            # it states, so the layer is turned off.
            "--dynamic-tp-sl", "false",
            "--json",
        ],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"engine failed:\n{proc.stderr[:600]}")
    return json.loads(proc.stdout)


def breakeven(data: str, tp: float) -> dict:
    gross = run(data, tp, 0.0)
    row = {
        "take_profit_pct": tp,
        "trades": gross["total_trades"],
        "gross_return_pct": round(gross["total_return"] * 100, 4),
    }
    if gross["total_return"] <= 0 or gross["total_trades"] == 0:
        # No gross edge to consume: cost is not what killed this one.
        row["breakeven_bps"] = 0.0
        return row

    lo, hi = 0.0, MAX_FEE
    if run(data, tp, hi)["total_return"] > 0:
        row["breakeven_bps"] = None      # survives 200 bps/side; not credible, flag it
        return row
    for _ in range(ITERATIONS):
        mid = (lo + hi) / 2
        if run(data, tp, mid)["total_return"] > 0:
            lo = mid
        else:
            hi = mid
    row["breakeven_bps"] = round(lo * 10_000, 3)
    return row


def main() -> None:
    Path("results").mkdir(exist_ok=True)
    out = {"fast": FAST, "slow": SLOW, "timeframes": {}}
    for name, data in TIMEFRAMES:
        if data is None or not Path(data).exists():
            print(f"skip {name}: no data")
            continue
        feat = data.replace(".csv", "_feat.csv")
        subprocess.run(
            [sys.executable, "build_features.py", data, feat, str(FAST), str(SLOW)],
            check=True, capture_output=True,
        )
        rows = []
        for tp in TAKE_PROFITS:
            r = breakeven(feat, tp)
            rows.append(r)
            be = "n/a" if r["breakeven_bps"] is None else f'{r["breakeven_bps"]:8.3f}'
            print(f'{name:>3}  TP {tp*100:5.2f}%  trades {r["trades"]:6d}  '
                  f'gross {r["gross_return_pct"]:9.2f}%  breakeven {be} bps/side',
                  flush=True)
        out["timeframes"][name] = rows
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
