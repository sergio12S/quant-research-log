#!/usr/bin/env python3
"""Add two simple moving averages to an OHLCV CSV. Standard library only:
the point of this study is that every number in it can be re-derived without
trusting a dependency."""
import csv, sys
from collections import deque

src, dst, fast_n, slow_n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rows = list(csv.DictReader(open(src)))
fast, slow = deque(maxlen=fast_n), deque(maxlen=slow_n)
out = []
for r in rows:
    c = float(r["close"])
    fast.append(c); slow.append(c)
    r["sma_fast"] = f"{sum(fast)/len(fast):.8f}" if len(fast) == fast_n else "0"
    r["sma_slow"] = f"{sum(slow)/len(slow):.8f}" if len(slow) == slow_n else "0"
    # 0 until both windows are full, so the rule cannot fire on a partial window
    r["warm"] = "1" if len(slow) == slow_n else "0"
    out.append(r)
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"{len(out)} bars -> {dst}")
