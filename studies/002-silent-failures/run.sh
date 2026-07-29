#!/usr/bin/env bash
# Reproduces this study's probe results.
#
#   ./run.sh /path/to/rlx-cli
#
# Features are derived from study 001's bundled dataset, so nothing here
# depends on a second download agreeing with the first.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
RLX="${1:-rlx-cli}"
[ -f data/btc_1h_feat.csv ] || python3 ../001-execution-costs/build_features.py \
  ../001-execution-costs/data/btc_1h.csv data/btc_1h_feat.csv 24 168
mkdir -p results
python3 probe.py "$RLX" data/btc_1h_feat.csv | tee results/run.log
