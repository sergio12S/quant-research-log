# 005 — Ranking candidates by the number that cannot be gamed

**Question:** you have ninety-six backtests and have to decide which few are
worth another day. Rank them how?

**Short answer:** not by return, once the candidates differ structurally. On a
grid of one rule with a swept take-profit, return and breakeven fee rank almost
identically — Spearman +0.91, four of the top five shared. Add rules with
genuinely different turnover and it falls apart: Spearman +0.61, **one of five**
shared, and the highest-returning candidate on the whole grid is dead at real
cost.

That candidate returns **+725.59% gross** over 3,514 trades and breaks even at
**3.00 bps per side**, against a live cost of 4.404. Ranked first by return,
rejected by the screen.

Costs are 4.404 bps/side throughout. Slippage is not modelled, so every figure
is optimistic.

---

## Why this got measured

This log's private counterpart keeps an idea map: fifty candidate ideas, each
with a status and the evidence that put it there. Thirty-five are `rejected`,
one is `robust`, none is `promising`. Its first working rule reads:

> Rank by breakeven fee, then buy-and-hold, then market correlation. **Never by
> return.** It inverted the true ordering here.

That is a strong claim resting on one private grid, which is exactly the kind of
claim that ought to be re-run somewhere a reader can check. So: same question,
public data, published script.

The screens themselves came from failure, not from theory. Each was added after
a candidate passed everything before it and then died anyway — which is the
honest way a screen gets built and the reason a list of them is worth more than
any individual result.

## Method

- **Data:** BTCUSDT 1h, 60,000 bars, 2019-09-04 → 2026-07-10, plus 4h and 1D
  resampled from it. Bundled with study 001.
- **Candidates:** four entry rules × eight take-profits × three timeframes = 96.
  The rules are deliberately structurally different, not one family with a
  parameter swept — `trend` (24/168 SMA crossover), `fast` (close above the fast
  average), `slow` (close above the slow one), `narrow` (trend plus an up bar).
  Turnover across them spans 175 to 3,784 trades.
- **A grid, not a search.** Every cell is reported. Nothing is selected on its
  own result, because selection is the failure this study is about.
- **Execution:** `next_open` and no synthetic bracket. Both engine defaults
  flatter; study 001 measures by how much.
- **Costs applied analytically.** Each backtest is run frictionless once, and
  the breakeven fee comes from `ln(1 + gross_return) / (2 × trades)` — derived
  and validated against bisection in study 001, generalised to fractional sizing
  in study 003.

## Result

96 candidates, 55 with any gross edge, 27 surviving 4.404 bps/side.

**Ranked by return** — the first column is what a naive sweep promotes:

| candidate | gross | trades | breakeven | at real cost |
|---|---:|---:|---:|---|
| `fast tp=10% 1h` | +725.59% | 3,514 | 3.00 bps | **dead** |
| `slow tp=10% 1h` | +650.94% | 1,219 | 8.27 bps | survives |
| `slow tp=10% 4h` | +577.59% | 399 | 23.98 bps | survives |
| `slow tp=8% 1D` | +548.36% | 236 | 39.60 bps | survives |
| `fast tp=6% 1h` | +545.10% | 3,784 | 2.46 bps | **dead** |

**Ranked by breakeven fee:**

| candidate | gross | trades | breakeven |
|---|---:|---:|---:|
| `slow tp=8% 1D` | +548.36% | 236 | 39.60 bps |
| `slow tp=10% 1D` | +291.71% | 175 | 39.01 bps |
| `trend tp=8% 1D` | +480.71% | 230 | 38.24 bps |
| `trend tp=10% 1D` | +199.57% | 175 | 31.35 bps |
| `fast tp=8% 1D` | +470.00% | 303 | 28.72 bps |

One name in common. Two of the return-ranked top five cannot survive the cost
they would actually pay, and the second-best candidate by breakeven returns
+291.71% — less than half the leader's gross, and about thirteen times its cost
tolerance.

### When return-ranking is safe, and when it is not

The claim as originally written — "never rank by return" — is too strong, and
the grid says where the line is.

