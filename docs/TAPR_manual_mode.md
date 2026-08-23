# TAPR manual-mode runbook — keep the 3-tier flow, turn CI off

**Purpose.** The middle path between *keep full CI* and *roll all the way back*
(`docs/TAPR_rollback.md`): turn the robots off but keep the `design → dev → main`
structure and hand the **same tools** to a human. Branches, design, and scripts
all stay — only the workflow automation goes.

> The automation is **only the six workflow YAML files**. Everything they call
> (`run_checks.sh`, `build_release.sh`, `next_version.sh`, `inject_provenance.py`,
> `build_endplates.sh`, `assemble_mechanical.py`, `assemble_glb.py`,
> `make_3d_viewer.py`, the KiBot config) are standalone hand-tools. Turning CI off
> just stops the robots; re-enabling is restoring six files.

Throughout, **`origin` = the TAPR repo**.

---

## What changes

**Remove** (the automation):

- `.github/workflows/dev-checks.yml`
- `.github/workflows/dev-release.yml`
- `.github/workflows/main-release.yml`
- `.github/workflows/mechanical-ci.yml`
- `.github/workflows/mechanical-build.yml`
- `.github/workflows/endplate-release.yml`
- the **`ci-docs`** branch (produced by CI; goes stale with nothing publishing to it)

**Keep** (now operated by hand):

- Branches **`design → dev → main`** — untouched.
- `scripts/*` — the manual toolkit (see *Operating the flow by hand*), including
  `run_checks.sh`, `build_release.sh`, `next_version.sh`, `inject_provenance.py`,
  `build_endplates.sh`, `assemble_mechanical.py`, `assemble_glb.py`,
  `make_3d_viewer.py`. Run these by hand instead of on push.
- `fabrication-toolkit-options.json` — JLCPCB export straight from the KiCad
  Fabrication Toolkit plugin GUI, no command line.
- `TAPR.kicad_wks`, `VERSION.txt`, the design files, and the docs.

**Branch protection:** **`main` only** — releases stay safe; `dev` and `design`
left open for day-to-day work.

---

## The switch-off procedure (needs TAPR admin)

1. **Delete the workflow files.** They must be gone on *every* branch that could
   trigger them (`design`, `dev`, `main`), or Actions still fires from whichever
   branch carries one. Remove on `dev`, then propagate by the normal merges.

   ```sh
   git switch dev && git pull
   git rm .github/workflows/dev-checks.yml \
          .github/workflows/dev-release.yml \
          .github/workflows/main-release.yml \
          .github/workflows/mechanical-ci.yml \
          .github/workflows/mechanical-build.yml \
          .github/workflows/endplate-release.yml
   git commit -m "Turn CI off; operate the 3-tier flow manually (docs/TAPR_manual_mode.md)"
   git push origin dev
   # then carry it to main and design:
   #   merge dev -> main (removes them from main)
   #   sync design up to dev (removes them from design)
   ```

2. **Delete the `ci-docs` branch:**

   ```sh
   git push origin --delete ci-docs
   ```

3. **Set protection to `main`-only:** Settings → Branches / Rulesets → remove the
   `dev` (and any `design`) rules; keep the `main` rule (require a PR, block
   force-push and deletion).

4. **(Optional, belt-and-suspenders)** Settings → Actions → General → **Disable
   Actions** for the repo, so nothing runs even if a stray workflow reappears.

---

## Operating the flow by hand

### Designer — unchanged

Pull `design`, edit in KiCad, commit, push to `design`, say "design is free."

### Reviewer — check a design change *(replaces `dev-checks` / `ci-docs`)*

```sh
git switch design && git pull
scripts/run_checks.sh          # ERC + DRC + BOM completeness -> reports/
# read reports/erc.rpt, reports/drc.rpt, reports/bom_check.txt, reports/*.pdf
```

If it looks good, merge `design → dev` (`dev` is unprotected in this mode), then
sync `design` back up to `dev` when the baton is free.

### Cut a release *(replaces `dev-release` / `main-release`)*

```sh
git switch main && git pull            # or dev, for a pre-release
REV=1.0                                # pick the number (next_version.sh can suggest it)
# GIT_HASH = last commit that touched a design file (same rule CI used):
GIT_HASH=$(git log -1 --format=%h -- '*.kicad_sch' '*.kicad_pcb' '*.kicad_pro' \
             '*.kicad_sym' 'Library.pretty' fp-lib-table sym-lib-table)

REVISION=$REV GIT_HASH=$GIT_HASH scripts/build_release.sh    # -> out/

( cd out && zip -qr "../TAPRX-888-v$REV-fabrication.zip" . )
gh release create "v$REV" "TAPRX-888-v$REV-fabrication.zip" \
  --repo TAPR/TAPRx888 --title "v$REV" \
  --notes "Fabrication package for v$REV (design commit $GIT_HASH). Built manually."
```

`build_release.sh` injects provenance and stamps `VERSION.txt`, producing the
**same stamped outputs** CI did. It needs the same tools locally (`kicad-cli`,
`kibot`, `python3`, `ghostscript`/`poppler-utils`); easiest is the same public
image:

```sh
docker run --rm -v "$PWD":/ws -w /ws \
  -e REVISION=$REV -e GIT_HASH=$GIT_HASH \
  ghcr.io/inti-cmnb/kicad10_auto:1.9.0-6_k10.0.4_d13.2 \
  scripts/build_release.sh
```

### End plates *(replaces `endplate-release`)*

Cut the independent `endplates-vX.Y` package by hand with `scripts/build_endplates.sh`
(uses `inject_provenance.py`), then `gh release create endplates-v$REV …`.

### Mechanical fit-check *(replaces `mechanical-ci` / `mechanical-build`)*

Build the assembly STEP + GLB + viewer by hand:
`scripts/assemble_mechanical.py`, `scripts/assemble_glb.py`,
`scripts/make_3d_viewer.py`.

### Fab outputs with no command line

The JLCPCB Fabrication Toolkit KiCad plugin reads
`fabrication-toolkit-options.json`, so a maintainer can export gerbers / BOM /
CPL straight from KiCad's GUI.

---

## Docs to touch when switching

- `docs/RELEASE_STRATEGY.md` and `CONTRIBUTING.md` describe the *CI-driven* flow.
  Add a "manual mode" note (or trim the CI sections) so they say checks and
  releases are run by hand via `scripts/`.
- `VERSION.txt` is already de-numbered; in manual mode you get the stamp by
  running `build_release.sh` yourself.

---

## Turning CI back on

Restore the six workflow files from history, push to `dev`, re-add `dev`
protection. The scripts never left, so CI and manual mode use the same tooling.

---

## What this does NOT do

- It does **not** touch the design or the branch structure — only the automation.
- It is **not** a rollback to pre-migration (that's `docs/TAPR_rollback.md`).
- Existing GitHub Releases are left as they are.
