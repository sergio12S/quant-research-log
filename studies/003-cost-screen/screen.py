#!/usr/bin/env python3
"""Screen a published strategy table for rows that cannot survive their costs.

Input is a CSV with at least `name`, `gross_return` and `trades`. An optional
`position_size` column gives the fraction of equity deployed per position; it
defaults to 1.0, and getting it wrong is the largest error this tool can make
(see the README).

    ./screen.py table.csv --cost 4.404

`gross_return` is a fraction, so 0.5 means +50%. `--cost` is basis points per
side. Output is the per-side fee at which each row's gross edge is exactly
consumed, and whether that is above or below the cost you named.

This is a one-way test. A row that fails is dead at the cost you named, assuming
the numbers it reports are honest. A row that passes has only shown that cost is
not what kills it — nothing here says the edge is real.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path


def breakeven_bps(gross_return: float, trades: int, position_size: float = 1.0):
    """Per-side fee, in bps, at which the gross edge is exactly consumed.

    Full-capital compounding pays the fee twice per round trip on notional, so
    over n trades the strategy gives up 2nf in log terms and breaks even when

        ln(1 + R) = 2·n·f          =>   f = ln(1 + R) / (2n)

    Deploying only a fraction `s` of equity scales both the edge and the fee
    paid per trade, and the measured breakeven rises by exactly 1/s. Study 001
    left this as an open question; 003 measures it.
    """
    if trades <= 0 or position_size <= 0:
        return None
    if gross_return <= -1:
        return None
    if gross_return <= 0:
        # No gross edge to consume. Cost is not what killed this one.
        return 0.0
    return math.log(1 + gross_return) / (2 * trades * position_size) * 1e4


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", help="CSV with name, gross_return, trades[, position_size]")
    ap.add_argument("--cost", type=float, default=4.404,
                    help="realised cost in bps per side (default 4.404)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    a = ap.parse_args()

    rows = []
    with open(a.table, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                gross = float(r["gross_return"])
                trades = int(float(r["trades"]))
            except (KeyError, ValueError):
                print(f"skipping unreadable row: {r}", file=sys.stderr)
                continue
            size = float(r.get("position_size") or 1.0)
            be = breakeven_bps(gross, trades, size)
            if be is None:
                verdict = "unusable"
            elif be == 0.0:
                verdict = "no gross edge"
            elif be < a.cost:
                verdict = "DEAD"
            elif be < a.cost * 2:
                verdict = "marginal"
            else:
                verdict = "survives"
            rows.append({"name": r.get("name", "?"), "gross_return": gross,
                         "trades": trades, "position_size": size,
                         "breakeven_bps": None if be is None else round(be, 3),
                         "verdict": verdict})

    if a.json:
        print(json.dumps(rows, indent=2))
        return 0

    w = max([len(r["name"]) for r in rows] + [8])
    print(f"cost basis: {a.cost:.3f} bps/side\n")
    print(f"{'strategy':{w}} {'gross':>9} {'trades':>8} {'size':>6} {'breakeven':>10}  verdict")
    for r in rows:
        be = "—" if r["breakeven_bps"] is None else f"{r['breakeven_bps']:.2f}"
        print(f"{r['name']:{w}} {r['gross_return']*100:>8.1f}% {r['trades']:>8} "
              f"{r['position_size']:>6.2f} {be:>10}  {r['verdict']}")
    dead = [r for r in rows if r["verdict"] == "DEAD"]
    print(f"\n{len(rows)} rows, {len(dead)} cannot survive {a.cost:.3f} bps/side"
          + (": " + ", ".join(r["name"] for r in dead) if dead else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
