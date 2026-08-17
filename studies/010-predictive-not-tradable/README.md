# 010 — A predictive feature was not automatically a tradable rule

**Question:** when a strict nonlinear validator identifies a feature as
predictive, how often does a simple quantile-threshold strategy preserve that
evidence after economic testing?

**Short answer:** four of five leads failed the bounded threshold-conversion
step. The strongest raw candidate scored **0.668**, yet its strategy probe had
Sharpe **0.168**. The one conversion required structural re-encoding rather
than another threshold on the original feature.

The public candidates are anonymized. This protects the private feature set
while preserving the workflow result.

---

## Why this got measured

Feature research often stops at information coefficient, predictive loss, or
fold stability. Trading needs a second bridge: a causal action rule, turnover,
costs, payoff asymmetry, and robustness. Without that bridge, "predictive" is
too easily read as "tradable".

## Method

Five leads passed a strict raw nonlinear or regime-sensitive screen. Conversion
was deliberately bounded: one or two preregistered quantile-threshold attempts,
followed by an economic strategy probe. A lead was not rescued by searching
thresholds until one worked.

`evidence.csv` contains anonymized raw scores and strategy-probe outcomes. A
conversion pass means only that a usable rule representation was found; it does
not mean the rule is permanent alpha.

## Result

| Candidate | Raw score | Probe Sharpe | Simple threshold conversion |
|---|---:|---:|---:|
| A | 0.668 | +0.168 | Fail |
| B | 0.341 | -0.690 | Fail |
| C | 0.346 | +0.190 | Fail |
| D | not retained | +0.130 | Fail |
| E | not comparable | not comparable | Pass after structural re-encoding |

The observed simple-threshold failure fraction was **4/5 (80%)**. Its 95%
Wilson interval is **[37.55%, 96.38%]**, which is intentionally wide: five leads
are enough to reject automatic promotion, not enough to estimate a universal
conversion rate.

## What would change this conclusion

A frozen economic probe that passes costs and chronological validation can
promote an individual feature. A multivariate model may also extract information
that no one-dimensional threshold can express, but it must be preregistered
before final evaluation.

## Caveats

Only five leads. Candidate identities, datasets, and exact thresholds remain
private. Failure of a simple threshold does not disprove multivariate or
regime-conditional usefulness. Conversely, a conversion pass is only the start
of robustness testing.

## Reproduce

```bash
./run.sh
```

The standard-library runner rebuilds the conversion table and Wilson interval
from `evidence.csv`.
