# 001 — What actually sets a strategy's tolerance for execution cost

**Question:** people say a strategy needs a wide enough take-profit to survive
fees, and that higher timeframes help. Both are folk wisdom. What sets the
tolerance?

**Answer:** neither, directly. The per-side fee a strategy breaks even at is

```
breakeven_fee = ln(1 + gross_return) / (2 × trades)
```

Take-profit and timeframe matter only through their effect on those two
numbers. This held to three decimal places on all 20 measurements below, across
three timeframes, which is unsurprising once written down — and is exactly why
it is worth writing down.

The practical consequence: **you never need to search for a breakeven fee.** One
frictionless backtest gives it to you in closed form, from numbers every
backtester already reports.

---

## Setup

- **Data:** BTCUSDT 1h, 60,000 bars, 2019-09-04 → 2026-07-10 (6.85 years),
  bundled in `data/`. 4h and 1D are resampled from it by `resample.py`, so no
  figure depends on two downloads agreeing.
- **Rule:** long when a 24-bar SMA is above a 168-bar SMA, flat otherwise, with
  a symmetric take-profit / stop-loss bracket. Public domain, mildly profitable
  on this data, and nobody's proprietary signal — this study is about cost
  geometry, not about finding an edge.
- **Execution:** `next_open`. The engine's default is `current_close`, which
  lets a signal trade on the bar that produced it. That is a look-ahead and it
  flatters everything.
- **Exits:** `--dynamic-tp-sl false`, so the only bracket is the one the
  strategy states. This is the default from engine 0.2.9 onward; it is passed
  explicitly anyway, both because a study should not depend on a default and
  because on 0.2.8 and earlier the default was the opposite — see "two defects
  this study walked into" below.
- **Engine:** rlx 0.2.9. `run.sh` prints the version it ran with; earlier
  versions will not reproduce the table.
- **Fees:** commission only, charged on notional at entry and exit separately.
  Slippage is **not** modelled, so every figure is optimistic.
- **Breakeven** is found by bisecting the commission over 20 iterations, *not*
  by the formula above — otherwise the agreement would be circular.

## Result

Breakeven fee in basis points per side. `0.00` means the rule has no gross edge
at that setting: cost is not what kills it.

| TP | 1h | 4h | 1D |
|---:|---:|---:|---:|
| 0.50% | 0.00 | 0.00 | 0.56 |
| 0.75% | 0.00 | 0.00 | 0.90 |
| 1.00% | 0.00 | 0.00 | 0.00 |
| 1.50% | 0.50 | 0.00 | 0.00 |
| 2.00% | 0.62 | 0.77 | 0.00 |
| 3.00% | 1.66 | 2.68 | 0.46 |
| 4.00% | 3.14 | 3.04 | 0.10 |
| 6.00% | 6.42 | 11.86 | 9.95 |
| 8.00% | 11.85 | 15.13 | 26.10 |
| 10.00% | 16.16 | 30.49 | 44.92 |

Against a real cost of 4.404 bps/side, this rule needs a take-profit of roughly
**5% on 1h** before cost stops being the thing that kills it. At 3% — a setting
that sounds conservative — it breaks even at 1.58 bps and loses money in
practice by a factor of three.

## What the table does not say

**It does not say higher timeframes help.** Read across any row: at a 3%
take-profit the daily version tolerates *less* cost than the hourly one (0.46 vs
1.58), and at 4% it is worse still (0.10 vs 3.14). The ordering flips again at
6%. Timeframe is not a dial that improves cost tolerance.

**It does not say breakeven rises smoothly with take-profit.** The 1D column is
non-monotone: 0.56 → 0.90 → 0.00 → … → 0.10 → 9.95. A law that produces that
shape is not a law.

Both readings dissolve once you look at what the fee is actually charged on.

## The mechanism

With full-capital sizing, each round trip pays the fee twice on notional, so
over `n` trades the strategy gives up `2nf` in log terms. It breaks even when
the gross log edge equals that:

```
Σ ln(1 + rᵢ) = 2nf     ⟹     f = ln(1 + R_gross) / (2n)
```

Measured against bisection on all 20 points where a gross edge exists:

| | |
|---|---|
| points compared | 20 |
| median ratio (measured ÷ formula) | 0.9995 |
| range | 0.9954 – 1.0004 |

So the quantity that matters is **gross log edge per trade**. Take-profit moves
it because widening the target raises the edge per trade and cuts the trade
count — both push breakeven up. Timeframe moves it for the same reason and with
no fixed sign, which is why "use a higher timeframe" is not advice.

This also explains the ragged 1D column. Its erratic rows are the ones with a
tiny gross edge spread over many trades: at a 4% take-profit the daily rule
returns +1.07% over 513 trades, so its per-trade edge — and therefore its cost
tolerance — is essentially zero. Nothing about the timeframe caused that.

### Why the take-profit has to be read against the bar, not in per cent

