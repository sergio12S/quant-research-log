# 008 — An ordered state chain did not add reliable breakout information

**Question:** does the ordered chain `volume expansion → buy pressure → failed
breakout` identify a better short than the failed breakout alone?

**Short answer:** no reliable incremental effect was established. The ordered
chain lost money in discovery and validation. Its untouched final point estimate
was **+3.47 bps/event**, but the 95% bootstrap interval was **[-14.92, +22.09]**
and its improvement over failure-only events was also unresolved:
**[-16.82, +36.39] bps**.

Figures are commission-only at **4.404 bps/side**. Spread and slippage are not
modelled.

---

## Why this got measured

State-sequence explanations are more persuasive than single-indicator stories:
participation expands, buyers take control, and then the breakout fails. But a
story with three states also has more ways to select an attractive history. The
relevant question is not whether the chain sometimes works; it is whether its
ordering adds information beyond the final failed-breakout state.

## Method

The same 60,000 BTCUSDT one-hour bars used by study 007 are split
chronologically 60/20/20.

The fixed states are:

- **volume expansion:** volume above the 80th percentile of the previous 168
  bars;
- **buy pressure:** bullish body at least 60% of range and close in the top 20%;
- **failed breakout:** high exceeds the previous 24-bar high but the close
  returns below it.

The first two states must occur in that order within the eight bars before the
failed breakout. Reversed-order and failure-only events are retained as
controls. Events do not overlap. Entry is the next open, the position is short
for six bars, and commission is charged on both sides.

## Result

| Cohort | Period | Events | Mean net EV | 95% bootstrap CI |
|---|---|---:|---:|---:|
| Ordered | Discovery | 301 | -19.91 bps | [-42.97, +1.30] |
| Ordered | Validation | 116 | -25.49 bps | [-55.44, +3.70] |
| Ordered | **Final** | **122** | **+3.47 bps** | **[-14.92, +22.09]** |
| Failure only | Discovery | 462 | -14.83 bps | [-32.10, +1.49] |
| Failure only | Validation | 159 | -19.63 bps | [-39.86, +0.39] |
| Failure only | Final | 143 | -6.45 bps | [-25.25, +11.25] |

The final positive point estimate is reported rather than hidden, but it does
not rescue the hypothesis. It followed two negative periods, its interval
crosses zero widely, and the incremental comparison against the simpler control
also crosses zero widely.

## What would change this conclusion

A new preregistered chain would need a positive incremental interval against
the failed-breakout control, a consistent sign across chronological partitions,
and positive economics after spread and slippage. Merely adding more states or
searching a different window against this final period would increase selection
risk rather than evidence.

## Caveats

This is one instrument and one timeframe. The states use only public price and
volume bars; open interest, funding, order-book state, and liquidations are not
included. The six-hour fixed hold is one economic interpretation of the chain,
not the only possible exit policy.

## Reproduce

```bash
./run.sh
```

The runner uses the dataset bundled with study 001 and only the Python standard
library. It rebuilds `results/summary.json` and `results/summary.txt` with fixed
bootstrap seeds.
