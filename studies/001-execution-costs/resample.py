#!/usr/bin/env python3
"""Resample an OHLCV CSV to a longer bar. Standard library only.

Bars are grouped by floor(timestamp / seconds), so a bucket is a fixed clock
window rather than a rolling count — the same convention an exchange uses.
Incomplete trailing buckets are dropped."""
import csv, sys
from collections import OrderedDict

src, dst, seconds = sys.argv[1], sys.argv[2], int(sys.argv[3])
rows = list(csv.DictReader(open(src)))
step = int(rows[1]["timestamp"]) - int(rows[0]["timestamp"])
per_bucket = seconds // step

buckets = OrderedDict()
for r in rows:
    key = int(r["timestamp"]) // seconds * seconds
    b = buckets.setdefault(key, [])
    b.append(r)

out = []
for key, bars in buckets.items():
    if len(bars) < per_bucket:      # partial bucket at either end
        continue
    out.append({
        "timestamp": key,
        "open": bars[0]["open"],
        "high": max(float(b["high"]) for b in bars),
        "low": min(float(b["low"]) for b in bars),
        "close": bars[-1]["close"],
        "volume": sum(float(b["volume"]) for b in bars),
    })
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"{len(rows)} bars @{step}s -> {len(out)} bars @{seconds}s")
