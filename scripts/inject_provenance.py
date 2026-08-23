#!/usr/bin/env python3
"""Inject build-time provenance into the KiCad design, in place.

Writes two things onto the ephemeral CI checkout, just before the release
export runs:

  - REVISION -> the title-block ``rev`` field of every schematic sheet and the
    board. KiCad's built-in ${REVISION} renders it in the title block / custom
    worksheet. We write the field itself (not a project text variable named
    REVISION) to avoid clashing with that built-in. TAPRX-888's schematic is
    hierarchical, so ALL sheets are stamped (root + Front_End + refclk) --
    otherwise a sub-sheet page in the exported PDF would still read "DEV".
  - GIT_HASH -> the ``GIT_HASH`` project text variable, rendered as ${GIT_HASH}
    in the title block / worksheet and on the bottom silkscreen.

This is intentionally the *only* place provenance is stamped, so the exporters
never own the revision -- they just generate from an already-stamped design.
Nothing is committed back; this runs on the throwaway CI checkout only.

Usage:
    inject_provenance.py --revision REV --git-hash HASH \\
        [--pro FILE] [--sheets FILE ...] [--pcb FILE]

Env fallbacks: REVISION, GIT_HASH (CLI flags win).
"""
import argparse
import json
import os
import re
import sys


def inject_git_hash(pro_path, git_hash):
    with open(pro_path) as f:
        p = json.load(f)
    p.setdefault("text_variables", {})
    p["text_variables"]["GIT_HASH"] = git_hash
    with open(pro_path, "w") as f:
        json.dump(p, f, indent=2)


def inject_revision(path, revision):
    with open(path) as f:
        t = f.read()
    t, n = re.subn(r'\(rev "[^"]*"\)', f'(rev "{revision}")', t, count=1)
    if n != 1:
        sys.exit(f"ERROR: expected exactly one (rev ...) in {path}, replaced {n}")
    with open(path, "w") as f:
        f.write(t)


def inject_board_git_hash(pcb_path, git_hash):
    """Sync the board's embedded GIT_HASH copy.

    KiCad caches the project text variables into the .kicad_pcb as a top-level
    ``(property "GIT_HASH" "...")`` entry. kicad-cli re-reads the .kicad_pro
    (so the schematic/assembly PDFs and the 3D GLB resolve ${GIT_HASH}
    correctly), but the pcbnew-based gerber plot (KiBot) resolves ${GIT_HASH}
    on the board silk from THIS embedded copy. If it isn't stamped too, the fab
    gerbers render the stale committed value ("dev") while every kicad-cli
    output is correct -- the split that hid this for several releases. Every
    board here (main + both end plates) carries exactly one such property.
    """
    with open(pcb_path) as f:
        t = f.read()
    t, n = re.subn(r'(\(property "GIT_HASH" ")[^"]*(")',
                   lambda m: m.group(1) + git_hash + m.group(2), t, count=1)
    if n != 1:
        sys.exit(f'ERROR: expected exactly one board (property "GIT_HASH" ...) '
                 f"in {pcb_path}, replaced {n}")
    with open(pcb_path, "w") as f:
        f.write(t)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--revision", default=os.environ.get("REVISION"),
                    help="title-block rev value (env: REVISION)")
    ap.add_argument("--git-hash", default=os.environ.get("GIT_HASH"),
                    help="GIT_HASH text variable value (env: GIT_HASH)")
    ap.add_argument("--pro", default="TAPRX-888.kicad_pro")
    ap.add_argument("--sheets", nargs="*",
                    default=["TAPRX-888.kicad_sch",
                             "Front_End.kicad_sch",
                             "refclk.kicad_sch"],
                    help="schematic sheet files to stamp "
                         "(each has exactly one title-block rev); may be empty "
                         "for a PCB-only project such as a mechanical end plate")
    ap.add_argument("--pcb", default="TAPRX-888.kicad_pcb")
    args = ap.parse_args(argv)

    if not args.revision:
        ap.error("REVISION required (--revision or env REVISION)")
    if not args.git_hash:
        ap.error("GIT_HASH required (--git-hash or env GIT_HASH)")

    inject_git_hash(args.pro, args.git_hash)
    for path in list(args.sheets) + [args.pcb]:
        inject_revision(path, args.revision)
    # The board caches the project text vars; sync its GIT_HASH copy too, or the
    # pcbnew-based gerber plot renders the stale value while kicad-cli is correct.
    inject_board_git_hash(args.pcb, args.git_hash)

    print(f"Injected rev='{args.revision}' into "
          f"{len(args.sheets)} sheet(s) + PCB title blocks; "
          f"GIT_HASH='{args.git_hash}' text var (.kicad_pro + board property)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
