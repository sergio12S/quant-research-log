# 011 — A backtest tested the opposite of its stated hypothesis

**Question:** can a backtest be mechanically reproducible and still answer the
wrong research question?

**Short answer:** yes. A real Idea Map audit found a pre-event precursor whose
execution direction had been borrowed from the post-event response. The run was
retained as an invalid test, not interpreted as evidence. The synthetic fixture
here makes the interval mismatch explicit.

Figures charge commission of 4.404 bps/side. They are synthetic and demonstrate
label semantics, not an investable effect.

---

## Why this got measured

An event study often contains at least three clocks:

1. the feature window;
2. the outcome interval used to assign a label;
3. the interval in which the backtest actually holds a position.

If a bullish rebound after an event assigns direction to a pattern that ends
before the event, entering long before the event does not test the rebound. It
trades into the event that the pattern was supposed to predict.

## Method

`audit.py` generates 400 deterministic synthetic events. Each has a negative
impulse averaging -2% followed by a positive response averaging +0.7%.

The stated precursor hypothesis is bearish from before the impulse through the
impulse. The invalid run instead takes the later bullish-response label and
applies it as a long position over the earlier interval. The audit checks the
feature, label, target, execution interval, and direction as separate contract
fields before calculating any metrics.

## Result

The contract check finds two independent mismatches:

- execution direction contradicts hypothesis direction;
- the direction label comes from a different interval.

| Run | Events | Mean net result | 95% bootstrap CI |
|---|---:|---:|---:|
| Invalid long before impulse | 400 | -217.51 bps | [-225.23, -209.62] |
| Corrected short before impulse | 400 | +199.89 bps | [+192.41, +207.45] |
| Separate post-event long | 400 | +61.46 bps | [+55.41, +67.14] |

The corrected and post-event rows are not competing strategies. They are two
different hypotheses over two different intervals. That distinction is the
finding.

## What would change this conclusion

The original idea can be tested only after freezing a contract in which feature
window, target interval, execution interval, and direction agree. Its corrected
version then needs a genuinely untouched sample. Metrics from the invalid run
must remain quarantined.

## Caveats

The public data is synthetic and deliberately gives the intervals different
signs so the bug is visible. It establishes the semantic failure mode, not its
frequency in real research. The historical invalid run's performance is omitted
because it does not measure either corrected hypothesis.

## Reproduce

```bash
./run.sh
```

The standard-library runner regenerates the fixture, audit verdict, and all
table values with fixed random and bootstrap seeds.
