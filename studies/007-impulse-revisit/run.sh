#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[ -e data ] || ln -s ../001-execution-costs/data data
python3 impulse_revisit.py data/btc_1h.csv
