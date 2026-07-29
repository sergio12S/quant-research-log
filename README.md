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

Four engine defects were found by writing these studies, all of the kind that
report a plausible number rather than failing: a backtest was being given exit
levels the strategy never specified; a risk bracket spelled in the wrong
format's field names was dropped in silence; a declared bracket was reaching only
about half of fills under the one execution setting that is not a look-ahead; and
one of the two strategy formats could not express a percentage bracket at all, so
it parsed the risk control and threw it away. Fixed in rlx 0.2.9, 0.2.10 and
0.2.11 respectively, each with regression tests. The studies say what each was,
what it cost, and what the figures looked like before and after.

That is the argument for publishing research rather than only shipping a tool:
a silent failure is one you only meet by using the thing. Study 002 turns them
into six probes you can run against any engine, including mine — where the sixth
was written *because* the other five had gone green while a defect sat in the
half of the engine none of them exercised. It still fails on 0.2.10, the release
that was current when it was written, and the run is in the repo.

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
| [002](studies/002-silent-failures/) | Six probes for a backtest that lies quietly | Ask the engine questions whose answers you already know. Six trivial checks that between them caught four real defects — costs not applied, exits invented, a declared bracket missing from half the fills, a bracket one input format silently discarded, and a validator that accepts `{}`. Runs against any engine; reports FAIL on my own release. |
| [001](studies/001-execution-costs/) | What sets tolerance for execution cost | A strategy's breakeven fee is `ln(1+gross_return) / (2 × trades)`. Take-profit and timeframe matter only through those two numbers — so "use a higher timeframe" is not advice, and you never need to search for a breakeven fee. |

Each study directory contains the question, the method, the figures, the
caveats, and a `run.sh` that reproduces them from data bundled in the repo.
If a study's `run.sh` does not reproduce its own numbers, that is a bug and an
issue is welcome.

## Reproducing

The engine is public two ways: the macOS app from [rlxbt.com](https://rlxbt.com),
and the headless server image `ghcr.io/sergio12s/rlxbt-server` with the compose
file at
[rlxbt.com/downloads](https://rlxbt.com/downloads/rlxbt-server-compose.yml).

**Use 0.2.11 or later.** Two settings these studies depend on — the signal
execution timing, and whether a synthetic take-profit and stop-loss are overlaid
on strategies that declare none — reached the HTTP API only in 0.2.10. Before
that they were flags on a binary that is not published, which meant nobody but
me could re-derive these tables. Now `POST /api/load-data` takes both:

```json
{
  "path": "/var/lib/rlxbt/datasets/btc_1h_feat.csv",
  "commission": 0.0,
  "signal_execution_timing": "next_open",
  "dynamic_tp_sl": false
}
```

Those are the settings every study here uses, and the defaults are not them:
execution defaults to same-bar, which lets a signal trade on the bar that
produced it.

Earlier engines will also produce different numbers for a second reason: up to
0.2.9 roughly half of these trades ran with no take-profit or stop-loss at all
despite the strategy declaring both. Study 001 explains what that was.

Both studies write their strategies in the graph format (`entry_rules`, with
`take_profit_pct`), which is why their tables are unaffected by the 0.2.11
defect: on 0.2.10 and earlier, the *simple* format silently discarded a
percentage bracket. Study 001's table reproduces byte-for-byte on 0.2.11. If you
port either study to the simple format, use 0.2.11.

```bash
git clone https://github.com/sergio12S/quant-research-log
cd quant-research-log/studies/001-execution-costs
./run.sh /path/to/engine
```

The bundled runners drive the engine binary. Against the server image the same
experiment is a `load-data` call per cost level and a `run-backtest` per
strategy — the study states every parameter it sets, so porting it is
mechanical.

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
