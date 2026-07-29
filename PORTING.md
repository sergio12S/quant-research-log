# Porting rules

This repository is a curated extract from a private working repository that
also runs live trading. The rules below exist because the failure mode is
irreversible: a public repository is forked, archived and indexed within
minutes, and nothing is ever really deleted.

## One way, by hand

```
private working repo  →  [human reads, decides, rewrites]  →  this repository
```

No mirroring, no sync script, no symlinks, no `git remote` shared between the
two. Automation is what eventually carries something across that should not
have crossed.

`scripts/leak-guard.sh` runs as a pre-commit hook and in CI. It cannot judge
what is safe — it only blocks known markers. Passing it is not permission.

## Never ported

- **Live execution.** Executors, order routing, position trackers, the trading
  database, run loops, and any runtime state file. Not sanitised versions of
  them either.
- **Anything currently traded with real money**, including the parameters that
  identify it.
- **Universe selection and the feature set.** The specific instruments screened
  and the engineered features are the research asset. Their *methodology* is
  publishable; their contents are not.
- **Internal card identifiers** and paths into the private repo's layout.

## Ported with judgement

General findings and laws — statements about how cost, take-profit distance,
ranking and validation behave — are publishable, because they constrain
everyone's research equally and give no one an entry.

A finding is publishable when it survives this question: *if a competitor read
this, could they place a trade they could not have placed before?* If the answer
is yes, it stays private, however good the writing is.

## Held back so far

Recorded here so the decision is explicit rather than forgotten:

| Item | Why it is not published |
|---|---|
| Market-neutral alt/BTC spread findings | Active research direction; the momentum-vs-reversion result and the leg decomposition are directly actionable |
| The one rule that survives real cost on a small sample | The only surviving positive lead in the project |
| The 1h directional strategy's cost profile | Currently traded |
| Feature-level IC measurements | Identifies the feature set |

Revisit deliberately, not by drift. A held-back item becomes publishable when
it stops being an edge — usually because it was disproven, occasionally because
it was superseded.

## Before publishing a study

1. `./scripts/leak-guard.sh --all` is clean.
2. `run.sh` regenerates every figure in the study's README from bundled data.
3. The caveats section names what is *not* modelled, in the study's own terms.
4. A stranger with the repository and no context can run it in under ten
   minutes.

Point 4 is the one that decides whether any of this is worth doing.
