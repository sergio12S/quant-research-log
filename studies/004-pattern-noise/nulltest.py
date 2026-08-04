#!/usr/bin/env python3
"""Run the pattern miner against data that cannot contain a pattern.

Shuffling a price series' log returns keeps the return distribution, the
volatility and the fat tails exactly, and destroys every temporal relationship.
Anything a miner "discovers" there is selection, by construction. So running the
same pipeline on real bars and on shuffled ones asks a question with a known
answer, which is the only kind worth asking of a discovery tool.

    ./nulltest.py http://127.0.0.1:8142 data/btc_1h_feat.csv

The engine must already be running and licensed. Costs are set on load, at
4.404 bps/side, because the pipeline refuses to promote a frictionless result —
a zero-cost run returns `needs_costs` and tests nothing.
"""
import csv
import json
import math
import random
import sys
import urllib.request
from pathlib import Path

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8142"
DATA = sys.argv[2] if len(sys.argv) > 2 else "data/btc_1h_feat.csv"
OUT = Path("results")
COMMISSION = 0.0004404          # 4.404 bps/side, the figure used across this log
SEEDS = (1, 2, 3)
ANCHORS, TOP_N = 120, 25


def post(path, body, timeout=3600):
    req = urllib.request.Request(
        API + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def shuffled_copy(src: str, dst: str, seed: int) -> None:
    """Same distribution, same volatility, no time structure."""
    rows = list(csv.DictReader(open(src)))
    close = [float(r["close"]) for r in rows]
    ts = [int(r["timestamp"]) for r in rows]
    vol = [float(r["volume"]) for r in rows]
    # Keep the intrabar range distribution too, so the synthetic bars are not
    # obviously degenerate to anything that looks at highs and lows.
    span = [(float(r["high"]) - float(r["low"])) / float(r["close"]) for r in rows]
    lr = [math.log(close[i] / close[i - 1]) for i in range(1, len(close))]

    rnd = random.Random(seed)
    rnd.shuffle(lr)
    rnd.shuffle(span)
    path = [close[0]]
    for x in lr:
        path.append(path[-1] * math.exp(x))

    with open(dst, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "open", "high", "low", "close",
                    "volume", "sma_fast", "sma_slow", "warm"])
        for i, c in enumerate(path):
            o = path[i - 1] if i else c
            half = c * span[i % len(span)] / 2
            hi = max(o, c) + half * rnd.random()
            lo = min(o, c) - half * rnd.random()
            w.writerow([ts[i], f"{o:.2f}", f"{hi:.2f}", f"{lo:.2f}",
                        f"{c:.2f}", f"{vol[i]:.6f}", 0, 0, 0])


def sweep(label: str, path: str) -> dict:
    post("/api/load-data", {"path": str(Path(path).resolve()),
                            "commission": COMMISSION,
                            "signal_execution_timing": "next_open",
                            "dynamic_tp_sl": False})
    d = post("/api/patterns/discover", {"anchor_count": ANCHORS, "top_n": TOP_N})["data"]
    cands = d.get("candidates", [])
    verdicts = {}
    for i, c in enumerate(cands):
        try:
            r = post("/api/patterns/experiment", {
                "report_name": f"nulltest-{label}-{i}",
                "query_closes": c.get("query_closes", []),
                "available_from_timestamp": c["feature_available_from_timestamp"],
                "direction": c.get("direction", "long"),
                "similarity_threshold": c.get("similarity_threshold") or 0.6,
            })["data"]
        except Exception as e:                       # noqa: BLE001
            verdicts["error"] = verdicts.get("error", 0) + 1
            print(f"    #{i} error: {e}", file=sys.stderr)
            continue
        v = r.get("verdict", "?")
        verdicts[v] = verdicts.get(v, 0) + 1
    row = {"label": label,
           "anchors_evaluated": d["anchors_evaluated"],
           "holdout_confirmed": d["anchors_confirmed_by_temporal_holdout"],
           "candidates": len(cands),
           "verdicts": verdicts,
           "promoted": verdicts.get("promoted", 0)}
    print(f"  {label:14} anchors {row['anchors_evaluated']:>3} → holdout "
          f"{row['holdout_confirmed']:>3} → candidates {row['candidates']:>3} "
          f"→ promoted {row['promoted']}   {verdicts}", flush=True)
    return row


def fisher_one_tailed(a: int, n1: int, b: int, n2: int) -> float:
    """P(as many or more of the successes fell in group 1 by chance)."""
    from math import comb
    tot_s, tot = a + b, n1 + n2
    if tot_s == 0:
        return 1.0
    return sum(comb(n1, k) * comb(n2, tot_s - k) / comb(tot, tot_s)
               for k in range(a, min(n1, tot_s) + 1))


def main() -> int:
    OUT.mkdir(exist_ok=True)
    print(f"engine: {post('/api/health', {}) if False else API}")
    print(f"costs:  {COMMISSION * 1e4:.3f} bps/side\n")

    rows = [sweep("BTC-real", DATA)]
    for s in SEEDS:
        dst = OUT / f"_shuffled_{s}.csv"
        shuffled_copy(DATA, dst, s)
        rows.append(sweep(f"noise-{s}", str(dst)))
        dst.unlink()

    real = rows[0]
    noise_n = sum(r["candidates"] for r in rows[1:])
    noise_p = sum(r["promoted"] for r in rows[1:])
    p = fisher_one_tailed(real["promoted"], real["candidates"], noise_p, noise_n)
    rule_of_three = 3 / noise_n * 100 if noise_n else float("nan")

    summary = {"rows": rows,
               "real_promoted": real["promoted"], "real_candidates": real["candidates"],
               "noise_promoted": noise_p, "noise_candidates": noise_n,
               "fisher_one_tailed_p": round(p, 4),
               "noise_promotion_upper_bound_pct": round(rule_of_three, 2)}
    (OUT / "nulltest.json").write_text(json.dumps(summary, indent=2))

    print(f"\nreal  {real['promoted']}/{real['candidates']} promoted")
    print(f"noise {noise_p}/{noise_n} promoted")
    print(f"Fisher exact, one-tailed: p = {p:.3f} "
          f"({'significant' if p < 0.05 else 'NOT significant'})")
    if noise_p == 0:
        print(f"Rule of three: with 0 of {noise_n}, the 95% upper bound on the "
              f"gate's noise-promotion rate is {rule_of_three:.1f}%")
    print(f"\nwritten to {OUT / 'nulltest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
