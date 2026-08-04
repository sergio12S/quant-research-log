#!/usr/bin/env python3
"""Does the screen work on a strategy made of several independently-sized sleeves?

The identity in this study assumes one position at a time, deploying a fixed
fraction of equity. A factor library is not that: it is N sleeves, each holding
its own slice of capital. This asks whether the screen can be rescued for that
case by any substitution of aggregate quantities — total trades, weighted
trades — and answers no.

Needs the HTTP API rather than the CLI, because `/api/portfolio` is the only
place the multi-sleeve capital model exists. Start the engine (the macOS app
serves it on 127.0.0.1:8142) and run:

    ./portfolio.py http://127.0.0.1:8142
"""
import csv
import json
import math
import sys
import urllib.request
from pathlib import Path

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8142"
SRC = Path("data/btc_1h_feat.csv")
GEN = Path("results/_btc_multi.csv")
OUT = Path("results/portfolio.json")

PERIODS = [12, 48, 96, 240]
CASES = [
    ("equal 0.25 x4", [12, 48, 96, 240], [0.25, 0.25, 0.25, 0.25]),
    ("tilted 0.4/0.3/0.2/0.1", [12, 48, 96, 240], [0.4, 0.3, 0.2, 0.1]),
    ("two sleeves 0.5/0.5", [12, 240], [0.5, 0.5]),
    ("extreme 0.85/0.05/0.05/0.05", [12, 48, 96, 240], [0.85, 0.05, 0.05, 0.05]),
    ("three sleeves 0.6/0.3/0.1", [48, 96, 240], [0.6, 0.3, 0.1]),
]
ITERATIONS = 20
MAX_FEE = 0.03


def post(path, body, timeout=1800):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def build_features() -> None:
    """Add the moving averages the sleeves need. The engine has no functions —
    indicators must already be columns — so they are computed here."""
    rows = list(csv.DictReader(open(SRC)))
    close = [float(r["close"]) for r in rows]
    sma = {}
    for p in PERIODS:
        acc, col = 0.0, []
        for i, c in enumerate(close):
            acc += c
            if i >= p:
                acc -= close[i - p]
            col.append(acc / min(i + 1, p) if i + 1 >= p else 0.0)
        sma[p] = col
    warm = max(PERIODS)
    GEN.parent.mkdir(exist_ok=True)
    with open(GEN, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"]
                   + [f"sma_{p}" for p in PERIODS] + ["warm"])
        for i, r in enumerate(rows):
            w.writerow([r["timestamp"], r["open"], r["high"], r["low"],
                        r["close"], r["volume"]]
                       + [f"{sma[p][i]:.4f}" for p in PERIODS]
                       + [1 if i >= warm else 0])


def sleeve(n: int) -> dict:
    return {"name": f"sma{n}",
            "entry_rules": [{"condition": f"warm > 0 && close > sma_{n}", "direction": 1}],
            "exit_rules": [{"condition": f"close < sma_{n}"}]}


def run(fee: float, periods, weights) -> dict:
    post("/api/load-data", {"path": str(GEN.resolve()), "commission": fee,
                            "signal_execution_timing": "next_open",
                            "dynamic_tp_sl": False})
    return post("/api/portfolio", {"strategies": [sleeve(p) for p in periods],
                                   "weights": weights})["data"]


def solve_sleevewise(L, n, w) -> float:
    """Fee at which Σ wᵢ·exp(Lᵢ − 2nᵢf) = 1, i.e. the portfolio's equity returns
    to its starting value. No closed form; bisected."""
    def f(x):
        return sum(wi * math.exp(Li - 2 * ni * x) for wi, Li, ni in zip(w, L, n)) - 1
    lo, hi = 0.0, MAX_FEE
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return lo


def main() -> int:
    build_features()
    out = []
    print(f"{'portfolio':32} {'naive':>8} {'weighted':>9} {'sleevewise':>11} {'measured':>10}")
    for label, periods, weights in CASES:
        g = run(0.0, periods, weights)
        Rp = g["portfolio"]["total_return"]
        sl = [(s["trades"], s["total_return"], s["weight"]) for s in g["strategies"]]

        # Sanity: the portfolio's return must be the weighted sum of the
        # sleeves'. If this fails, the capital model is not what we think.
        assert abs(Rp - sum(w * r for _, r, w in sl)) < 1e-9, "capital model mismatch"

        lo, hi = 0.0, MAX_FEE
        for _ in range(ITERATIONS):
            mid = (lo + hi) / 2
            if run(mid, periods, weights)["portfolio"]["total_return"] > 0:
                lo = mid
            else:
                hi = mid
        measured = lo * 1e4

        n_tot = sum(t for t, _, _ in sl)
        n_wtd = sum(t * w for t, _, w in sl)
        naive = math.log(1 + Rp) / (2 * n_tot) * 1e4
        weighted = math.log(1 + Rp) / (2 * n_wtd) * 1e4
        sleevewise = solve_sleevewise([math.log(1 + r) for _, r, _ in sl],
                                      [t for t, _, _ in sl],
                                      [w for _, _, w in sl]) * 1e4

        out.append({"label": label, "portfolio_return": round(Rp, 8),
                    "total_trades": n_tot, "weighted_trades": round(n_wtd, 2),
                    "naive_bps": round(naive, 4), "weighted_bps": round(weighted, 4),
                    "sleevewise_bps": round(sleevewise, 4),
                    "measured_bps": round(measured, 4),
                    "naive_ratio": round(naive / measured, 4),
                    "weighted_ratio": round(weighted / measured, 4),
                    "sleevewise_ratio": round(sleevewise / measured, 4),
                    "sleeves": [{"trades": t, "return": round(r, 8), "weight": w}
                                for t, r, w in sl]})
        print(f"{label:32} {naive:>8.3f} {weighted:>9.3f} {sleevewise:>11.3f} "
              f"{measured:>10.3f}")
        print(f"{'  ratio to measured':32} {naive/measured:>8.4f} "
              f"{weighted/measured:>9.4f} {sleevewise/measured:>11.4f}")

    OUT.write_text(json.dumps(out, indent=2))
    GEN.unlink(missing_ok=True)
    err = [abs(o["sleevewise_ratio"] - 1) for o in out]
    print(f"\n{len(out)} portfolios. Sleeve-wise model vs bisection: "
          f"max error {max(err)*100:.2f}%")
    print("Naive and weighted aggregates are not close, and their error is not "
          "even a constant:")
    print(f"  naive ratio spans    {min(o['naive_ratio'] for o in out):.2f}"
          f"–{max(o['naive_ratio'] for o in out):.2f}")
    print(f"  weighted ratio spans {min(o['weighted_ratio'] for o in out):.2f}"
          f"–{max(o['weighted_ratio'] for o in out):.2f}")
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
