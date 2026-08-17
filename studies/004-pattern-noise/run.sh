#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
API="${1:-http://127.0.0.1:8142}"
./nulltest.py "$API" data/btc_1h_feat.csv
