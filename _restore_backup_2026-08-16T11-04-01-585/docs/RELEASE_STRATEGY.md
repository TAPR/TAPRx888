# Release Strategy

How TAPRX-888 versions, builds, and publishes. Implemented in
`.github/workflows/` (`dev-checks`, `dev-release`, `main-release`,
`endplate-release`, `mechanical-ci`, reusable `mechanical-build`) and
`scripts/next_version.sh` (offline-tested by `scripts/test_next_version.sh`).

## Branches & CI

Flow: **`design` → `dev` → `main`**, with a `ci-docs` review surface.

- **`design`** — designer's working branch (unprotected). Each push runs
  `dev-checks` and publishes results to `ci-docs`.
- **`ci-docs`** — throwaway branch holding the latest `design` check results
  (ERC/DRC/BOM + schematic PDF), readable via `raw.githubusercontent.com`; the
  reviewer reads it to decide `design → dev`.
- **`dev`** — integration + default branch; protected. A qualifying merge cuts a
  `v0.x` **pre-release**. `dev-*` feature branches also run `dev-checks`.
- **`main`** — release branch; protected, stricter gate. `dev → main` cuts a
  production revision.

Merges into `dev` and `main` are **squash** merges. Which work goes on which
branch (design/PCB/mechanical vs docs/CI) is in `CONTRIBUTING.md`.

CI lanes:

- **`dev-checks`** — on `design`/`dev-*` pushes and PRs into `dev`/`main`: ERC,
  DRC, BOM completeness + schematic PDF / gerbers artifacts; on `design`, also
  publishes to `ci-docs`.
- **`dev-release`** — on merge to `dev`: the `v0.x` combined pre-release (below).
- **`main-release`** — on merge to `main` (or dispatch): production `vX.0`.
- **`endplate-release`** — on merge to `main`: independent `endplates-vX.Y` lane.
- **`mechanical-ci`** / reusable **`mechanical-build`** — mechanical assembly +
  Pages viewer for `design`/`dev-*` (`dev` is handled by `dev-release`).

## Versioning

**`main` = production spins (whole majors); `dev` = the minors between.** `dev`'s
major follows whatever `main` last shipped.

| Event | Version |
|---|---|
| `dev` merge, pre-1.0 | `0.6 → 0.7 …` |
| first `dev → main` | **`1.0`** |
| `dev` merge, post-1.0 | `1.1 → 1.2 …` |
| next `dev → main` | **`2.0`** |

- **`main`** = `<latest main major + 1>.0` (first ever → `1.0`); always a major,
  published as a normal Release ("Latest").
- **`dev`** = minor++ in the current major line; first after a `main` `X.0` is
  `X.1`, pre-1.0 seeds at `0.6`. Published `--prerelease`. Does **not** retire at
  1.0 — it keeps running `1.x`, `2.x`, … toward the next `main`.

**GitHub Releases are the source of truth** — no version lives in the design.
Tags `v<MAJOR>.<MINOR>`; pre-releases add a `(pre-release)` title suffix. Policy
lives once in `scripts/next_version.sh`, called by both lanes.

### `dev` combined snapshot

The `dev` pre-release is a **single combined snapshot** (unlike `main`, where
board and plates ship on separate lanes). Each qualifying `dev` merge folds into
the one `v0.x` pre-release:

- the **board** package (`scripts/build_release.sh`);
- **both end-plate** packages (`scripts/build_endplates.sh`), stamped with the
  board's `v0.x` and the end-plate design commit;
