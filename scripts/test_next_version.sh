#!/usr/bin/env bash
# Offline unit tests for scripts/next_version.sh -- proves the versioning policy
# across the full lifecycle (0.6 -> ... -> 1.0 -> 1.1 -> ... -> 2.0 -> 2.1)
# without cutting any real releases. Run: scripts/test_next_version.sh
set -uo pipefail
cd "$(dirname "$0")"

pass=0 fail=0

# check <name> <lane> <releases-multiline> <expected> [seed]
check() {
  local name="$1" lane="$2" releases="$3" expected="$4" seed="${5:-}"
  local got
  got=$(printf '%s' "$releases" | ./next_version.sh "$lane" $seed)
  if [ "$got" = "$expected" ]; then
    printf '  ok   %-42s -> %s\n' "$name" "$got"; pass=$((pass+1))
  else
    printf '  FAIL %-42s -> got %s, expected %s\n' "$name" "$got" "$expected"; fail=$((fail+1))
  fi
}

echo "== pre-1.0 (dev increments 0.x) =="
check "dev, no releases (seed)"        dev ""                                  "0.6"
check "dev, custom seed"               dev ""                                  "0.1" "0.1"
check "dev after 0.6"                  dev "v0.6 true"                         "0.7"
check "dev after 0.6,0.7,0.8"          dev $'v0.6 true\nv0.7 true\nv0.8 true'  "0.9"
check "dev unordered input"            dev $'v0.8 true\nv0.6 true\nv0.7 true'  "0.9"

echo "== first production release (main -> 1.0) =="
check "main, no releases"              main ""                                 "1.0"
check "main, only prereleases exist"   main $'v0.8 true\nv0.9 true'            "1.0"

echo "== post-1.0 (dev increments 1.x) =="
check "dev right after 1.0"            dev $'v0.9 true\nv1.0 false'            "1.1"
check "dev after 1.1"                  dev $'v1.1 true\nv1.0 false'            "1.2"
check "dev after 1.1,1.2,1.3"          dev $'v1.0 false\nv1.1 true\nv1.2 true\nv1.3 true' "1.4"

echo "== next production release (main -> 2.0) =="
check "main after 1.0 (+ dev churn)"   main $'v1.0 false\nv1.3 true'          "2.0"
check "main picks highest major"       main $'v1.0 false\nv2.0 false'         "3.0"

echo "== post-2.0 (dev increments 2.x, ignores old line) =="
check "dev right after 2.0"            dev $'v2.0 false\nv1.5 true'           "2.1"
check "dev after 2.1 (old 1.9 ignored)" dev $'v2.0 false\nv2.1 true\nv1.9 true' "2.2"

echo
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
