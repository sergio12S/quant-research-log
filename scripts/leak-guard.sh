#!/usr/bin/env bash
# Refuse to commit anything carrying markers from the private working repo.
#
# This is a guard, not an automation: it cannot decide what is safe to publish,
# only block the specific things that must never appear. Curation stays manual.
#
#   ./scripts/leak-guard.sh          # check staged changes (what a commit would publish)
#   ./scripts/leak-guard.sh --all    # check every tracked file (what CI does)
#
# Install as a hook:
#   ln -sf ../../scripts/leak-guard.sh .git/hooks/pre-commit

set -uo pipefail

# --- Forbidden markers. Edit freely; over-blocking is cheap, under-blocking is not.
PATTERNS=(
  # Machine and repository layout
  '/Users/[a-z]+'
  '\.env\b'

  # Live execution — must never reach a public repository
  '[Hh]yperliquid'
  'HYPERLIQUID_SECRET_KEY'
  'live_flagship'
  'position_tracker'
  'trading_db'
  'run_live_loop'
  'hybrid_bot_state'
  '_status\.json'

  # Credentials and addresses
  '0x[a-fA-F0-9]{40}'
  'ghp_[A-Za-z0-9]{20,}'
  'sk-[A-Za-z0-9]{20,}'
  'BEGIN [A-Z ]*PRIVATE KEY'
  'api[_-]?secret'
  'private[_-]?key'

  # Internal identifiers and the research assets that constitute the edge
  'hyp_[0-9]{10,}'
  'alt_universe'
  'canonical_v1'
  'combo_v1'
  'entropy_288'
  'compression_6_72'
  'full_bar_streak'
  'avg_trade_size_z_24'
  'vol_regime_delta_24'
  'narrow_wide_vol_streak'
)

mode="${1:-staged}"
fail=0

if [ "$mode" = "--all" ]; then
  files=$(git ls-files)
else
  files=$(git diff --cached --name-only --diff-filter=ACM)
fi

[ -z "$files" ] && { echo "leak-guard: nothing to check"; exit 0; }

for pat in "${PATTERNS[@]}"; do
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    # The guard's own pattern list is not a leak.
    [ "$f" = "scripts/leak-guard.sh" ] && continue
    if hits=$(grep -InE "$pat" "$f" 2>/dev/null); then
      echo "BLOCKED  $f"
      echo "$hits" | head -3 | sed 's/^/         /'
      echo "         matched: $pat"
      fail=1
    fi
  done <<< "$files"
done

if [ "$fail" -ne 0 ]; then
  cat <<'EOF'

leak-guard refused this commit.

Either the content genuinely should not be published, or the marker is a false
positive and belongs removed from PATTERNS in scripts/leak-guard.sh. Do not
bypass with --no-verify: the whole point is that publishing is a decision
someone makes on purpose.
EOF
  exit 1
fi

echo "leak-guard: clean"
