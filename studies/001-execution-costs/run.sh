#!/usr/bin/env bash
# Reproduces every figure in this study's README.
#
#   ./run.sh                       # uses `rlx-cli` from PATH
#   ./run.sh /path/to/rlx-cli      # or point at a build
#
# The engine ships as the macOS app from https://rlxbt.com (its bundled rlx-cli
# is what this drives) or as ghcr.io/sergio12s/rlxbt-server. Its own repository
# is private, so there is no clone-and-build path.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

RLX="${1:-rlx-cli}"
command -v "$RLX" >/dev/null 2>&1 || [ -x "$RLX" ] || {
  echo "engine not found: $RLX"; exit 1; }

VERSION="$("$RLX" --version 2>/dev/null || echo unknown)"
echo "engine: $VERSION"

# 1h is bundled; 4h and 1D are derived from it so nothing depends on a second
# download agreeing with the first.
[ -f data/btc_4h.csv ] || python3 resample.py data/btc_1h.csv data/btc_4h.csv 14400
[ -f data/btc_1d.csv ] || python3 resample.py data/btc_1h.csv data/btc_1d.csv 86400

mkdir -p results
# The README says this transcript begins with the engine version. It did not:
# the line was echoed to the terminal and never reached the file.
{ echo "engine: $VERSION"; python3 breakeven.py "$RLX"; } | tee results/run.log
python3 bar_ranges.py | tee results/bar_ranges.txt

echo
echo "results/breakeven.json holds the table in the README."
echo "If a number here differs from the README, the README is wrong — open an issue."
