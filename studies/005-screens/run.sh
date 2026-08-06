#!/usr/bin/env bash
# Reproduces every figure in this study's README.
#
#   ./run.sh                       # uses `rlx-cli` from PATH
#   ./run.sh /path/to/rlx-cli
#
# The engine ships as the macOS app from https://rlxbt.com or as
# ghcr.io/sergio12s/rlxbt-server. Its own repository is private, so there is no
# clone-and-build path. Needs 0.2.12 or later.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

RLX="${1:-rlx-cli}"
command -v "$RLX" >/dev/null 2>&1 || [ -x "$RLX" ] || {
  echo "engine not found: $RLX"; exit 1; }

VERSION="$("$RLX" --version 2>/dev/null || echo unknown)"
echo "engine: $VERSION"

# Same dataset as study 001, linked rather than copied.
[ -e data ] || ln -s ../001-execution-costs/data data
for f in btc_1h_feat.csv btc_4h_feat.csv btc_1d_feat.csv; do
  [ -f "data/$f" ] || { echo "missing data/$f — run study 001's run.sh first"; exit 1; }
done

mkdir -p results
{ echo "engine: $VERSION"; python3 screens.py "$RLX"; } | tee results/run.log

echo
echo "results/screens.json holds the grid and both rankings."
echo "If a number here differs from the README, the README is wrong — open an issue."
