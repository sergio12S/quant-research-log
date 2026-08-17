# 007 — A bullish impulse did not become support on first revisit

**Question:** after an unusually large bullish candle, does the candle's open
act as support when price first returns to it?

**Short answer:** not under this fixed definition. On the untouched final
period, the range-only version lost **11.37 bps per event** after commission;
requiring elevated volume still lost **11.02 bps**. Both 95% bootstrap
intervals were entirely below zero.

Figures are commission-only at **4.404 bps/side**. Spread and slippage are not
modelled, so the economic result is optimistic.

---

## Why this got measured

"The origin of an impulse becomes support" is a common price-action story. It
has an attractive chart explanation but several degrees of freedom: what counts
as an impulse, which level is the origin, how long a revisit remains valid, and
whether volume confirmation matters. This test freezes one reasonable version
before looking at the final period.

## Method

The bundled dataset contains 60,000 BTCUSDT one-hour bars from 2019-09-04
through 2026-07-10. It is split chronologically 60/20/20 into discovery,
validation, and final periods.

A bullish impulse must have:

- range at least 2.0 times the prior 20-bar median range;
- bullish body at least 60% of its range;
- close in the top 20% of the bar;
- optionally, volume at least 1.5 times its prior 20-bar median.

The candidate support level is the impulse open, with a 0.1 ATR touch
tolerance. The first revisit must occur at least three and no more than 500 bars
later. Entry is the next bar's open. Symmetric target and stop are 0.5 ATR away,
with a 12-bar maximum hold. A bar touching both is counted as a stop. Duplicate
entry bars are removed.

## Result

| Variant | Period | Events | Mean net EV | 95% bootstrap CI |
|---|---|---:|---:|---:|
| Range only | Discovery | 497 | -13.78 bps | [-18.47, -9.03] |
| Range only | Validation | 237 | -16.04 bps | [-20.89, -11.19] |
| Range only | **Final** | **205** | **-11.37 bps** | **[-16.01, -6.35]** |
| Range + volume | Discovery | 438 | -13.38 bps | [-18.40, -8.20] |
| Range + volume | Validation | 209 | -17.75 bps | [-22.95, -12.42] |
| Range + volume | **Final** | **183** | **-11.02 bps** | **[-16.15, -5.69]** |

The volume filter reduced the number of events but did not change the economic
conclusion. In the final range-plus-volume sample, the upper barrier was reached
first in 81 of 183 events; the lower barrier was reached first in 102.

## What would change this conclusion

A different causal definition could be useful, but it must be preregistered and
tested on a new untouched period. A context filter would need to survive its own
chronological split and remain positive after spread and slippage; selecting it
against this final period would not reopen the idea.

## Caveats

This is one instrument, one timeframe, one support level, and one symmetric
barrier geometry. The first-touch search can span hundreds of hours, so it tests
a persistent horizontal level rather than a short-lived microstructure effect.
Commission is included but spread, slippage, funding, and market impact are not.

## Reproduce

```bash
./run.sh
```

The runner uses the public dataset already bundled with study 001 and only the
Python standard library. It rebuilds `results/summary.json` and
`results/summary.txt`; the bootstrap seed and all parameters are fixed in the
source.
