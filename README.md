# Quant research log

A public record of systematic-trading research: what was tested, what died, and
what killed it. Mostly negative results, because most results are negative.

Nothing here is a signal service and nothing here is an invitation to copy a
strategy. The value, if there is any, is in the screens — the tests that a
candidate has to survive, and the order they should be applied in.

**Disclosure:** I build [RLXBT](https://rlxbt.com), the backtesting engine used
for this work. Every study states the commands it was produced with so the
result does not depend on trusting either the engine or me.

---

## Why this exists

Published backtests are, correctly, met with suspicion. The reasonable default
assumption about a strategy with a good equity curve is that it is overfit,
survivorship-biased, or costed at zero. I share that assumption about other
people's results and I have no way to argue you out of it about mine.

So this log does not try. It publishes the process instead of the outcome:
the screens, the rejections, and the exact figures at real execution cost.
A reader who disagrees with a conclusion can re-run it and say so.

## What the record currently says

No strategy in this project beats buy-and-hold. The one construction that
achieved genuine market neutrality earns a fraction of a percent per year once
a single exceptional year is removed. That is the honest summary, and it has
not changed in the direction I hoped.

The useful part is *why* each thing died, because the binding constraint moved
three times, and knowing which constraint binds is worth more than any
individual result.

## Studies

| # | Study | Finding |
|---|---|---|
| [001](studies/001-execution-costs/) | What sets tolerance for execution cost | A strategy's breakeven fee is `ln(1+gross_return) / (2 × trades)`. Take-profit and timeframe matter only through those two numbers — so "use a higher timeframe" is not advice, and you never need to search for a breakeven fee. |

Each study directory contains the question, the method, the figures, the
caveats, and a `run.sh` that reproduces them from data bundled in the repo.
If a study's `run.sh` does not reproduce its own numbers, that is a bug and an
issue is welcome.

## Reproducing

```bash
git clone https://github.com/sergio12S/quant-research-log
cd quant-research-log/studies/001-execution-costs
./run.sh
```

The bundled datasets are small on purpose — enough to reproduce the studies,
not enough to do your own research with. Bring your own data for that; the
engine loads any OHLCV CSV by path.

## What is deliberately not here

- Anything currently traded with real money.
- The feature set and universe selection that constitute whatever edge exists.
- Live execution code, positions, or account state.

This is a curated extract from a private working repository. The flow is one
way, by hand, and a commit hook refuses anything matching the private
project's internal markers. See [PORTING.md](PORTING.md).

## Conventions

Figures are **commission-only** unless stated. Slippage is not modelled, so
every number here is optimistic — which matters most for the results that look
worst, since they are worse still.

Costs are quoted as **basis points per side**. The live cost used throughout is
4.404 bps/side; where a study uses a different figure it says so in the first
paragraph.
