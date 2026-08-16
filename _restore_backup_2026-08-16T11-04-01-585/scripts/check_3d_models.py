#!/usr/bin/env python3
"""Validate the TAPRX-888 3D-model references.

Every model the design uses is vendored in this repo, so nothing depends on the
CI image or the network (the kicad*_auto image ships no 3D models and KiBot's
on-demand download 404s on KiCad 10). Two resolvable prefixes (see 3d/README.md):

  - custom parts   -> ${KIPRJMOD}/3d/<file>
  - stock KiCad    -> ${KICAD10_3DMODEL_DIR}/<pkg>.3dshapes/<file>, mirrored
                      in-repo under 3d/kicad-stock/<pkg>.3dshapes/<file>. In CI
                      KICAD10_3DMODEL_DIR is pointed at that mirror; on a local
                      KiCad install the same var resolves to the standard library.

Both prefixes resolve to real files in the tree, so both presences ARE checkable
and are checked. Always FAILS if any legacy/unresolvable reference survives the
remap (${TIS}, the :TIS: nickname, or the deprecated ${KISYS3DMOD}).

With --require-local it additionally FAILS if any BOARD-USED model file is
missing from the repo (custom OR stock). "Board-used" = referenced by a footprint
in TAPRX-888.kicad_pcb; models referenced only by an (unplaced) Library.pretty
footprint are reported but do not gate, since they never enter the board STEP.

Usage:
    python3 scripts/check_3d_models.py [--require-local] [ROOT]
"""
import re, sys, os

LEGACY = ('${TIS}', ':TIS:', '${KISYS3DMOD}')
LOCAL_PREFIX = '${KIPRJMOD}/3d/'
STOCK_PREFIX = '${KICAD10_3DMODEL_DIR}/'
STOCK_VENDOR_DIR = '3d/kicad-stock'   # in-repo mirror the stock prefix maps to


def model_refs(text):
    return re.findall(r'\(model "([^"]+)"', text)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    require_local = '--require-local' in sys.argv[1:]
    root = args[0] if args else '.'

    pcb = os.path.join(root, 'TAPRX-888.kicad_pcb')
    files = [pcb]
    libdir = os.path.join(root, 'Library.pretty')
    if os.path.isdir(libdir):
        files += [os.path.join(libdir, f) for f in sorted(os.listdir(libdir))
                  if f.endswith('.kicad_mod')]

    # refs[rel_repo_path] = present?   board_used = {rel_repo_path}
    legacy_hits, refs, board_used, kinds = [], {}, set(), {}
    for fp in files:
        if not os.path.exists(fp):
            print(f"ERROR: missing {fp}"); return 2
        is_board = os.path.abspath(fp) == os.path.abspath(pcb)
        for m in model_refs(open(fp).read()):
            if any(tok in m for tok in LEGACY):
                legacy_hits.append((os.path.relpath(fp, root), m))
            elif m.startswith(LOCAL_PREFIX):
                rel = m[len('${KIPRJMOD}/'):]                 # 3d/<file>
                refs.setdefault(rel, os.path.exists(os.path.join(root, rel)))
                kinds[rel] = 'custom'
                if is_board:
                    board_used.add(rel)
            elif m.startswith(STOCK_PREFIX):
                sub = m[len(STOCK_PREFIX):]                   # <pkg>.3dshapes/<file>
                rel = os.path.join(STOCK_VENDOR_DIR, sub)     # 3d/kicad-stock/...
                refs.setdefault(rel, os.path.exists(os.path.join(root, rel)))
                kinds[rel] = 'stock'
                if is_board:
                    board_used.add(rel)
            else:
                legacy_hits.append((os.path.relpath(fp, root), m))  # unexpected

    n_custom = sum(1 for k in kinds.values() if k == 'custom')
    n_stock = sum(1 for k in kinds.values() if k == 'stock')
    print(f"distinct models: {len(refs)}  (stock: {n_stock}, custom: {n_custom})")
    for rel, ok_present in sorted(refs.items()):
        tag = 'present' if ok_present else 'MISSING'
        scope = '' if rel in board_used else ' (library-only, unplaced)'
        print(f"   [{tag}] {kinds[rel]:6} {rel}{scope}")

    ok = True
    if legacy_hits:
        ok = False
        print(f"\nFAIL: {len(legacy_hits)} unresolvable/legacy model reference(s):")
        for fp, m in legacy_hits[:20]:
            print(f"   {fp}: {m}")

    missing_board = sorted(r for r in board_used if not refs.get(r))
    missing_lib   = sorted(r for r, v in refs.items() if not v and r not in board_used)

    if require_local and missing_board:
        ok = False
        print(f"\nFAIL (--require-local): {len(missing_board)} board-used model file(s) missing:")
        for r in missing_board:
            print(f"   {r}")
    if missing_lib:
        print(f"\nNOTE: {len(missing_lib)} library-only model(s) missing (unplaced "
              f"footprints; do not affect the board STEP): {', '.join(missing_lib)}")

    print("\nOK" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
