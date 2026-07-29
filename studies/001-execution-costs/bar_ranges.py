#!/usr/bin/env python3
"""Median and 90th-percentile bar range per timeframe.

Needed to interpret a take-profit distance: a 0.5% target on a bar whose median
range is 3.7% is not a target, it is a coin flip resolved by whatever the engine
assumes about the order of prices inside the bar.
"""
import csv
import statistics

for name, path in [("1h", "data/btc_1h.csv"), ("4h", "data/btc_4h.csv"), ("1D", "data/btc_1d.csv")]:
    rows = list(csv.DictReader(open(path)))
    rng = [
        (float(r["high"]) - float(r["low"])) / float(r["open"])
        for r in rows
        if float(r["open"]) > 0
    ]
    med = statistics.median(rng)
    p90 = sorted(rng)[int(len(rng) * 0.9)]
    print(f"{name:>3}  bars {len(rows):6d}  median range {med*100:6.2f}%   p90 {p90*100:6.2f}%")
