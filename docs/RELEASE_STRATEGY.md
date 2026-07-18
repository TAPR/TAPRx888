# Release Strategy

How TAPRX-888 versions the design, builds fabrication packages, and publishes
releases. Implemented by `.github/workflows/main-release.yml` (and
`dev-checks.yml` for pre-merge validation).

## Branches & CI

Flow: **`design` → `dev` → `main`**, with a `ci-docs` review surface.

- **`design`** is the designer's working branch (unprotected): the designer
  pulls down, edits, and pushes here — and nothing more. Every push runs
  `dev-checks` and publishes the results to `ci-docs`.
- **`ci-docs`** is a throwaway branch holding the latest `design` check results
  (ERC/DRC/BOM + schematic PDF), readable directly via
  `raw.githubusercontent.com` without downloading an artifact zip. It is the
  **reviewer's surface**: the reviewer reads it and decides whether to merge
  `design → dev`.
- **`dev`** is the permanent integration branch (and default branch). A merge
  here cuts a **pre-release** (see *Pre-releases*). `dev-*` feature branches may
  also be used — they get `dev-checks` on push — and merge into `dev`.
- **`main`** is the release branch. Merging `dev → main` builds and (if the
  design changed) publishes a production revision.
- Both `dev` and `main` are protected (PR required); `main` is the stricter
  release gate. `design` is intentionally **unprotected** so the designer can
  push freely.

CI:

- **`dev-checks`** runs on `design` and `dev-*` pushes and on **PRs into `dev`
  and `main`**: ERC, DRC, BOM completeness, plus schematic PDF and gerbers/drill
  as artifacts. On a **`design`** push it additionally publishes the reports to
  `ci-docs`.
- **`dev-release`** runs on every merge to `dev` and publishes/refreshes the
  **pre-release** (see *Pre-releases* below).
- **`main-release`** runs on every merge to `main` (and can be dispatched
  manually) and is responsible for `v1.0+` production releases and published
  packages.

## Versioning

Think of it as **`main` = production board spins; `dev` = the iterations toward
the next spin.**

**`main` advances to the next whole `.0`; `dev` does the minor increments** in
between. `dev`'s major line simply follows whatever `main` last shipped.

| Event | Version |
|---|---|
| `dev` merge, pre-1.0 | `0.6 → 0.7 → 0.8 …` (minor++) |
| **first `dev → main`** | **`1.0`** |
| `dev` merge, post-1.0 | `1.1 → 1.2 → 1.3 …` (minor++ in the 1.x line) |
| **next `dev → main`** | **`2.0`** |
| `dev` merge, post-2.0 | `2.1 → 2.2 …` |
| **next `dev → main`** | **`3.0`** |

- **`main` release** = `<latest main major + 1>.0`; first-ever → `1.0`. Every
  production release is a major — no auto-minor, and **no manual major decision
  needed**. Published as a normal (non-prerelease) Release so it lands as
  "Latest".
- **`dev` pre-release** = minor increment within the **current major line**, whose
  major follows the latest `main` release (`0` while pre-1.0). The first `dev`
  pre-release after a `main` `X.0` starts at `X.1`; the very first pre-release
  while pre-1.0 uses the seed (`0.6`). Published with `--prerelease` so it never
  claims "Latest".

**GitHub Releases are the source of truth** for the version — no number lives in
the design files. Tags are `v<MAJOR>.<MINOR>`; the title matches (pre-releases add
a `(pre-release)` suffix). The policy is implemented **once** in
`scripts/next_version.sh` (unit-tested offline by `scripts/test_next_version.sh`)
and called by both lanes, so `dev` and `main` can't drift apart.

### Pre-releases (dev lane)

`dev-release` runs on every merge to `dev` and publishes a `--prerelease`:

- Computes the next `dev` version via `scripts/next_version.sh dev` and publishes
  when a design file changed since the last release (of any kind); docs/CI/
  script-only merges are a no-op.
- **First run seeds the line** from the design at `dev` HEAD — automated, no
  manual tag.
- **Does not retire at 1.0.** After `main` ships `1.0`, `dev` continues in the
  `1.x` line (`1.1`, `1.2`, …) building toward the next `main` (`2.0`); after
  `2.0` it runs `2.x`; and so on.

Both lanes accept the same manual `version` override / `dry_run` inputs.

## When is a new revision cut?

`main-release` publishes a **new** revision **only when a design file changed
since the last release**. Docs/CI/script-only merges are a **no-op** — they run
the workflow, determine nothing changed, and stop without building or publishing.

**Design files** (a change to any of these triggers an uprev):

- `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`, `*.kicad_dru`, `*.kicad_sym`
- `Library.pretty/**`, `fp-lib-table`, `sym-lib-table`

**Not design files** (never trigger an uprev): `README.md`, `docs/**`,
`.github/**`, `scripts/**`, and `*.kicad_prl` (editor/UI state).

The comparison is made against **the last release's commit**, not just the
merge's own diff — so a design edit that landed in an earlier (unpublished)
commit is still caught, and a later docs-only merge cannot mask it.

## Manual override — how a maintainer operates it

The workflow listens to **both** an automatic trigger (`push` to `main`) and a
manual one (`workflow_dispatch`). The manual path is driven entirely by inputs —
no YAML editing.

**GitHub web UI:**

1. Repo → **Actions** → **main-release** (left sidebar).
2. **Run workflow ▾** (top-right).
3. Fill the form:
   - **Use workflow from** — for a real release pick **`main`**.
   - **version** — force a specific number; **blank** = automatic (`main` → the
     next whole `.0`).
   - **dry_run** — tick to build + upload artifacts but publish nothing.
4. **Run workflow**.

