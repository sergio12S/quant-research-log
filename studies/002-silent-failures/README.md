# 002 — Five probes for a backtest that lies quietly

**Question:** how do you find out whether your backtester is measuring the
strategy you wrote?

**Answer:** ask it questions whose answers you already know. All five probes
here are trivial. Between them they would have caught three real defects found
in a single afternoon, each of which produced a plausible backtest of a
strategy nobody had written.

The failure mode that matters in backtesting is not a crash. A crash is free —
you see it, you fix it. The expensive one is a number: correctly formatted,
plausibly sized, and about something else.

---

## The probes

| # | Probe | What it catches |
|---|---|---|
| 1 | Costs are applied | A fee parameter that never reaches the fill |
| 2 | No exits are invented | The engine adding a take-profit or stop-loss you did not declare |
| 3 | No trade escapes the declared bracket | A bracket that reaches some fills and not others |
| 4 | Execution timing | A default that lets a signal trade on the bar that produced it |
| 5 | The validator validates | A pre-flight check that accepts `{}` |

Run them:

```bash
./probe.py /path/to/rlx-cli data/btc_1h_feat.csv
```

Each prints PASS, FAIL or INFO with the numbers behind it, and the run is
written to `results/probes.json`. Exit code is non-zero if anything failed, so
it works in CI.

## Why each one exists

### 1. Costs are applied

Run the same strategy at zero fees and at an absurd fee. If the two agree, the
fee is not reaching the fill.

This sounds too dumb to be worth writing. It is the check that would have saved
a project in which **147 archived reports had been run frictionless** and all
nine strategies promoted on their strength went negative once real costs were
applied. Nothing failed at the time; the reports looked fine.

### 2. No exits are invented

Declare a strategy with no take-profit and no stop-loss. Then count how many
trades exited on one.

An engine was giving every position a bracket built from the range of its entry
bar, on by default. **92% of exits belonged to levels the strategy never
contained**, and the reported return differed by a factor of eighteen from the
same rule run honestly. The strategy was "hold while the fast average is above
the slow one"; what ran was that rule wrapped in someone else's risk management.

### 3. No trade escapes the declared bracket

Declare a bracket, then check the **worst** trade against it.

Two things had to be got right here, and both were got wrong first.

Counting *exit reasons* is not enough: a rule exit can legitimately close a
trade before its bracket fires, so a low "exited on the bracket" share proves
nothing. And counting the *share* of trades that overshoot is not enough
either — a bracket is a guarantee about the worst case, so the worst case is
the statistic. One unexplained violation means the bound was not enforced,
however rare it is.

With that rule the probe separates the two builds cleanly:

| | worst trade against a 1% bracket | trades over 2× |
|---|---|---|
| released engine | **6.50%** (6.50×) | 131 of 9,039 |
| with the pending fix | 1.00% (1.00×) | 0 of 8,515 |

The defect behind the 6.50%: under `next_open` execution, roughly half of
trades were opening with no bracket at all, because the component deciding
signals filled a bar earlier than the engine and the two drifted apart. It was
invisible under the default execution timing — **choosing the methodologically
correct setting was what exposed it.**

### 4. Execution timing

Not a pass/fail, a number to look at. Compare executing on the signal bar's
close against the next bar's open. The first lets a strategy act on information
it did not have yet.

A large positive gap means the default is flattering you. A small one, as here,
means this particular strategy does not depend on the difference — which is
worth knowing before you argue about it.

### 5. The validator validates

Submit `{}`. Submit `{"nonsense": 42}`. If either comes back valid, the
validator is decoration, and calling it before a run tells you nothing.

An engine's validator returned `"valid"` for both, because every field of its
strategy format was optional and unknown fields were dropped in silence. The
same mechanism meant a bracket spelled in the wrong format's field names —
`take_profit_pct` where the format wanted `take_profit` — was discarded without
a word.

## Results on the engine used here

| probe | rlx 0.2.9 (released) | with the pending fix |
|---|---|---|
| costs are applied | PASS | PASS |
| no exits are invented | PASS | PASS |
| no trade escapes the declared bracket | **FAIL** (6.50×) | PASS (1.00×) |
| execution timing | INFO, +0.11 pp gap | INFO, +0.11 pp gap |
| the validator validates | PASS | PASS |

Probes 1, 2 and 5 pass on 0.2.9 because the defects they describe were fixed in
that release — each of them was a live failure a few hours earlier. Probe 3
describes one that was not, and is the reason there will be a 0.2.10.

Both runs are in `results/`, produced against binaries built from the release
commit and from the fix.

## Two mistakes worth keeping

Writing the probes was harder than writing the defects, and both errors are the
shape the probes exist to catch.

**Units.** The first version of probe 3 failed everything, including correct
runs. It compared a per-trade return against a threshold — the return in per
cent, the threshold a fraction. A factor of a hundred, and a confident,
well-formatted, entirely wrong verdict.

**Statistic.** The second version measured the *share* of trades that overshot
the bracket, and passed a build where the bracket was missing from half the
fills — those trades still closed on a rule before drifting far, so the share
stayed at 0.4%. Only the extreme exposed it: a single trade running 6.5× past
its stop.

Both are left documented in the source rather than quietly corrected. A probe
suite that has never been wrong is a probe suite nobody has tested against a
known-bad build — which is exactly why one was built here from the release
commit on purpose.

## Reproduce

```bash
./probe.py /path/to/rlx-cli data/btc_1h_feat.csv
```

`data/btc_1h_feat.csv` is generated from study 001's bundled dataset by its
`build_features.py`. Adapting the suite to another engine means rewriting one
function, `run()`, and the two strategy literals at the top. The probes
themselves assume nothing about the engine.

**Disclosure:** I build the engine these probes are demonstrated on. Which is
why they are published as a script that runs against anything, reports FAIL on
my own release, and prints the numbers rather than a verdict you have to trust.
