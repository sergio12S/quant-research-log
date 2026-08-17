# 009 — Clearing trading costs was not out-of-sample validation

**Question:** if a parameter sweep contains many strategies whose gross edge
exceeds commission, how many remain after chronological and distributional
robustness gates?

**Short answer:** none of the five leaders. In a 200-configuration sweep, 53 of
196 eligible configurations cleared the commission hurdle. The five highest
breakeven-fee candidates then produced WFE between **0.09 and 0.45** and Monte
Carlo fifth-percentile returns between **-8.34% and -2.30%**. The joint gate
passed **0/5**.

The source sweep used commission of 4.404 bps/side and zero slippage. This
public package deliberately anonymizes the entry rules.

---

## Why this got measured

Breakeven fee is a useful first screen because it asks whether an observed gross
edge can pay for execution. It is not a validation statistic. Searching enough
configurations can produce many cost survivors that capture drift or a favorable
sample without carrying stable information out of sample.

## Method

The frozen sweep contained 200 configurations; 196 met its minimum trade-count
floor. Candidates were first ranked by breakeven fee. The top five then faced
three preregistered gates:

1. walk-forward efficiency at least 0.5;
2. a strict majority of 12 non-overlapping OOS windows positive;
3. Monte Carlo fifth-percentile return above zero.

Passing means passing all three, not choosing whichever metric looks best.

## Result

| Candidate | WFE | Positive OOS windows | Monte Carlo p05 | Full gate |
|---|---:|---:|---:|---:|
| A | 0.25 | 8/12 | -2.30% | Fail |
| B | 0.45 | 8/12 | -3.75% | Fail |
| C | 0.16 | 7/12 | -4.10% | Fail |
| D | 0.12 | 7/12 | -7.29% | Fail |
| E | 0.09 | 6/12 | -8.34% | Fail |

The cost screen admitted **53/196 (27.04%)** configurations, yet robustness
admitted **0/5** leaders. Ranking by frictionless return and breakeven fee was
also nearly equivalent inside this homogeneous grid: Spearman **0.938**, with
6/10 overlap between their top tens.

At a nominal 5% threshold, 200 independent null tests would produce 10 false
winners in expectation and at least one with probability 99.9965%. That
calculation is illustrative—the grid configurations are correlated—but it
explains why a cost survivor cannot be treated as confirmation.

## What would change this conclusion

A candidate must pass all three robustness gates on a new untouched corpus and
remain distinct from benchmark drift. A heterogeneous sweep may also make
breakeven ranking more informative if strategy structures have discontinuously
different turnover.

## Caveats

One homogeneous grid, one corpus, and commission-only economics. The public
table omits private rule definitions, so it reproduces the selection audit, not
the underlying backtests. The nominal false-winner probability assumes
independence and is not used as the final decision rule.

## Reproduce

```bash
./run.sh
```

The standard-library runner rebuilds all figures from `top_candidates.csv` and
writes `results/summary.json` and `results/summary.txt`.
