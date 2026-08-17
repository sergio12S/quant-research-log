# 006 — Four plausible trading ideas that failed after costs

**Question:** what survives when four statistically plausible crypto signals
are evaluated on chronological holdouts, charged realistic costs, and checked
across time or assets?

**Short answer:** none of them. All four had negative final net expectancy. The
least bad lost **4.19 bps per trade** and the worst lost **21.71 bps per
trade**.

The original experiments charged commission, spread, and slippage for a total
round trip of 11.81 bps where applicable. This study is a synthesis of their
frozen final evidence, not a claim that their different horizons can be pooled.

---

## Why this got measured

Research archives naturally retain winners and forget failures. That makes
classification lift, a slightly higher ROC-AUC, or an improvement over a losing
baseline look more useful than it is. These four experiments failed for four
different reasons, so together they form a compact set of warnings.

## Method

Each source experiment used chronological separation, next-open decisions,
validation-only threshold selection, non-overlapping labels where applicable,
and an untouched final evaluation. The public `evidence.csv` contains only the
frozen headline and final metrics needed to rebuild the table below. It omits
private features, event timestamps, and live strategy parameters.

## Result

| Experiment | What initially looked promising | Final evidence | Decision |
|---|---|---|---|
| Selective ML | UP precision **66.21%** | **-9.19 bps/trade**; 2/5 positive walk-forward windows | Classification lift did not survive costs |
| Order-book magnitude gate | ROC-AUC improved by **0.027** | **-21.71 bps/trade**; 0/17 assets positive | Magnitude information did not supply direction |
| Lagged macro regime | Improved net EV by **4.26 bps** | Still **-4.19 bps/trade**; 1/3 positive windows | A smaller loss was still a loss |
| Bitcoin network state | Direction ROC-AUC changed by **-0.0136** | **-6.50 bps/trade**; 0/3 positive windows | Daily state was too slow for four-hour timing |

The reusable boundaries are:

- precision is not expectancy;
- movement magnitude is not direction;
- improvement over a bad baseline is not an edge;
- relevant data can operate at the wrong clock speed.

## What would change this conclusion

A new untouched period with positive net expectancy could reopen an individual
idea. The order-book case additionally needs a directional mechanism; the
network-state case needs historical data at a cadence appropriate to the
decision horizon. Retuning the same final sample would not count.

## Caveats

This is a synthesis, so `run.sh` verifies and formats the frozen evidence rather
than rerunning four private research pipelines. The experiments used different
assets and horizons, and their effect sizes must not be averaged. The package is
useful as a failure map, not as a benchmark leaderboard.

## Reproduce

```bash
./run.sh
```

The command rebuilds `results/summary.json` and `results/summary.txt` from
`evidence.csv` using only the Python standard library.
