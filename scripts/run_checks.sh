#!/usr/bin/env bash
# Dev-CI check runner for the TAPRX-888 KiCad project (Phase 1).
#
# Runs ERC, DRC, and a BOM completeness check with kicad-cli, plus a 3D-model
# resolution check, and produces the schematic PDF, gerbers/drill, the board
# STEP and a top 3D render as artifacts. The KiBot turnkey/release outputs
# (interactive BOM, CPL, composited PDFs) are the release pipeline.
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
  # Echo a report file into the run log only, as a collapsed group. The full
  # reports are uploaded as artifacts (and published to ci-docs on design
  # pushes), so the job summary keeps just the concise pass/fail lines instead
  # of a second full copy -- that duplication is what overflowed the 1 MB
  # summary limit.
  local title="$1" file="$2"
  [ -f "$file" ] || return 0
  echo "::group::$title"
  cat "$file"
  echo "::endgroup::"
}

note "## Dev-CI checks (ENFORCE=$ENFORCE)"

# --- ERC (gate) ---------------------------------------------------------------
# Full report including warnings, uploaded as an artifact. --exit-code-violations
# makes any violation (error or warning) set the exit code; with ENFORCE=false the
# job still passes and just records the baseline (see the verdict block).
if kicad-cli sch erc "$SCH" -o reports/erc.rpt --exit-code-violations; then
  note "- ✅ ERC: no violations"
else
  note "- ⚠️ ERC: violations found (errors and/or warnings; see reports/erc.rpt)"; fail=1
fi

# --- DRC (gate) ---------------------------------------------------------------
# Board design settings (.kicad_pro) + custom rules (TAPRX-888.kicad_dru).
# --refill-zones is REQUIRED: without it kicad-cli runs against the SAVED zone
# fill and silently skips every pour-dependent check (solder-mask bridges,
# copper-to-zone clearance). No --save-board, so the refill is transient and the
# committed board is untouched. Full report incl. warnings; non-gating while
# ENFORCE=false.
if kicad-cli pcb drc "$PCB" -o reports/drc.rpt --refill-zones --schematic-parity --exit-code-violations; then
  note "- ✅ DRC: no violations"
else
  note "- ⚠️ DRC: violations found (errors and/or warnings; see reports/drc.rpt)"; fail=1
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

# --- 3D models + STEP/render (structure gates; STEP built from vendored models) -
# check_3d_models GATES on structure: no legacy refs survive the remap, every
# board-used ${KIPRJMOD}/3d/ custom model is present, AND every board-used stock
# model is vendored under 3d/kicad-stock/ (#45). All 3D paths therefore resolve
# from the repo itself -- no image models and no network needed -- so the STEP
# below is fully populated and is uploaded as the EE<->ME artifact
# (mechanical/README.md).
if python3 scripts/check_3d_models.py --require-local . > reports/check_3d_models.txt 2>&1; then
  note "- ✅ 3D models: no legacy refs; all board-used models present"
else
  note "- ❌ 3D models: unresolved or missing (see reports/check_3d_models.txt)"; exit 1
fi
# The stock KiCad models are vendored in-repo (3d/kicad-stock/, mirroring the
# .3dshapes layout) so the STEP is reproducible with no image models or network
# (the CI image ships no 3D models, and KiBot's on-demand download 404s on KiCad
# 10). Point KICAD10_3DMODEL_DIR at that mirror unless the environment already set
# it -- a local KiCad install defines it, so respect that; custom parts resolve
# via ${KIPRJMOD}, which KiCad always sets.
if [ -z "${KICAD10_3DMODEL_DIR:-}" ]; then
  export KICAD10_3DMODEL_DIR="$PWD/3d/kicad-stock"
fi
note "- 3D model path: KICAD10_3DMODEL_DIR=${KICAD10_3DMODEL_DIR:-<unset>}"

# STEP export with the full board-feature flag set, so the shell matches the PCB
# editor's 3D view (copper/silk/mask + solid, watertight body) rather than a bare
# outline. --subst-models pulls the STEP twin of any VRML-referenced model. With
# every model vendored, an unresolved model is a real regression -> gate on it.
if kicad-cli pcb export step "$PCB" -o reports/TAPRX-888.step \
      --subst-models --no-dnp --include-tracks --include-silkscreen --include-soldermask \
      --cut-vias-in-body --fill-all-vias --drill-origin --min-distance=0.01mm \
      > reports/step_export.log 2>&1; then
  if grep -qE 'File not found|Could not add' reports/step_export.log; then
    note "- ❌ STEP: some 3D models did not resolve (see run log)"; fail=1
  else
    note "- ✅ STEP: board STEP built, all component models resolved"
  fi
else
  note "- ⚠️ STEP export failed (see run log)"
fi
# 3D renders via KiBot's render_3d (OpenGL, ray_tracing:false) -- the same engine
# as the PCB editor's 3D viewer (File -> Export Image). kicad-cli's standalone
# raytracer in 10.0.4 doesn't draw the soldermask (bare-copper "gold" render, so
# the stackup mask colour never shows); KiBot's OpenGL path honours the stackup
# mask/silk/finish colours. Same invocation the release build uses.
if kibot -c scripts/TAPRX-888.kibot.yaml -e "$SCH" -b "$PCB" -d reports \
      --skip-pre all render_top render_bottom > reports/render.log 2>&1; then
  # The KiBot output has `dir: fab` (the release package layout), so the PNGs
  # land in reports/fab/. In the dev-checks artifact we want them at the top
  # level next to the STEP, so flatten fab/ here (leaving the shared release
  # config untouched).
  mv -f reports/fab/TAPRX-888-3d-top.png reports/fab/TAPRX-888-3d-bottom.png \
     reports/ 2>/dev/null || true
  rmdir reports/fab 2>/dev/null || true
  note "- ✅ 3D renders (top+bottom) via KiBot render_3d (OpenGL, stackup colours)"
else
  note "- ⚠️ 3D render failed (see run log)"
fi

# --- Report detail (echoed to the collapsed run log) --------------------------
emit_report "ERC report (erc.rpt)" reports/erc.rpt
emit_report "DRC report (drc.rpt)" reports/drc.rpt
emit_report "BOM completeness (bom_check.txt)" reports/bom_check.txt
emit_report "3D model check (check_3d_models.txt)" reports/check_3d_models.txt
# The STEP/render command logs are process noise, not review outputs: echo them
# to the collapsed run log (available if a build breaks) then drop them so the
# uploaded artifact carries only the actual outputs, not these logs.
emit_report "STEP export log (step_export.log)" reports/step_export.log
emit_report "3D render log (render.log)" reports/render.log
rm -f reports/step_export.log reports/render.log

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
