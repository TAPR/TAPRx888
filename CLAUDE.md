# CLAUDE.md — Working Agreement for `TAPRX-888`

Guidance for Claude (and any agent) working in this repository. This is a
**KiCad hardware project**, not a software codebase — the "code" is a schematic,
a PCB layout, and a component library, and the "build" is a set of
manufacturing outputs produced by `kicad-cli`.

## Project

TAPRX-888 is a simplified, HF-only software-defined radio (SDR) receiver based
on the **RX-888**. It is a proof-of-concept design: HF-only (no VHF up/down
converter), on a larger **6-layer** PCB with no bottom-side components and 0603
passives, aimed at improved thermal and RF layout. Notable features: improved,
bypassable RF input filtering; an **external reference-clock input with
auto-switching**; an attenuated filter-bypass injector port (for timesync); and
an SPI boot PROM configurable as USB boot, SPI boot, or SPI boot with USB
fallback.

Core devices: **LTC2208** 16-bit ADC, **Si5351** clock generator, Infineon
**EZ-USB FX3 (CYUSB301x)** SuperSpeed USB3 controller, and an **MX25L3233F**
SPI flash. Datasheets for all of these live on the
[project wiki](https://github.com/TAPR/TAPRx888/wiki/Reference-Documents).

## Repository layout

The KiCad project lives at the **repo root** (flattened from the former
`TAPRX-888 KiCad/` subdirectory).

- `TAPRX-888.kicad_pro / .kicad_sch / .kicad_pcb` — the design. The schematic is
  **hierarchical**: `TAPRX-888.kicad_sch` is the root sheet and pulls in
  `Front_End.kicad_sch` and `refclk.kicad_sch`. Run ERC against the root sheet.
- `fp-lib-table` / `sym-lib-table` — project-local library tables (they use
  `${KIPRJMOD}`; keep paths relative).
- `Library.kicad_sym` + `Library.pretty/` — the project-local symbol library and
  footprints.
- `fabrication-toolkit-options.json` — JLCPCB Fabrication Toolkit export config
  (`EXCLUDE DNP: true`, so DNP parts are omitted from fab outputs).

BOM, Gerbers, and other fabrication outputs are **build products regenerated
from the schematic/PCB** (`kicad-cli sch export bom`, etc.) and are **not
committed** — CI produces them as artifacts. The schematic `LCSC Part #` fields
are the authoritative source of part numbers; `MFG`/`MPN` are derivable from the
LCSC number via the JLC/LCSC catalog.

Device datasheets and RX888 reference material live on the
[project wiki](https://github.com/TAPR/TAPRx888/wiki/Reference-Documents), not
in the repository.

**KiCad 10.0** is the project baseline (latest stable 10.0.4). The committed
files are already in the v10 format (`version 20260206`) — no format migration
is pending. Author changes with KiCad 10.

## Working agreement

- **Planning first.** For any multi-step change, write/update a short plan and
  get approval before implementing.
- **Commit & push only with explicit approval.** Never commit or push without
  being asked to.
- **Branch discipline.** The canonical flow is **`design` → `ci-docs` → `dev` →
  `main`** (see `docs/RELEASE_STRATEGY.md` and `CONTRIBUTING.md`). `dev` is the
  default branch; both `dev` and `main` are protected, `design` is not. Agent /
  infrastructure work (CI, docs, scripts, `.kicad_dru`) happens on `dev-*` feature
  branches that merge (squash) into **`dev`**; the designer works on **`design`**.
  `dev` merges (squash) into **`main`** only when cutting a release.
  **Authorization to do work is NOT authorization to create a branch** — do not
  create a branch unless the user names it. Unrelated fixes go on the current
  branch as separate commits unless directed otherwise.
- **Evidence before claims.** Do not assert a design problem or file an issue on
  untested theory. Back every finding with concrete evidence: a `grep`/file
  read, a datasheet reference, or `kicad-cli` ERC/DRC/BOM output. (Example: the
  6-layer stackup lists `In1..In4.Cu` as **signal** layers — confirm claims like
  that by reading the PCB `(layers …)` stanza, not by assumption.) Existing
  observations override untested theory. For design-level review specifically,
  `docs/AI_REVIEW.md` is the project's rule for AI reviewers: **a finding is a
  lead, never a verdict** — ground yourself in the datasheets, firmware, current
  design, and closed issues before making a claim, and never report an unverified
  finding as fact.
- **Change documentation.** Before committing a design-touching change, give the
  user a copy-pastable block with: (1) what changed and why, (2) how to
  regenerate outputs (`kicad-cli` commands), (3) how to validate (which
  ERC/DRC/BOM checks must pass), (4) regression check (re-run the CI check set).
- **No `gh` CLI here.** GitHub operations go through the GitHub MCP tools, not
  `gh`. When batch-filing findings as issues, use those tools (or offer a
  script), not `gh issue create`.

## Design-rule baseline

- Manufacturing capability reference: **JLCPCB, 6-layer process** (the assembly
  BOM targets JLC part numbers, and `fabrication-toolkit-options.json` drives
  the JLCPCB Fabrication Toolkit export). Set and validate DRC rules against it,
  and keep the board settings (`.kicad_pro` `board_design_settings`) in sync.
- Custom DRC rules live in **`TAPRX-888.kicad_dru`** — understand them before
  changing them, and keep them consistent with the `.kicad_pro`
  `board_design_settings`.

## CI, provenance & releases

**Implemented** — the full policy is in `docs/RELEASE_STRATEGY.md`; the workflows
are in `.github/workflows/`. CI runs `kicad-cli` + **KiBot** inside the public
**`ghcr.io/inti-cmnb/kicad10_auto`** image (pinned to KiCad 10.0.4), across three
workflows mirroring the `design → ci-docs → dev → main` flow:

- **`dev-checks`** — on `design`/`dev-*` pushes and PRs into `dev`/`main`: ERC
  (root schematic), DRC (PCB), and a BOM completeness check, plus schematic PDF
  and gerbers/drill as artifacts. On a `design` push it also publishes the reports
  to the `ci-docs` branch (the reviewer's surface). **Currently non-gating**
  (`ENFORCE=false`) during bring-up — the design has known ERC/DRC violations
  tracked as issues; flip `ENFORCE=true` and add required checks once the baseline
  is triaged.
- **`dev-release`** — on merge to `dev`: publishes/refreshes a **pre-release**
  (minor increment) when a design file changed.
- **`main-release`** — on merge to `main`: builds the full fabrication package
  (gerbers, drill, LCSC BOM, CPL, interactive BOM, schematic + assembly PDFs) via
  KiBot and publishes a production **GitHub Release** (next whole `.0`). **STEP /
  3D renders are not yet included** — the footprints reference custom 3D models
  absent from the CI image (issue #45); the KiBot outputs remain defined for when
  they are.

- **Revision & provenance**: `${REVISION}` and `${GIT_HASH}` are **injected at
  build time** (`scripts/inject_provenance.py`) into the title block and bottom
  silkscreen — never committed back to the design files. **GitHub Releases are the
  source of truth** for the version; no number lives in the design. `VERSION.txt`
  in the tree is a de-numbered "development snapshot," stamped with the exact
  version only inside the released package.

| Check | dev-checks | main-release |
|---|---|---|
| ERC / DRC | run (non-gating in bring-up) | gated earlier, on the PR into `main` |
| Fab artifacts (PDF / Gerbers / BOM) | artifact | full package on the Release |

## Useful `kicad-cli` commands (KiCad 10)

Run from the repo root.

```sh
kicad-cli sch erc          TAPRX-888.kicad_sch --output erc.rpt --exit-code-violations
kicad-cli pcb drc          TAPRX-888.kicad_pcb --output drc.rpt --exit-code-violations
kicad-cli sch export pdf   TAPRX-888.kicad_sch --output TAPRX-888-schematic.pdf
kicad-cli sch export bom   TAPRX-888.kicad_sch --output bom.csv
kicad-cli pcb export gerbers TAPRX-888.kicad_pcb --output gerbers/
kicad-cli pcb export drill   TAPRX-888.kicad_pcb --output gerbers/
kicad-cli pcb export pos     TAPRX-888.kicad_pcb --output cpl.csv   # pick-and-place
kicad-cli pcb export step    TAPRX-888.kicad_pcb --output TAPRX-888.step
```

## Reference docs

- [Project wiki → Reference Documents](https://github.com/TAPR/TAPRx888/wiki/Reference-Documents)
  — LTC2208, Si5351, EZ-USB FX3, MX25L3233F datasheets and RX888 reference
  material (moved out of the repo to keep it lean).