| | bars | median range | p90 range |
|---|---:|---:|---:|
| 1h | 60,000 | 0.64% | 1.64% |
| 4h | 14,986 | 1.36% | 3.31% |
| 1D | 2,483 | 3.74% | 7.93% |

A 0.5% take-profit on a daily bar sits well inside the median bar. Both the
target and the stop are reachable within a single bar, so which one fills is
decided by the engine's assumption about the order of prices inside that bar,
not by the strategy. Those rows measure a convention.

The engine used here resolves fills inside the bar with an explicit high-first
or low-first ordering rather than assuming one — but it can only do that with
intrabar data, which this study does not supply. Every figure at a take-profit
below roughly 1.5× the median bar range should be read as a lower bound on the
uncertainty, not as a measurement.

## What would change this conclusion

The identity assumes full-capital compounding and a fee proportional to notional
on both sides. Fractional position sizing, per-order minimum fees, funding, or
leverage all break it, and the direction is not obvious in advance. If you use
any of those, measure rather than assume.

## Two defects this study walked into

Writing this study took two attempts before the table described the strategy it
claimed to describe. Both causes were engine defects, both were silent, and both
are fixed in 0.2.9. They are worth reading as a pair, because they are the same
failure: not a crash, but a plausible number about the wrong thing.

### Exits nobody asked for

`--dynamic-tp-sl` defaulted to **true**. With it on, a strategy specifying no
take-profit and no stop-loss was given one anyway, built from the range of its
entry bar. Same rule, same data, that flag alone:

| | trades | gross return | exits |
|---|---:|---:|---|
| overlay on (the old default) | 3,011 | +31.97% | StopLoss 1,872 · TakeProfit 892 · Signal 246 |
| overlay off | 281 | +566.49% | Signal 280 |

**92% of the exits belonged to levels the strategy never contained**, and the
reported return differed by a factor of eighteen. The rule was "hold while the
fast average is above the slow one"; what ran was that rule wrapped in a bracket
the author never wrote.

It also explains a behaviour that reads as nonsense on its own: supplying an
*unreachable* stop-loss raised returns — because an explicit level takes a
different code path, and the synthetic one is then never applied.

The width came from `atr_multiplier * (bar.high - bar.low)` of the single entry
bar. There is no average in it, despite the name.

### A bracket lost to a suffix

The engine takes two strategy formats. The simple one names the bracket
`take_profit` / `stop_loss`; the graph one names it `take_profit_pct` /
`stop_loss_pct`. Unknown fields were dropped silently, so the wrong name meant
no bracket at all:

| field used in the simple format | trades | gross return |
|---|---:|---:|
| `take_profit` | 281 | +566.49% |
| `take_profit_pct` | 3,011 | +31.97% |

One suffix. The first draft of this study used the wrong name and would have
published a table of a strategy that had no take-profit in it, while claiming to
measure the effect of the take-profit.

The same root cause made the validator useless: every field of the simple format
was optional with no `deny_unknown_fields`, so `{}` and arbitrary JSON both
returned `"valid"`.

### What changed in 0.2.9

- The overlay is **off by default**. It remains available as
  `--dynamic-tp-sl true`, and a run that opts in now reports
  `synthetic_brackets_applied` so the result says how many positions were
  affected.
- `atr_multiplier` renamed to `range_multiplier` and documented as a fixed 2:1
  shape taken from one bar's noise.
- A payload with no entry condition, or one carrying the other format's field
  names, is now an error that names the field. Unknown fields are reported as
  warnings. The CLI and HTTP validators share one implementation and cannot
  disagree.
- Eight regression tests cover the payloads that used to validate. The one that
  matters most asserts that `{}` is not a strategy.

Both were found by using the engine for this study rather than by testing it,
which is the argument for publishing research at all: a tool you only ship is a
tool whose silent failures you never meet.

### What did not change

The conclusion. The table moved only at tight take-profits (1h 3%: 1.58 → 1.66;
4h 2%: 0.61 → 0.77) and not at all from 4% up, and the identity held at a median
ratio of 0.9995 across the re-measurement. Had it depended on which exits fired,
it was never an identity.

## Reproduce

```bash
./run.sh                    # rlx-cli on PATH
./run.sh /path/to/rlx-cli
```

Roughly 400 backtests, a few minutes. `results/breakeven.json` is the table
above; `results/run.log` is the transcript, and it begins with the engine
version it ran against. If a number here differs from what the script produces,
the README is wrong — please open an issue.

Build the engine from source:

```bash
git clone https://github.com/sergio12S/rlx-backtester
cd rlx-backtester/rlxbt
cargo build --release --bin rlx-cli --no-default-features --features offline_license
```

The table was last regenerated against **rlx 0.2.9**, byte for byte across all
30 measured points.

**Disclosure:** I build the engine used here. Which is exactly why the study
ships the data, the rule, the commands and its own mistake: none of it should
require taking my word for anything.
