# 001 — Execution cost is the binding constraint

**Question:** at what point does the fee, rather than the signal, decide whether
a strategy works?

**Short answer:** below roughly a 1.6% take-profit, it always does — and ranking
candidates by return actively selects the ones that will fail once cost is
applied.

Figures are commission-only at **4.404 bps/side** unless stated. Slippage is not
modelled, so everything here is optimistic.

---

## Why this got measured at all

An audit of 147 archived backtest reports found every one of them had been run
frictionless. All nine strategies that had been promoted on the strength of
those reports go negative at real cost.

That is a boring failure and an extremely common one. What was not obvious —
and is the actual finding — is that the damage is not uniform. It is a function
of the take-profit distance, and it is large enough to invert the ranking.

## Law 1 — breakeven scales with the take-profit, not with the timeframe

One rule, four timeframes, take-profit scaled with the timeframe. The measured
quantity is **breakeven fee**: the per-side cost at which the strategy's gross
edge is exactly consumed.

| Timeframe | Take-profit | Trades | Breakeven | vs. 4.404 bps real cost |
|---|---:|---:|---:|---|
| 5m | 0.5% | 5,359 | 0.30 bps | 15× short — dead |
| 1h | 3% | 1,040 | 8.17 bps | 1.86× margin |
| 4h | 6% | 331 | 16.99 bps | 3.86× margin |
| 1D | 10% | 59 | 39.98 bps | 9.08× margin |

That is roughly **2.7–4.0 bps of breakeven per 1% of take-profit**, which puts
the minimum viable take-profit at about **1.63%** at this cost level.

The corollary is the part people get wrong: moving to a higher timeframe does
nothing on its own. The same rule at 4h with a 3% take-profit breaks even at
1.64 bps — *worse* than the 1h version at the same 3%. It is the take-profit
that carries the relationship, and the timeframe only matters because it is
usually changed alongside it.

A 5m scalper at 0.5% take-profit is about 3× below the minimum. No amount of
signal work fixes that; the arithmetic is upstream of the strategy.

## Law 2 — ranking by return inverts the true ordering

This is the finding worth the most and it cost the most to learn.

Ranked by reported (frictionless) return, the best candidate in one sweep was a
four-leg combination showing **+308%**. At real cost it returns **−80.84%** — the
single worst result in the set.

The strategies that showed a modest **+19–29%** were the only ones that survived
contact with real fees.

The mechanism is not subtle once stated: return rewards trade count, and trade
count is exactly what cost punishes. Ranking by return is therefore a filter
that *prefers* the strategies most exposed to the thing you have not yet
measured.

Breakeven fee does not have this problem, and it has a second useful property:
it is scale-invariant, so position sizing cannot distort it.

**Rank by breakeven fee. Report return; never sort on it.**

## The screens, in order

Each of these was added because a false positive escaped the previous set.
Order matters — applying them in this sequence kills candidates cheaply.

1. **Return** — reported, never ranked on.
2. **Breakeven fee** exceeds real cost, with margin.
3. **Annualised return beats buy-and-hold** over the same window. In this
   market that bar is roughly 30%/yr, which is brutal and is supposed to be.
4. **Per-year market correlation** is low, and most individual years are
   positive.

Screen 3 is the one that removes the most work. A directional strategy that
returns +1.7%/yr against a +30%/yr buy-and-hold is not a weak strategy, it is
market beta with extra steps and worse tax treatment.

Expect this set to still be incomplete.

## Caveats worth stating plainly

- **Commission only.** Slippage is not modelled here. In the engine used,
  slippage is specified in absolute currency rather than as a fraction, which is
  an easy thing to configure wrongly by four orders of magnitude — and a wrong
  slippage figure fails silently, in the flattering direction.
- **Selection effect.** The survivors of the audit were picked from 39
  real-cost trials. At a one-sided 5% bar, roughly two positives are expected by
  chance alone. Surviving this screen is necessary, not sufficient; walk-forward
  at real cost is the next gate and nothing here has passed it yet.
- **One rule, one market.** The breakeven-vs-take-profit relationship was
  measured on a single rule on BTC. The mechanism should generalise; the
  coefficients should not be assumed to.

## Reproduce

> **Status: not yet reproducible.** The bundled dataset and `run.sh` are being
> prepared. Until `./run.sh` regenerates the table above, treat these figures as
> a claim rather than as evidence — which is precisely the standard this
> repository asks of everyone else.

```bash
./run.sh
```