- the **mechanical assembly** — STEP + coloured GLB + self-contained 3D viewer
  (reusable `mechanical-build.yml`) — and it deploys the viewer to GitHub Pages
  (<https://tapr.github.io/TAPRx888/>).

Its trigger therefore spans board ∪ end-plate ∪ mechanical inputs
(`mechanical/**`, `3d/**`, `TAPR.kicad_wks`, the `assemble_*` / `make_3d_viewer` /
`build_endplates` scripts) — any of them cuts/refreshes it. `dev` deploys Pages
here, not via `mechanical-ci`, so the two never double-deploy.

## When is a revision cut?

Both lanes publish **only when a design file changed since the last release** (of
any kind) — compared against the last release's commit, not the merge diff, so an
earlier unpublished design edit is still caught and a later docs-only merge can't
mask it. Docs/CI/script-only merges are a no-op.

**Design files:** `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`, `*.kicad_dru`,
`*.kicad_sym`, `Library.pretty/**`, `fp-lib-table`, `sym-lib-table`.
**Not:** `README.md`, `docs/**`, `.github/**`, `scripts/**`, `*.kicad_prl`.
(The `dev` snapshot additionally treats `mechanical/**`, `3d/**`, `TAPR.kicad_wks`
and the assembler scripts as triggers — see above.)

## Provenance (`${REVISION}`, `${GIT_HASH}`)

**Injected at build time** (`scripts/inject_provenance.py`), never committed back
— the design's committed placeholders (`DEV`/`dev`) apply only to local opens.

- `${REVISION}` — the published version, stamped into the `rev` of every sheet
  (root + `Front_End` + `refclk`) and the board.
- `${GIT_HASH}` — the **last commit that touched a design file** (not `HEAD`), so
  the mark is stable across docs-only commits.

## Release assets

Each release attaches **version-stamped** assets (the filename names its own
version). PDFs inside `…-fabrication.zip` are stamped too.

| Asset (`v<REV>`) | Contents |
|---|---|
| `TAPRX-888-v<REV>-schematic.pdf` | Schematic |
| `TAPRX-888-v<REV>-assembly.pdf` | Assembly drawing (top + bottom, framed) |
| `TAPRX-888-v<REV>.step` | Board STEP — the EE↔ME interface |
| `TAPRX-888-v<REV>-gerbers.zip` | Gerbers + drill (JLCPCB-ready) |
| `TAPRX-888-v<REV>-fabrication.zip` | Full package: gerbers, drill, LCSC BOM, CPL, iBOM, PDFs, board STEP, stamped `VERSION.txt` |

> No fixed `releases/latest/download/<name>` path (version is in the filename) —
> link to the release page. Board STEP + 3D renders ship (models vendored in
> `3d/`, resolved via `KICAD10_3DMODEL_DIR`); board **connector** models are still
> absent (issue #45), so those parts are missing from the STEP/renders.

## End-plate lane (independent, `main`)

The end plates (`mechanical/endplate-{front,rear}`) release independently via
`endplate-release.yml` — a plate change never moves the board's `vX.Y`, or vice
versa.

- **Trigger:** on merge to `main`; publishes only when a plate dir or the shared
  `TAPR.kicad_wks` changed since the last endplates release.
- **Version:** both plates cut together; tags `endplates-v<MAJOR>.<MINOR>`, minor
  auto-increments (never rolls over), first → `endplates-v1.0`; major via dispatch
  `version:`. Numbered inline, separate from the board.
- **Build:** `scripts/build_endplates.sh` stamps provenance (empty `--sheets`,
  PCB-only) and exports per plate `endplate-<front|rear>-v<REV>-gerbers.zip` +
  `-fab.pdf`. No BOM/CPL (no components).

## Manual operation (board lanes)

`main-release` / `dev-release` take `workflow_dispatch` inputs — no YAML edits:

```sh
gh workflow run main-release.yml --ref main -f version=2.5   # force a number
gh workflow run main-release.yml --ref main -f dry_run=true  # build only, no publish
```

- **`version`** — force a number; blank = automatic. Re-running an existing
  version is **idempotent** (`gh release upload --clobber`) — the "re-publish /
  fix a release" button.
- **`dry_run: true`** — builds the full package as run artifacts
  (`release-package`), forces a build even with no design change, publishes
  nothing.
- **PR preview:** every PR into `dev`/`main` touching the design or pipeline runs
  a **forced dry-run** — download `release-package` from the PR's Checks tab. The
  `release` job is gated on `publish==true` (never set for PRs).
- **Approval gate (optional):** create an Environment `release` with a required
  reviewer and uncomment `environment: release` on the `release` job.

> The **Run workflow** button only appears once the workflow is on the default
> branch (`dev`); until then the PR preview validates the pipeline.

## Edge cases

- **First production release:** no prior non-prerelease → `v1.0` (always publishes).
- **`dev` after a `main` release:** major follows `main`, so the first pre-release
  after `1.0` is `1.1` (not `0.x`/`2.0`).
- **Doc-only merge, or `main` merge with no design change:** no-op on either lane.
