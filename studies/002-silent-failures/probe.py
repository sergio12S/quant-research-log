#!/usr/bin/env python3
"""Probes for backtest failures that report a number instead of an error.

Each probe asks a question whose answer you already know, and checks that the
engine agrees. That is the whole idea: you cannot audit a result you cannot
predict, so predict something trivial first.

None of these are clever. They are the checks that would have caught three
real defects found in one afternoon, each of which produced a plausible
backtest of a strategy nobody had written.

    ./probe.py /path/to/rlx-cli data/btc_1h_feat.csv

Adapting to another engine means rewriting `run()` and the strategy literals.
The probes themselves are engine-agnostic.
"""
import json
import subprocess
import sys
from pathlib import Path

RLX = sys.argv[1] if len(sys.argv) > 1 else "rlx-cli"
DATA = sys.argv[2] if len(sys.argv) > 2 else "data/btc_1h_feat.csv"

ENTRY = {"condition": "warm > 0 && sma_fast > sma_slow", "signal": "Long", "direction": 1}
EXIT = {"condition": "sma_fast < sma_slow", "reason": "RegimeExit"}

results = []


def run(strategy: dict, commission=0.0, timing="next_open", dynamic=False) -> dict:
    Path("_probe.json").write_text(json.dumps(strategy))
    p = subprocess.run(
        [RLX, "rules-backtest", "-d", DATA, "-r", "_probe.json",
         "--commission", f"{commission:.10f}",
         "--signal-execution-timing", timing,
         "--dynamic-tp-sl", "true" if dynamic else "false",
         "--json"],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"engine failed:\n{p.stderr[:500]}")
    return json.loads(p.stdout)


def exits(res: dict) -> dict:
    out = {}
    for t in res.get("trades", []):
        r = t.get("exit_reason", "?")
        out[r] = out.get(r, 0) + 1
    return out


def record(name, verdict, detail):
    results.append((name, verdict, detail))
    mark = {"pass": "PASS", "fail": "FAIL", "info": "INFO"}[verdict]
    print(f"[{mark}] {name}\n       {detail}", flush=True)


# --- 1. Are costs applied at all? -------------------------------------------
# A backtest that ignores fees is the most common way to publish a strategy
# that loses money. It is also the easiest thing in the world to check.
def probe_costs():
    free = run({"entry_rules": [ENTRY], "exit_rules": [EXIT]})
    paid = run({"entry_rules": [ENTRY], "exit_rules": [EXIT]}, commission=0.01)
    if abs(free["total_return"] - paid["total_return"]) < 1e-9:
        record("costs are applied", "fail",
               f"100 bps/side changed nothing: {free['total_return']*100:.2f}% both ways. "
               "The fee is not reaching the fill.")
    else:
        record("costs are applied", "pass",
               f"0 bps -> {free['total_return']*100:+.2f}%, "
               f"100 bps/side -> {paid['total_return']*100:+.2f}% "
               f"over {free['total_trades']} trades")


# --- 2. Does the engine invent exits? ---------------------------------------
# A strategy that declares no take-profit and no stop-loss must not exit on
# one. If it does, the result describes a strategy the author never wrote.
def probe_phantom_exits():
    # Default settings on purpose: this asks what a user actually gets, not
    # what an opt-in flag does when you ask for it.
    res = run({"entry_rules": [ENTRY], "exit_rules": [EXIT]})
    ex = exits(res)
    invented = ex.get("TakeProfit", 0) + ex.get("StopLoss", 0)
    if invented:
        pct = 100 * invented / max(res["total_trades"], 1)
        record("no exits are invented", "fail",
               f"{invented} of {res['total_trades']} trades ({pct:.0f}%) exited on a "
               f"take-profit or stop-loss the strategy never declared. Exits: {ex}")
    else:
        record("no exits are invented", "pass",
               f"{res['total_trades']} trades, all exited on the rule or end of data: {ex}")


