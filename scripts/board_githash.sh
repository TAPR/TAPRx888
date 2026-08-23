#!/usr/bin/env sh
# Short hash of the last commit that touched the main-board design files.
#
# Single source of truth for board provenance. Used by:
#   - dev-release.yml (prepare): the githash stamped into the v0.x pre-release
#   - mechanical-build.yml (boards-step): the hash injected into the 3D board
#     silk AND shown as "Board commit:" in the viewer header
# so the 3D viewer, the fab package, and the release notes all cite one hash.
#
# End plates have their own provenance lane (ep_githash) and are intentionally
# excluded here. A bare glob like '*.kicad_pcb' is a git pathspec that matches
# at ANY depth (mechanical/**/x.kicad_pcb), so the root board files are listed
# explicitly.
set -eu
git log -1 --format=%h -- \
  'TAPRX-888.kicad_sch' 'Front_End.kicad_sch' 'refclk.kicad_sch' \
  'TAPRX-888.kicad_pcb' 'TAPRX-888.kicad_pro' 'TAPRX-888.kicad_dru' \
  'Library.kicad_sym' 'Library.pretty/' 'fp-lib-table' 'sym-lib-table'