| grid | Spearman(return, breakeven) | top-5 shared | return-leaders dead at cost |
|---|---:|---:|---:|
| one rule, take-profit swept | **+0.9107** | 4 of 5 | 0 |
| four structurally different rules | **+0.6120** | 1 of 5 | 2 |

Within one family, return and breakeven rank nearly the same thing, because
widening the take-profit raises the edge per trade and cuts the trade count
together. Nothing is gained by switching metric and nothing is lost.

Across candidates that differ in *turnover structure*, they measure different
things, and return measures the wrong one. That is the situation any real
research programme is in: you are not comparing one rule against itself, you are
comparing a fast rule against a slow one.

The mechanism is not subtle once seen. `fast tp=10% 1h` earns its 725% over
3,514 trades — 0.058% of gross log edge per trade. `slow tp=8% 1D` earns 548%
over 236 trades — 0.79% per trade, thirteen times more. A fee is charged per
trade, so the second can pay thirteen times more of it. Total return says
nothing about that ratio, and ranking on it is ranking on the numerator alone.

## The screens, and the failure that produced each

The order matters: each is cheap relative to the one after it, and each was
added because something passed the previous set.

1. **Return** — reported, never ranked on. Added first because it is what a
   sweep sorts by, and the table above is what that costs.
2. **Breakeven fee** > realised cost, with margin. Scale-invariant, so position
   sizing cannot flatter it. See studies 001 and 003 for the derivation and for
   the case where it does not apply: a strategy of several independently
   capitalised sleeves cannot be screened this way at all.
3. **Beats buy-and-hold** on the same window, risk-adjusted. Added after a
   candidate cleared cost and turned out to be market beta — it made money
   because the market did.
4. **Per-year market correlation low, and most years positive.** Added after a
   candidate cleared all three above and had its entire result come from a
   single exceptional year.

Screen 4 is worth expanding because it is the one people skip. A construction
that reaches genuine market neutrality — portfolio returns correlating −0.056
with the benchmark, where every directional candidate measured between −0.64 and
+0.82 — still earned **+0.40%/yr** once one year was removed. That year
contributed 87% of the total.

And the diversification was not what it looked like. Twelve spread strategies,
ten of them positive, sounds like ten independent confirmations. Average
pairwise correlation between them was **+0.383**, so effective breadth is

```
n / (1 + (n−1)ρ)  =  12 / (1 + 11×0.383)  =  2.30
```

Ten of twelve positive is one event seen ten times. The binding constraint was
never the entry threshold.

## What would change this conclusion

A grid where breakeven-ranking promotes candidates that later fail
out-of-sample while return-ranking promotes ones that survive. Nothing here
tests out-of-sample survival at all — these are in-sample gross figures, and the
screens are a *cheap filter applied before* the expensive test, not a substitute
for it. A candidate that passes all four has earned a walk-forward run, not a
conclusion.

The clearest way to falsify the ordering claim specifically: run the same 96
candidates through walk-forward validation at real cost and check whether the
breakeven-ranked top five survives more often than the return-ranked one. That
is a much larger experiment and is not run here.

## Caveats

One instrument, one direction, four rule shapes. Long-only; a short or
market-neutral book has doubled cost per fill and a different benchmark, which
moves every threshold.

The four screens are stated as a sequence that worked on one programme. Their
*order* is a claim about relative cost, not about importance, and the set is
certainly incomplete — every one of them was added after something got past its
predecessors, and there is no reason to think that process has finished.

The private figures quoted in screen 4 — the −0.056 correlation, the +0.383
pairwise, the 87% single-year concentration — come from a working repository
that is not public. They are reported as the reason a screen exists, not as a
result you can reproduce here. Everything in the tables above is reproducible.

## Reproduce

```bash
./run.sh                    # rlx-cli on PATH
./run.sh /path/to/rlx-cli
```

96 frictionless backtests, a couple of minutes. `results/screens.json` holds
every cell plus both rankings. Needs rlx 0.2.12 or later.

The screens themselves need no particular engine — breakeven is arithmetic on
two numbers every backtester reports, and the other three are comparisons
against a benchmark you already have. `screens.py` drives one engine because it
has to drive something; the method transfers by rewriting one function.

If a number here differs from what the script produces, the README is wrong —
please open an issue.
