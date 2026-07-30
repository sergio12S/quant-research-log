# 003 — Reading a published strategy table

**Question:** someone publishes a table of strategies with returns and trade
counts. Which rows are already dead at realistic cost, without re-running
anything?

**Short answer:** one line of arithmetic per row.

```
breakeven_fee = ln(1 + gross_return) / (2 × trades × position_size)
```

This is the per-side fee at which the strategy's gross edge is exactly consumed.
Below your real cost, the row is dead. It needs only numbers a published table
already reports, so it costs nothing to run on anything — including work you did
not produce and cannot re-run.

It is a **one-way test**. A row that fails is dead at the cost you named. A row
that passes has shown only that cost is not what kills it; nothing here says the
edge is real.

Figures are commission-only at 4.404 bps/side unless stated. Slippage is not
modelled, so every verdict below is optimistic — which matters most for the rows
that already fail, since they are worse still.

---

## Why this got measured

Two reasons, and the second is the reason there is a study rather than a script.

A public thread proposed a strategy registry seeded with the backtest results of
fifteen strategies, so an agent could answer "what should I use in a bear
market?". The table reported gross returns and trade counts spanning three
orders of magnitude — 4 to 13,820 — and did not say what costs were modelled.
Running the line above over it put one row, reported at +116.8% excess and a
Sharpe of 0.39, at a breakeven of **0.31 bps per side**: below any realistic
A-share cost, where commission alone is 2–3 bps before stamp duty. That is
[said in the thread](https://github.com/HKUDS/Vibe-Trading/issues/894#issuecomment-5121390817),
not behind anyone's back.

But the screen had a hole in it. [Study 001](../001-execution-costs/) derived the
identity for full-capital compounding and stated plainly that fractional
position sizing breaks it "in a direction that is not obvious in advance". Most
published tables are not full-capital. So the screen was unusable on exactly the
tables it was meant for, and the caveat could not be resolved by argument.

It could not be resolved by measurement either, because the engine used here
accepted a `position_size` field and ignored it: the same strategy returned
+83.52% at sizes 1.0, 0.5 and 0.25 alike — identical trades, identical equity
curve. Fixed in rlx 0.2.12. With the knob connected the question is one
experiment.

## Method

- **Data:** BTCUSDT 1h, 60,000 bars, 2019-09-04 → 2026-07-10, the same file
  study 001 uses.
- **Rules:** two, chosen for very different trade counts so the comparison is
  not a single accident — a 24/168 SMA crossover with a symmetric 3% bracket
  (2,021 trades) and the same crossover with no bracket (281 trades). Both are
  public domain and neither is anyone's proprietary signal.
- **Execution:** `next_open`, and `--dynamic-tp-sl false`. Same-bar execution is
  a look-ahead; the overlay adds a bracket the rules never declared.
- **Sizes:** 1.0, 0.75, 0.5, 0.2 of equity per position.
- **Measurement:** the commission is bisected over 24 iterations until the
  strategy's return crosses zero. That answers the same question as the formula
  without using it, so the agreement is not circular.

## Result

`formula` is study 001's identity with no sizing term. `measured` is bisection.

| rule | size | trades | gross | formula | measured | formula ÷ measured |
|---|---:|---:|---:|---:|---:|---:|
| SMA + 3% bracket | 1.00 | 2,021 | +83.52% | 1.502 | 1.502 | 1.0001 |
| SMA + 3% bracket | 0.75 | 2,021 | +72.40% | 1.347 | 1.796 | 0.7501 |
| SMA + 3% bracket | 0.50 | 2,021 | +52.60% | 1.046 | 2.091 | 0.5001 |
| SMA + 3% bracket | 0.20 | 2,021 | +21.85% | 0.489 | 2.444 | 0.2000 |
| SMA, no bracket | 1.00 | 281 | +468.97% | 30.937 | 30.901 | 1.0012 |
| SMA, no bracket | 0.75 | 281 | +318.47% | 25.470 | 33.916 | 0.7510 |
| SMA, no bracket | 0.50 | 281 | +184.27% | 18.590 | 37.111 | 0.5009 |
| SMA, no bracket | 0.20 | 281 | +59.17% | 8.271 | 41.224 | 0.2006 |

The last column is the finding. **The uncorrected formula divided by the
measured value equals the position size**, across two rules with a sevenfold
difference in trade count and a fifteenfold difference in gross return. So the
correction is exactly `1 / position_size`:

| | |
|---|---|
| points compared | 8 |
| corrected formula vs bisection, max error | 0.31% |
| median error | 0.12% |

Study 001's identity is the `size = 1` case.

**Which direction, and why.** Deploying less capital makes breakeven *higher*,
not lower — 1.502 bps at full size becomes 2.444 at a fifth. Halving the size
halves the edge per trade but also halves the notional the fee is charged on, so
the two do not cancel: what survives is that compounding hurts less at small
size. In the limit the per-trade edge that must cover the fee is the arithmetic
mean rather than the log mean, and by Jensen's inequality that is the larger
number. Reading the table above with the naive formula understates a
quarter-size strategy's cost tolerance by a factor of four.

## What the screen does

```
$ ./screen.py example-table.csv --cost 4.404
```

Every row is a measurement from study 001 or from `validate.py`; none was
rescaled by hand.

| strategy | gross | trades | size | breakeven | verdict |
|---|---:|---:|---:|---:|---|
| sma24/168 tp=0.5% 1h | −98.7% | 13,568 | 1.00 | 0.00 | no gross edge |
| sma24/168 tp=2% 1h | +16.8% | 3,674 | 1.00 | 0.21 | **DEAD** |
| sma24/168 tp=3% 1h | +83.5% | 2,021 | 1.00 | 1.50 | **DEAD** |
| sma24/168 tp=6% 1h | +184.9% | 786 | 1.00 | 6.66 | marginal |
| sma24/168 tp=10% 1h | +364.0% | 456 | 1.00 | 16.83 | survives |
| sma24/168 tp=4% 1D | +4.5% | 496 | 1.00 | 0.44 | **DEAD** |
| sma24/168 tp=8% 4h | +188.3% | 355 | 1.00 | 14.91 | survives |
| sma24/168 tp=3% 1h @ 20% size | +21.9% | 2,021 | 0.20 | 2.44 | **DEAD** |

Two things worth noticing. A strategy returning **+83.5% gross is dead** at a
real fee, while one returning +4.5% is dead for the same reason — the number
that decides it is the edge *per trade*, not the total. And the arithmetic
reproduces study 001's bisected breakeven column exactly, which is the internal
check that the tool is not doing something else.

## What this cannot tell you

The screen answers one question and it is easy to mistake it for a larger one.

**It does not say an edge is real.** A row that survives 300 bps may be six
lucky trades. Cost tolerance and statistical significance are unrelated, and a
table with 33 trades in it should be read with the sample size in front of you,
not the breakeven.

**It does not know what the publisher counted.** If "trades" means fills rather
than round trips, every figure is out by two. If it means rebalances of a
portfolio, the mapping to a per-side fee is not defined at all. This is the
single largest source of error and it is invisible from outside — the number to
ask for is round trips.

**It assumes the fee is proportional to notional on both sides.** Per-order
minimums, tiered schedules, maker rebates, funding and borrow all break it.
Under a per-order minimum a high-frequency row is worse than the screen says;
under maker rebates it may be better.

**Untested here:** everything in the paragraph above. The sizing correction is
measured; the rest are stated limits, not results. They are separable
experiments and this study did not run them.

## What would change this conclusion

If `formula ÷ measured` departed from `position_size` on a rule with a different
shape — one whose per-trade returns are heavily skewed, or one holding through
many bars per trade — the correction would be an artefact of these two rules
rather than a property of the arithmetic. Both rules here are long-only
crossovers on one instrument. A short-side or multi-instrument test would be the
obvious next place to look, and is not run here.

## Caveats

One instrument, one venue's worth of price history, two rules. The bisection is
over the engine's commission model, which charges a proportional fee on notional
at entry and exit separately; an engine that models cost differently will not
reproduce these numbers, and that is a property of the cost model, not of the
identity.

The screen's verdict bands — dead below your cost, "marginal" below twice it —
are a reading convention, not a measurement. The breakeven figure is the result;
the label is there to make a long table scannable.

## Reproduce

```bash
./run.sh                    # rlx-cli on PATH
./run.sh /path/to/rlx-cli
```

About 200 backtests, a couple of minutes. `results/validation.json` is the table
above and `results/run.log` is the transcript. **Needs rlx 0.2.12 or later** —
before that the engine ignored `position_size`, so every sizing produced
identical numbers and the correction this study measures could not be observed
at all.

Screen your own table:

```bash
./screen.py your-table.csv --cost 7.5
```

A CSV with `name`, `gross_return` (a fraction) and `trades`, plus an optional
`position_size`. If a number here differs from what the scripts produce, the
README is wrong — please open an issue.

**Disclosure:** I build the engine used here, and the defect that made this
study possible was one of mine. Which is exactly why it ships the data, the
commands and the measurement rather than the conclusion alone.