# --- 3. Does the declared bracket reach every trade? ------------------------
# Declare a bracket so tight that essentially no trade can avoid it, then check
# that essentially every trade exits on it. Anything else means the bracket is
# not being applied to some fills.
def probe_bracket_reaches_trades():
    # A bracket is a guarantee about the WORST case, so test the worst case.
    # An earlier version of this probe measured the *share* of trades that ran
    # past the level and passed a build where the bracket was missing from half
    # the fills — because those trades still closed on a rule before drifting
    # far. The extreme is the right statistic: one unexplained violation means
    # the bound was not enforced, however rare.
    band = 0.01           # 1% each side
    tolerance = 2.0       # a gap can carry price through a level; 2x is generous
    res = run({"entry_rules": [ENTRY], "exit_rules": [],
               "take_profit_pct": band, "stop_loss_pct": band})
    # `returns` is per cent here (1.0 == 1%), not a fraction.
    limit_pct = band * 100.0
    worst = max((abs(t.get("returns", 0.0)) for t in res.get("trades", [])), default=0.0)
    over = [t for t in res.get("trades", []) if abs(t.get("returns", 0.0)) > limit_pct * tolerance]
    ratio = worst / limit_pct if limit_pct else 0.0
    detail = (f"worst trade moved {worst:.2f}% against a {band*100:.0f}% bracket "
              f"({ratio:.2f}x); {len(over)} of {res['total_trades']} trades exceeded "
              f"{tolerance:.0f}x")
    if ratio > tolerance:
        record("no trade escapes the declared bracket", "fail",
               detail + " — the bracket did not bound those fills.")
    else:
        record("no trade escapes the declared bracket", "pass", detail)


# --- 4. Is the default execution timing a look-ahead? ----------------------
# Executing a signal on the bar that produced it lets the strategy trade on
# information it did not have. Compare against the weakest honest assumption.
def probe_execution_timing():
    same = run({"entry_rules": [ENTRY], "exit_rules": [EXIT]}, timing="current_close")
    nxt = run({"entry_rules": [ENTRY], "exit_rules": [EXIT]}, timing="next_open")
    gap = same["total_return"] - nxt["total_return"]
    record("execution timing", "info",
           f"current_close {same['total_return']*100:+.2f}% vs next_open "
           f"{nxt['total_return']*100:+.2f}% (gap {gap*100:+.2f} pp). "
           "A large positive gap means the default is flattering the strategy.")


# --- 5. Does the validator validate? ----------------------------------------
# If a validator accepts an empty object, it accepts anything, and calling it
# before a run tells you nothing.
def probe_validator():
    bad = []
    for name, payload in [("empty object", {}), ("arbitrary json", {"nonsense": 42})]:
        Path("_probe.json").write_text(json.dumps(payload))
        p = subprocess.run([RLX, "agent", "validate-strategy", "--rules", "_probe.json"],
                           capture_output=True, text=True)
        try:
            status = json.loads(p.stdout).get("status")
        except Exception:
            status = "unparseable"
        if status == "valid":
            bad.append(name)
    if bad:
        record("the validator validates", "fail",
               f"accepted as a valid strategy: {', '.join(bad)}")
    else:
        record("the validator validates", "pass",
               "an empty object and arbitrary JSON are both rejected")


def main():
    print(f"engine: {subprocess.run([RLX, '--version'], capture_output=True, text=True).stdout.strip()}")
    print(f"data:   {DATA}\n")
    probe_costs()
    probe_phantom_exits()
    probe_bracket_reaches_trades()
    probe_execution_timing()
    probe_validator()
    Path("_probe.json").unlink(missing_ok=True)

    failed = [r for r in results if r[1] == "fail"]
    print(f"\n{len(results)} probes, {len(failed)} failed")
    Path("results").mkdir(exist_ok=True)
    Path("results/probes.json").write_text(json.dumps(
        [{"probe": n, "verdict": v, "detail": d} for n, v, d in results], indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
