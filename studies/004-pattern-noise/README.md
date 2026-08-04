# 004 — What a pattern miner finds in data that has no patterns

**Question:** an engine that mines historical price shapes will always find
*something*. How much of what survives its own filters is selection?

**Short answer:** at the discovery stage, all of it. Shuffled returns — a series
with no temporal structure by construction — produced 13 to 18 candidates
"confirmed by temporal holdout", against 17 from real BTC. The phrase carries no
information.

The promotion gate downstream is a different matter: it rejected **45 of 45**
noise candidates. That bounds its false-positive rate at roughly 6.7% (95%, rule
of three) and is a real result. It does **not** establish that the gate
discriminates: it promoted 1 of 17 real-data candidates, and 1-versus-0 at these
sample sizes gives a one-tailed Fisher p of 0.274. One promotion is what chance
looks like.

Costs are 4.404 bps/side throughout, and that matters more than usual here — see
Method.

---

## Why this got measured

Pattern mining is the most overfitting-prone thing in systematic trading, and
the engine used in this log shipped a pattern miner. The pipeline documents real
safeguards: matches are purged so a candidate and all its measured outcomes
finish before the query window begins; candidates must survive a later temporal
holdout; a materialised feature forces every row before
`feature_available_from_timestamp` to `NaN` so a selected motif cannot leak
backward into the history that chose it.

Those are the right mechanisms. Whether they are sufficient is not something the
mechanisms can tell you, and "I read the code and it looks careful" is not
evidence. The way to find out is to run the pipeline on data whose answer you
already know.

**Disclosure up front:** I build this engine. That is precisely why this study
runs the least flattering test available and reports the statistic that refuses
to support the conclusion I would have preferred.

## Method

**The null.** Take the real BTCUSDT 1h series, compute its log returns, shuffle
them, and rebuild the price path. This keeps the return distribution, the
volatility and the fat tails exactly as they were, and destroys every temporal
relationship. Intrabar ranges are shuffled and reapplied too, so the synthetic
bars are not degenerate to anything that reads highs and lows. Three seeds.

A shuffle is a stronger null than a random walk: it cannot be dismissed as
"unrealistic data". It is the same data, in a different order.

**The pipeline.** For each dataset: `POST /api/patterns/discover` with
`anchor_count: 120`, then `POST /api/patterns/experiment` on every candidate it
returns, and record the verdict. Identical settings for real and shuffled.

**Costs are load-bearing.** The first version of this test loaded data with
`commission: 0.0` and got verdicts of `needs_costs` — the pipeline refuses to
promote a frictionless result. That is the engine being right and the test being
wrong: at zero cost the gate never reaches a promote-or-reject decision, so it
measures nothing. Everything below is at 4.404 bps/side.

**Why n is what it is.** `anchor_count` is clamped to `[4, 100]` in the source,
so requesting 400 anchors evaluates the same 99 as requesting 120, and yields the
same 17 candidates. The real-data sample cannot be enlarged by turning that dial.

## Result

| dataset | anchors | holdout-confirmed | candidates | promoted |
|---|---:|---:|---:|---:|
| BTC, real | 99 | 17 | 17 | **1** |
| shuffled, seed 1 | 99 | 13 | 11 | 0 |
| shuffled, seed 2 | 99 | 16 | 16 | 0 |
| shuffled, seed 3 | 99 | 18 | 18 | 0 |

| | |
|---|---|
| real promoted | 1 / 17 |
| noise promoted | 0 / 45 |
| Fisher exact, one-tailed | p = 0.274 — **not significant** |
| 95% upper bound on noise promotion (rule of three) | **6.7%** |

## What this establishes, and what it does not

**Established: discovery output is not evidence.** Data with no temporal
structure produced holdout-confirmed candidates at the same rate as real data —
13, 16 and 18 against 17. Whatever "confirmed by temporal holdout" means, it does
not mean the shape predicts anything. Anyone reading a discovery report, from
this engine or another, should treat the candidate list as a list of things to
test, which is exactly what the endpoint's own documentation calls it. This study
is the number behind that sentence.

**Established: an upper bound on the gate's false positives.** Zero promotions
from 45 noise candidates puts the 95% upper bound at 6.7%. That is worth having.
It is not the same as zero.

**Not established: that the gate discriminates.** It promoted one real candidate
and no noise candidates, and with 17 real against 45 noise, a single promotion
landing in the real group has a 27% chance of happening by itself. The result is
consistent with a gate that discriminates and equally consistent with a gate that
promotes about 1 in 60 of anything. This study cannot separate those.

I want to be plain about the temptation here, because the headline "the miner
rejected 45 out of 45 noise patterns" is available, true, and misleading on its
own. The gate also rejected 16 of 17 real ones. A filter that rejects almost
everything will reject noise, and that is not the same as knowing the difference.

## What would change this conclusion

More real-data promotions. If the same test at other pattern geometries — a
different `query_length` or `forecast_horizon` — produced, say, 6 promotions from
real data and still none from shuffled, p would fall below 0.05 and the
discrimination claim would be supportable. That is the experiment to run next,
and it is deliberately not run here: choosing among configurations after seeing
which ones promote more is how a null test turns into its opposite. The
configuration above was fixed before any of it ran.

Conversely, a single promoted candidate from shuffled returns would falsify the
upper bound as stated and would be the more interesting result. Anyone can look:
`./nulltest.py` takes about half an hour and its seeds are in the source.

## Caveats

One instrument, one timeframe, one pattern geometry, three shuffles. The shuffle
destroys volatility clustering along with everything else, so it is a null for
"is there a predictable shape" and not for "is there a predictable shape given
the volatility regime" — a miner that exploited only volatility persistence would
be penalised by this test unfairly.

The promoted real-data candidate is not examined here and is not a
recommendation. Whether it survives out of sample is a different study; this one
is about the filter, not about the pattern.

The `needs_more_data` verdict appearing once in the noise runs is the pipeline
declining to judge rather than judging, and it is counted as not-promoted, which
is the conservative reading for the upper bound and the generous one for the
gate.

## Reproduce

```bash
# with the engine running and licensed on 127.0.0.1:8142
./nulltest.py http://127.0.0.1:8142 data/btc_1h_feat.csv
```

Roughly half an hour. `results/nulltest.json` holds the table above. The
shuffled datasets are generated from the bundled real one and deleted after each
sweep, so nothing here depends on a file you cannot rebuild.

Needs rlx 0.2.12 or later — the pattern endpoints do not exist before it.

If a number here differs from what the script produces, the README is wrong —
please open an issue.
