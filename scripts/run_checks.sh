#!/usr/bin/env bash
# Dev-CI check runner for the TAPRX-888 KiCad project (Phase 1).
#
# Runs ERC, DRC, and a BOM completeness check with kicad-cli, and produces the
# schematic PDF plus gerbers/drill as artifacts. The KiBot outputs (interactive
# BOM, STEP, CPL, 3D renders) and the release pipeline are Phase 2.
#
# Gating is governed by ENFORCE:
#   ENFORCE=false (default) -> checks run and report, but never fail the job
#                              (bring-up mode: the design has known ERC/DRC
#                               violations tracked as issues; this captures the
#                               baseline as artifacts without blocking).
#   ENFORCE=true            -> ERC / DRC / BOM violations fail the job.
# Flip to true once the tracked ERC/DRC issues are cleared, and add these as
# required status checks in the dev/main rulesets at the same time.
set -uo pipefail

SCH="TAPRX-888.kicad_sch"
PCB="TAPRX-888.kicad_pcb"
ENFORCE="${ENFORCE:-false}"
mkdir -p reports
fail=0

note() {
  echo "$1"
  [ -n "${GITHUB_STEP_SUMMARY:-}" ] && echo "$1" >> "$GITHUB_STEP_SUMMARY"
}

emit_report() {
  # Echo a report file into the run log (collapsible group) and the job summary
  # (collapsible <details>), so the full ERC/DRC/BOM detail is visible without
  # downloading the artifact.
  local title="$1" file="$2"
  [ -f "$file" ] || return 0
  echo "::group::$title"
  cat "$file"
  echo "::endgroup::"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
      printf '\n<details><summary>%s</summary>\n\n```\n' "$title"
      cat "$file"
      printf '\n```\n\n</details>\n'
    } >> "$GITHUB_STEP_SUMMARY"
  fi
}

note "## Dev-CI checks (ENFORCE=$ENFORCE)"

# --- ERC (gate) ---------------------------------------------------------------
# Full report as artifact; --severity-error means only errors set the exit code
# (the known footprint-library-name warnings, #10, do not gate).
if kicad-cli sch erc "$SCH" -o reports/erc.rpt --severity-error --exit-code-violations; then
  note "- ✅ ERC: no errors"
else
  note "- ❌ ERC: errors found (see reports/erc.rpt)"; fail=1
fi

# --- DRC (gate) ---------------------------------------------------------------
# Uses the board design settings in .kicad_pro (no .kicad_dru yet, #3).
if kicad-cli pcb drc "$PCB" -o reports/drc.rpt --severity-error --exit-code-violations; then
  note "- ✅ DRC: no errors"
else
  note "- ❌ DRC: errors found (see reports/drc.rpt)"; fail=1
fi

# --- BOM completeness (gate) --------------------------------------------------
# Fitted parts only (--exclude-dnp). Map the project's "LCSC Part #" field to an
# "LCSC" column so the checker (and later JLCPCB tooling) find it.
kicad-cli sch export bom "$SCH" -o reports/bom.csv \
  --fields "Reference,Value,Footprint,LCSC Part #" \
  --labels "Reference,Value,Footprint,LCSC" \
  --exclude-dnp || note "- ⚠️ BOM export failed"
if python3 scripts/bom_check.py reports/bom.csv | tee reports/bom_check.txt; then
  note "- ✅ BOM check: all fitted parts complete"
else
  note "- ❌ BOM check: incomplete fitted rows (see reports/bom_check.txt)"; fail=1
fi

# --- Artifacts (never gate) ---------------------------------------------------
kicad-cli sch export pdf "$SCH" -o reports/TAPRX-888-schematic.pdf \
  || note "- ⚠️ schematic PDF export failed"
kicad-cli pcb export gerbers "$PCB" -o reports/gerbers/ \
  || note "- ⚠️ gerber export failed"
kicad-cli pcb export drill "$PCB" -o reports/gerbers/ \
  || note "- ⚠️ drill export failed"

# --- Report detail (echoed to the run log + job summary) ----------------------
emit_report "ERC report (erc.rpt)" reports/erc.rpt
emit_report "DRC report (drc.rpt)" reports/drc.rpt
emit_report "BOM completeness (bom_check.txt)" reports/bom_check.txt

# --- Verdict ------------------------------------------------------------------
if [ "$fail" -ne 0 ]; then
  if [ "$ENFORCE" = "true" ]; then
    note ""
    note "**Result: FAILED** (ENFORCE=true)."
    exit 1
  fi
  note ""
  note "**Result: violations found but not gated** (ENFORCE=false — bring-up mode). Baseline is in the uploaded reports."
fi
exit 0
