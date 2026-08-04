#!/usr/bin/env bash
# Reproduces every figure in this study's README.
#
#   ./run.sh                       # uses `rlx-cli` from PATH
#   ./run.sh /path/to/rlx-cli      # or point at a build
#
# The engine ships as the macOS app from https://rlxbt.com (its bundled rlx-cli
# is what this drives) or as ghcr.io/sergio12s/rlxbt-server. Its own repository
# is private, so there is no clone-and-build path.
#
# Needs rlx 0.2.12 or later: before that the engine accepted `position_size` and
# ignored it, so every sizing produced identical numbers and the correction this
# study measures could not be observed at all.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

RLX="${1:-rlx-cli}"
command -v "$RLX" >/dev/null 2>&1 || [ -x "$RLX" ] || {
  echo "engine not found: $RLX"; exit 1; }

VERSION="$("$RLX" --version 2>/dev/null || echo unknown)"
echo "engine: $VERSION"

# Same dataset as study 001, linked rather than copied: three studies sharing
# one 5 MB file should not mean three copies of it in the repository.
[ -e data ] || ln -s ../001-execution-costs/data data
[ -f data/btc_1h_feat.csv ] || {
  echo "missing data/btc_1h_feat.csv — run study 001's build_features.py first"; exit 1; }

mkdir -p results

# 1. The screen against bisection, across position sizes.
# The version goes into the log, not only onto the terminal: a transcript that
# does not say which build produced it cannot settle an argument later.
{ echo "engine: $VERSION"; python3 validate.py "$RLX"; } | tee results/run.log

# 2. The screen applied to a table, to show what the tool actually does.
echo
python3 screen.py example-table.csv --cost 4.404 | tee results/example.txt

# 3. The portfolio case, which needs the HTTP API rather than the CLI —
# /api/portfolio is the only place the multi-sleeve capital model exists.
# Skipped rather than failed when no engine is listening, so this script still
# reproduces the single-position result on a machine without one.
if curl -sf -o /dev/null --max-time 5 "${RLX_API:-http://127.0.0.1:8142}/api/health"; then
  echo
  python3 portfolio.py "${RLX_API:-http://127.0.0.1:8142}" | tee results/portfolio.log
else
  echo
  echo "skipping portfolio.py: no engine on ${RLX_API:-http://127.0.0.1:8142}"
  echo "  (start the macOS app, or set RLX_API, to reproduce the portfolio table)"
fi

echo
echo "results/validation.json holds the measurement in the README."
echo "If a number here differs from the README, the README is wrong — open an issue."
