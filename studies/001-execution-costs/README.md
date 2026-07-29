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
- **Exits:** `--dynamic-tp-sl false`. The default is `true`, which adds
  take-profit and stop-loss levels the strategy never specified — see
  "the second trap" below.
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

## The second trap: exits nobody asked for

The engine has a `--dynamic-tp-sl` flag that defaults to **true**. With it on, a
strategy that specifies no take-profit and no stop-loss is given some anyway.

Same rule, same data, the difference is only that flag:

| | trades | gross return | exits |
|---|---:|---:|---|
| `--dynamic-tp-sl true` (default) | 3,011 | +31.97% | StopLoss 1,872 · TakeProfit 892 · Signal 246 |
| `--dynamic-tp-sl false` | 281 | +566.49% | Signal 280 |

92% of the exits in the default run come from levels the strategy never
contained. The rule was "hold while the fast average is above the slow one";
what ran was that rule wrapped in a bracket the author never wrote, and the
reported return differs by a factor of eighteen.

It also explains a behaviour that looks absurd in isolation: supplying an
unreachable stop-loss *increases* returns, because an explicit level displaces
the synthesised ones and lets the strategy run as written.

The first version of this study used the default. The figures above were
re-measured with the layer off, so the table now describes the bracket the
strategy actually states. The conclusions did not change — the identity held at
a median ratio of 0.9995 across the re-run, which is the more useful result:
if it had depended on the exit mix, it was never an identity.

Whether that default is right is a product decision, not a bug report: for an
interactive session a bracket by default is defensible. For a research run it
means the number you publish is not about the strategy you wrote. State the
flag explicitly, in either direction.

## A trap this study fell into

The engine takes two strategy formats. The simple one names the bracket
`take_profit` / `stop_loss`; the graph one names it `take_profit_pct` /
`stop_loss_pct`. Unknown fields are dropped silently.

Writing `take_profit_pct` in a simple-format strategy therefore runs with **no
bracket at all**, and reports a perfectly plausible result:

| field used in the simple format | trades | gross return |
|---|---:|---:|
| `take_profit` | 281 | +566.49% |
| `take_profit_pct` | 3,011 | +31.97% |

Same rule, same data, one suffix. The first draft of this study used the wrong
name and would have published a table of a strategy that had no take-profit in
it, while claiming to measure the effect of the take-profit.

Nothing warned. This is the shape of the error that matters in backtesting: not
a crash, but a silent, plausible number.

## Reproduce

```bash
./run.sh                    # rlx-cli on PATH
./run.sh /path/to/rlx-cli
```

Roughly 400 backtests, a few minutes. `results/breakeven.json` is the table
above; `results/run.log` is the transcript. If a number here differs from what
the script produces, the README is wrong — please open an issue.

**Disclosure:** I build the engine used here. Which is exactly why the study
ships the data, the rule, the commands and its own mistake: none of it should
require taking my word for anything.
