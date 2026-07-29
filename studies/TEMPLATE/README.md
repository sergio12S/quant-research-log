# NNN — Short claim, stated as a claim

**Question:** the one thing this study set out to decide, in a sentence.

**Short answer:** the finding, including when it does not hold.

State the cost basis in the first paragraph. Figures are commission-only at
X bps/side unless stated; say what is not modelled.

---

## Why this got measured

What prompted it. If it was a mistake — an audit that found something wrong, a
result that failed to reproduce — say so plainly. That context is why a reader
believes the rest.

## Method

Enough that someone could rebuild it without this repository: the rule, the
instrument, the window, the parameters that were varied and the ones that were
held fixed.

## Result

The table or the figure. Every number here must come out of `run.sh`.

## What would change this conclusion

Name the observation that would overturn the finding. A study that cannot be
wrong is not a study.

## Caveats

What is not modelled, what the sample cannot support, and where the selection
effects are. Be specific — "past performance does not guarantee future results"
is not a caveat, it is filler.

## Reproduce

```bash
./run.sh
```

Bundled data lives in `data/`. Engine version and the run digest are written to
`results/` so a rerun can be compared byte for byte.