**gh CLI:**

```sh
gh workflow run main-release.yml --ref main -f version=2.5      # force a specific number
gh workflow run main-release.yml --ref main -f dry_run=true     # validate only
gh workflow run main-release.yml --ref main -f version=1.4 -f dry_run=true
```

`version` sets the published version and skips auto-detection. Re-running with an
existing version is **idempotent**: the job refreshes that release's assets
(`gh release upload --clobber`) instead of failing — so it doubles as the
"re-publish / fix a release" button.

| Goal | Inputs |
|---|---|
| Normal production release | *(none — merging `dev → main` auto-cuts the next `.0`)* |
| Re-publish / fix a release | `version: <existing>` (e.g. `1.4`) |
| Force a specific number | `version: 2.5` (rare) |
| Validate the pipeline | `dry_run: true` |

> The **Run workflow** button only appears once `main-release.yml` is on the
> **default branch** (`dev`). Dispatching requires write/Actions permission.
> Until then (and any time), the **PR preview build** below validates the
> pipeline from the pull request itself.

### Dry run (build without publishing)

`dry_run: true` builds the full turnkey package and uploads it as **run
artifacts** (`release-package`) **without** publishing a release. It forces a
build even when no design file changed, so the pipeline (e.g. a KiBot config
change) can be validated before you commit to a real release. Provenance is
still injected, so the artifacts carry the version they *would* be published
under.

### PR preview build (no button needed)

Every **pull request** into `dev` or `main` that touches the design or the
release pipeline runs `main-release` in **forced dry-run** automatically. The
full package is built and attached to the run as the `release-package`
artifact — download it straight from the PR's **Checks** tab to inspect exactly
what a release would contain, before merging. The `release` job is gated on
`publish==true` (never set for PR events), so a PR can never publish. This also
sidesteps the "Run workflow button only exists on the default branch" limitation
during initial bring-up: you can validate the pipeline from the PR itself.

### Optional approval gate

To require a human "Approve" before **every** publish (automatic or manual),
create a GitHub **Environment** named `release` with a required reviewer and
uncomment `environment: release` on the `release` job. Build and package still
run automatically; only the `gh release create` waits behind the approver.

## Provenance (`${REVISION}` and `${GIT_HASH}`)

Both are **injected at build time** (`scripts/inject_provenance.py`) into the
design and rendered into the schematic/PCB **title block** and the **bottom
silkscreen**. Nothing is committed back to the design files — the placeholders
committed in the design (`DEV` / `dev`) only apply to local opens.

- `${REVISION}` — the version being published, stamped into the `rev` field of
  **every** schematic sheet (root + `Front_End` + `refclk`) and the board, so no
  sub-sheet page renders a stale `DEV`.
- `${GIT_HASH}` — **the last commit that touched a design file**, not `HEAD`.
  Written to the `GIT_HASH` project text variable.

Stamping the *design* commit (rather than the build's `HEAD`) keeps the mark
truthful and stable: a docs-only commit never changes it, and the same physical
design never ends up stamped with two different hashes.

## Release assets

Each release attaches **version-stamped** assets, so a file that is downloaded
and emailed around names its own version in the filename — not only in the
content (the recurring "which version is this PDF?" problem). The schematic and
assembly PDFs *inside* `…-fabrication.zip` are stamped too, so a document pulled
out of the unzipped folder is just as obvious.

| Asset (`v<REV>` = e.g. `v0.5`) | Contents |
|---|---|
| `TAPRX-888-v<REV>-schematic.pdf` | Schematic (direct download, no unzip) |
| `TAPRX-888-v<REV>-assembly.pdf` | Assembly drawing — top + bottom placement (F/B.Fab + silk + edge), framed |
| `TAPRX-888-v<REV>-gerbers.zip` | Gerbers + drill (JLCPCB-ready) |
| `TAPRX-888-v<REV>-fabrication.zip` | Full package: gerbers, drill, LCSC BOM, CPL, interactive BOM, schematic + assembly PDFs, and a `VERSION.txt` stamped with the exact version + commit |

The git hash also lives inside the files and in the release title/tag.

> **Permalink note:** because the version is in the filename, there is no fixed
> `…/releases/latest/download/<name>` path. Link people to the **release page**
> (or `…/releases/latest`), which shows the version prominently — that is the
> stable entry point. Gerber files *inside* the zips keep their standard
> KiCad/JLCPCB names (consumed as a set; the containing zip carries the version).

> **Scope notes (Phase A):**
> - A **basic** assembly drawing (top/bottom placement, framed) is included. The
>   fully composited, board-normalized **assembly** and multipage
>   **fabrication-drawing** PDFs (`scripts/gen_docs.sh` in usb3-fiber) are a
>   planned Phase B follow-up.
> - **STEP (3D model) and 3D renders** are not yet in the package. The
>   footprints reference custom 3D models via `${TIS}`/`${KISYS3DMOD}`, which
>   aren't in the CI image, so KiBot can't resolve them. Restoring them needs
>   that model library provisioned in the CI image (or the 3D paths
>   remapped to KiCad's standard packages). The KiBot `step`/`render_*` outputs
>   remain defined for then.

## Edge cases

- **First production release:** no prior non-prerelease → `v1.0` (always
  publishes — it's the promotion of the current design to production).
- **`dev` after a `main` release:** `dev`'s major follows the latest `main`, so
  the first pre-release after `1.0` is `1.1` (not `0.x`, not `2.0`); pre-releases
  are `--prerelease` so they never advance the `main` number.
- **Doc-only merge after a design change is already released:** no-op on either
  lane — the released design is unchanged.
- **`main` merge with no design change since the last production release:** no-op
  — a production major is never spent on nothing.
