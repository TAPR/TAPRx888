# Contributing to TAPRX-888

How we collaborate on this KiCad project: keep the design moving, keep everyone's
work safe.

## The one fact that shapes everything

KiCad `.kicad_sch`/`.kicad_pcb` files **cannot be meaningfully merged** — two
people editing the design at once overwrite each other. So the design is edited by
**one person at a time**; everything else merges normally via pull requests. That
single fact splits the work into two lanes.

## Two lanes

- **`design`** — PCB, mechanical, and end-plate design work (schematic, layout,
  libraries, the enclosure/plates). One person at a time — see the baton below.
- **`dev-*`** — docs, CI, design rules, BOM tooling, and everything else;
  short-lived feature branches opened as PRs into `dev`.

The branch flow (`design → dev → main`), CI lanes, versioning, and branch
protection all live in **[docs/RELEASE_STRATEGY.md](docs/RELEASE_STRATEGY.md)** —
this doc covers only how we work together.

## Who does what

- **Design authority — Paul Elliott (WB6CXC).** Schematic, PCB, libraries, and
  mechanical are Paul's; design decisions are his call. Owns `design`.
- **Integration & production — David and George (K9TRV).** Reviews, CI, merges,
  releases, procurement, and JLCPCB fab — so the designer needn't context-switch
  into branch mechanics.
- **Everyone.** Reviews changes and files issues.

## The design baton (edit lock)

Only one person edits the board at a time, so pass a baton:

1. Say **"taking the design"** in Signal and **pull first**.
2. Edit in KiCad; pull-to-push in one sitting is ideal.
3. **Commit → push**, then say **"design is free."**

No version numbers in filenames, no zip uploads — Git is the archive and the repo
is the one authoritative copy; point KiCad at the checked-out repo, not a local
copy. Maintainers pick it up from there; the integration + sync-`design`-down
steps are in **[docs/INTEGRATION_RUNBOOK.md](docs/INTEGRATION_RUNBOOK.md)**.

## Libraries

`Library.kicad_sym` and `Library.pretty/` are committed and **authoritative** — no
personal/global library is needed to open the project or get a clean ERC, so every
machine and CI see the same result.

## Issues

- **One issue = one item**, "clear is kind": the specific change, a screenshot
  where it helps, and the datasheet/appnote link that backs it.
- **Assigned = agreed and ready.** An unassigned issue is still under discussion.
- **Closed only when the fix is in the design *and* confirmed by a second person**
  (including the design authority). A clean ERC/DRC is necessary, not sufficient.
- **Validate findings before acting — especially AI output.** Check every claim
  against the current design *and* the closed issues before treating it as real; a
  confident-sounding finding can still be wrong. Pointing an AI at the design? Read
  **[docs/AI_REVIEW.md](docs/AI_REVIEW.md)** first.

## The one shared file

`.kicad_pro` (board settings, DRC rules, net classes) is touched by **both** lanes
— KiCad rewrites it during design work, and it's where DRC/net-class changes live.
So board-settings and DRC-rule changes go through the **design baton** too, rather
than landing on `dev` while the design is being edited.
