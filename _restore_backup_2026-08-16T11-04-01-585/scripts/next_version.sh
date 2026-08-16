#!/usr/bin/env bash
# Compute the next release version for a lane, given the existing releases.
#
# This is the single source of truth for the versioning policy (see
# docs/RELEASE_STRATEGY.md). It is pure and testable: it takes the existing
# releases on stdin, so the same logic that runs in CI can be unit-tested
# offline against fabricated inputs (scripts/test_next_version.sh) without
# cutting real releases.
#
# Usage:
#   next_version.sh <dev|main> [seed]
#
# stdin: one release per line, "<version> <isPrerelease>", newest-first order
#        is NOT required. Version may carry a leading 'v'. Example:
#            v1.3 true
#            v1.0 false
#        (In CI:  gh release list --json tagName,isPrerelease
#                   --jq '.[] | "\(.tagName) \(.isPrerelease)"' )
#
# stdout: the next version, no 'v' prefix (e.g. "1.4" or "2.0").
#
# Policy:
#   main : the next whole major, minor 0  (first ever -> 1.0). Every production
#          release is a major -- there is no auto-minor and no manual major.
#   dev  : minor++ within the CURRENT major line. The line's major follows the
#          latest main (non-prerelease) release's major (0 while pre-1.0). The
#          first dev pre-release after a main "X.0" starts at "X.1"; the very
#          first pre-release while pre-1.0 uses <seed> (default 0.6).
set -euo pipefail

lane="${1:?usage: next_version.sh <dev|main> [seed]}"
seed="${2:-0.6}"

major() { printf '%s' "${1%%.*}"; }
minor() { local v="${1#*.}"; printf '%s' "${v%%.*}"; }   # tolerate extra parts

stable=()   # non-prerelease versions (main line, always X.0)
pre=()      # prerelease versions (dev line)
while read -r ver ispre _rest || [ -n "${ver:-}" ]; do
  [ -n "${ver:-}" ] || continue
  ver="${ver#v}"
  case "${ispre:-false}" in
    true|True|TRUE) pre+=("$ver") ;;
    *)              stable+=("$ver") ;;
  esac
done

# Highest major among main (stable) releases; track whether any exist.
main_major=0
have_main=0
for v in "${stable[@]:-}"; do
  [ -n "$v" ] || continue
  have_main=1
  m=$(major "$v")
  [ "$m" -gt "$main_major" ] && main_major="$m"
done

if [ "$lane" = "main" ]; then
  if [ "$have_main" -eq 0 ]; then echo "1.0"; else echo "$((main_major + 1)).0"; fi
  exit 0
fi

if [ "$lane" != "dev" ]; then
  echo "ERROR: lane must be 'dev' or 'main', got '$lane'" >&2
  exit 2
fi

# dev lane: the current major line follows the latest main release (0 pre-1.0).
line="$main_major"
best_minor=-1
for v in "${pre[@]:-}"; do
  [ -n "$v" ] || continue
  if [ "$(major "$v")" -eq "$line" ]; then
    mn=$(minor "$v")
    [ "$mn" -gt "$best_minor" ] && best_minor="$mn"
  fi
done

if [ "$best_minor" -ge 0 ]; then
  echo "${line}.$((best_minor + 1))"       # continue the line
elif [ "$line" -eq 0 ]; then
  echo "$seed"                             # pre-1.0, first-ever pre-release
else
  echo "${line}.1"                         # first dev after a main "X.0"
fi
