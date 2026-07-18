#!/usr/bin/env bash
# Build the TAPRX-888 fabrication + design package for a release, via KiBot,
# with build-time provenance injection.
#
# Order matters: provenance (title-block rev + GIT_HASH) is injected into the
# ephemeral checkout FIRST, then the exporters generate from the already-stamped
# design. KiBot never owns the revision -- it only generates. Nothing is
# committed back. See docs/RELEASE_STRATEGY.md.
#
# Preflights (ERC/DRC) are skipped here: gating already happened on the PR into
# main (dev-checks). This job just produces the package.
#
# Phase A scope: JLCPCB turnkey data (gerbers, drill, CPL, LCSC BOM), STEP,
# interactive BOM, 3D renders, and a plain framed schematic PDF (kicad-cli).
# The composited assembly / fabrication-drawing PDFs (gen_docs.sh) are Phase B.
#
# Requires env: REVISION, GIT_HASH. Produces everything under out/.
set -euo pipefail

CFG="scripts/TAPRX-888.kibot.yaml"
SCH="TAPRX-888.kicad_sch"
PCB="TAPRX-888.kicad_pcb"
WKS="TAPR.kicad_wks"
: "${REVISION:?REVISION required}"
: "${GIT_HASH:?GIT_HASH required}"

OUT="out"
mkdir -p "$OUT/docs"

# Version-stamped filename stem, so every emailed/exported document names its
# own version (not just the content). e.g. TAPRX-888-v0.5-schematic.pdf.
STEM="TAPRX-888-v${REVISION}"

# --- Inject provenance (build-time only; never committed back) ----------------
python3 scripts/inject_provenance.py --revision "$REVISION" --git-hash "$GIT_HASH"

# --- Version marker stamped into the package ----------------------------------
# The committed VERSION.txt is a de-numbered "development snapshot" so a zip of
# the source tree is never anonymous yet never goes stale. The released package
# carries the exact version on the Version: line, so an unzipped copy names its
# own version too. Build-time only -- the committed file is untouched.
sed "s#^Version:.*#Version:  v${REVISION}   (commit ${GIT_HASH})#" \
  VERSION.txt > "$OUT/VERSION.txt"

# --- Schematic PDF (kicad-cli renders the title-block frame natively) ---------
# Pass the worksheet explicitly so the frame never depends on the project's
# page_layout_descr_file (which KiCad can blank locally). rev/date/title come
# from the title blocks stamped above; GIT_HASH is threaded through; the other
# frame variables (DESIGNER/LICENSE/REPO) come from the project text_variables.
kicad-cli sch export pdf "$SCH" -o "$OUT/docs/${STEM}-schematic.pdf" \
  --drawing-sheet "$WKS" \
  --define-var "GIT_HASH=$GIT_HASH"

# --- Assembly drawing: top + bottom, framed -----------------------------------
# Component-placement drawing for the fab house: F/B.Fab + silkscreen + edge,
# with the title-block frame (--include-border-title). The bottom view is
# mirrored. Two single-page plots merged into one 2-page PDF. Needs no 3D models
# and no compositor -- the fully framed, board-normalized fabrication drawing is
# a Phase B (gen_docs.sh) follow-up.
ASM="$(mktemp -d)"
kicad-cli pcb export pdf "$PCB" -o "$ASM/top.pdf" --mode-single \
  --include-border-title --drawing-sheet "$WKS" --define-var "GIT_HASH=$GIT_HASH" \
  --layers "F.Fab,F.Silkscreen,Edge.Cuts"
kicad-cli pcb export pdf "$PCB" -o "$ASM/bot.pdf" --mode-single --mirror \
  --include-border-title --drawing-sheet "$WKS" --define-var "GIT_HASH=$GIT_HASH" \
  --layers "B.Fab,B.Silkscreen,Edge.Cuts"
if command -v pdfunite >/dev/null 2>&1; then
  pdfunite "$ASM/top.pdf" "$ASM/bot.pdf" "$OUT/docs/${STEM}-assembly.pdf"
elif command -v gs >/dev/null 2>&1; then
  gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
     -sOutputFile="$OUT/docs/${STEM}-assembly.pdf" "$ASM/top.pdf" "$ASM/bot.pdf"
else
  echo "ERROR: no PDF merge tool (pdfunite/gs) available" >&2; exit 1
fi
rm -rf "$ASM"

# --- Turnkey data via KiBot ---------------------------------------------------
# Essential JLCPCB outputs -- a failure here fails the release. These are all 2D
# (gerbers/drill/placement/BOM), so they need neither 3D models nor a netlist;
# --skip-pre all is safe (ERC/DRC already gated on the PR into main).
kibot -c "$CFG" -e "$SCH" -b "$PCB" -d "$OUT" --skip-pre all \
  JLCPCB_gerbers JLCPCB_drill JLCPCB_position JLCPCB_bom

# Interactive HTML BOM -- best-effort. Skip only erc/drc (not update_xml): iBOM
# needs the XML netlist to populate its user-defined fields (LCSC/MFG/MPN).
kibot -c "$CFG" -e "$SCH" -b "$PCB" -d "$OUT" --skip-pre erc,drc \
  ibom \
  || echo "WARN: iBOM generation failed; release continues without it."

# NOTE: STEP (3D model) and 3D renders are intentionally NOT built here. The
# board's footprints reference custom 3D models via ${TIS} (Turn Island Systems'
# model library) and the deprecated ${KISYS3DMOD}, neither of which exists in the
# CI image -- KiBot cannot resolve them and aborts. Restoring STEP/renders needs
# either that model library provisioned in the CI image, or the
# footprints' 3D paths remapped to KiCad's standard packages. Tracked as a
# follow-up; the outputs remain defined in scripts/TAPRX-888.kibot.yaml for then.

echo "Built package for rev${REVISION} (git ${GIT_HASH}):"
find "$OUT" -type f | sort
