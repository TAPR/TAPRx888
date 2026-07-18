# Contributing to TAPRX-888

How we collaborate on this KiCad project. The goal is simple: keep the design
moving, keep everyone's work safe, and keep each person doing what they do best.

## The one fact that shapes everything

KiCad's `.kicad_sch` and `.kicad_pcb` are text files, but a **layout or
schematic edit cannot be meaningfully merged** — two people editing the design
at the same time overwrite each other. So the design is edited by **one person
at a time**. Everything else (CI, design rules, BOM tooling, docs) merges
normally and follows ordinary pull requests.

That single fact is why the workflow below is split into two lanes.

## Who does what

- **Design authority — Paul Elliott (WB6CXC).** The schematic, the PCB layout,
  and the symbol/footprint libraries are Paul's work. Design decisions are his
  call. Paul owns the `design` branch and is the one who edits the board.
- **Integration & production — David and George (K9TRV).** Reviews, CI, merges,
  releases, part procurement, and JLCPCB fabrication. They handle the Git
  integration so the design authority doesn't have to context-switch into
  branch mechanics mid-layout.
- **Everyone.** Reviews changes and files issues.

## Branches

- **`main`** — released, buildable board revisions. Tagged. Protected.
- **`dev`** — the integration branch and the default branch. Where design work
  and infrastructure work come together before a release. Protected.
- **`design`** — the design authority's working branch (see below).
- **`dev-*`** — short-lived feature branches for everything that isn't the board
  itself (CI, `.kicad_dru`, BOM scripts, docs).

Flow: work → `dev` → `main` (at release). Merges into `dev` and `main` are
**squash** merges.

## Lane 1 — the design (schematic / PCB / libraries)

The design is edited on the **`design`** branch, one sitting at a time. Because
those edits live on their own branch, they're never tangled up with in-flight
infrastructure work, and integration is handled by the maintainers.

### The design workflow — day to day (GitHub Desktop)

The design authority stays on the `design` branch and repeats the same three
steps every session:

> 1. **Pull** (get the latest)
> 2. **Edit in KiCad** — schematic / PCB / libraries
> 3. **Commit → Push**

Then say **"design is free"** in Signal so the next person knows the board is
available. That's the whole routine — no branch switching, no merge wrangling.
The maintainers pick the change up from there.

### The "design baton" (edit lock)

Because only one person can safely edit the board at a time, we pass a baton:

1. Before editing, say **"taking the design"** in Signal, and **Pull first**.
2. Keep the session focused — pull to push in one sitting is ideal.
3. **Commit → Push**, then say **"design is free."**
4. Nobody else edits the design files until the baton is free again.

House rules that keep the history clean:

- **No version numbers in filenames** and **no zip uploads.** Git already
  archives every version; the files in the repo are the one authoritative copy.
- Point KiCad at the project checked out from GitHub — the repo is the source of
  truth, not any single machine.

## Lane 2 — everything else (mergeable work)

CI, `.kicad_dru`, net classes, BOM scripting, README/CLAUDE.md, and similar:

1. Branch from `dev`: `dev-<short-description>`.
2. Commit, push, open a pull request into `dev`.
3. CI runs; a maintainer reviews and squash-merges.

## Integration & releases (maintainers)

> Step-by-step for the occasional infra (`dev-*`) merge — including the
> **sync-`design`-down** that keeps the designer safe — is in
> **`docs/INTEGRATION_RUNBOOK.md`**. The summary below is the shape of it.

- A **standing pull request, `design` → `dev`**, stays open. Each push to
  `design` re-runs CI (ERC/DRC/BOM) and publishes the reports to the **`ci-docs`**
  branch — a review surface readable straight from `raw.githubusercontent.com`,
  no artifact download needed. David or George reviews those results and
  squash-merges into `dev` when a change is good.
- After a design change merges into `dev`, sync `design` back up to `dev` at a
  moment when the baton is free, so the branch doesn't drift.
- **`dev` → `main`** is a release: merged by consensus between David and George.
  The `main-release` CI then builds the fabrication package and publishes a
  GitHub **Release** (`v1.0`, `v2.0`, … — see `docs/RELEASE_STRATEGY.md`); that
  published package is what George procures and fabricates from.
- Either David or George may merge into `dev`; release merges to `main` are by
  consensus.

## Guardrails

`main` and `dev` are **protected branches** — changes arrive only through a
reviewed merge, and *nobody* pushes to them directly (maintainers included).
This protects released revisions and the shared integration branch from
accidental overwrites.

Repo setup (Settings → Branches → Add branch protection rule), for each of
`main` and `dev`:

- Require a pull request before merging.
- Do not allow direct pushes / require the change to go through a PR.
- Do not allow force pushes.

Day-to-day design work is unaffected — the `design` branch stays open for the
designer to push to freely; it reaches `dev`/`main` only through the reviewed
merge above.

## Libraries

The project-local `Library.kicad_sym` and `Library.pretty/` are committed and
**authoritative**. Nobody needs a personal/global library installed to open the
project or to get a clean ERC — this is deliberate, so every machine and CI see
the same result.

## CI is the shared referee

ERC (root schematic), DRC (PCB), and a BOM completeness check run in a pinned
KiCad 10 CI container on every push to `design` and every pull request into
`dev`/`main`. The CI report — not any one person's local run — is the shared
source of truth, so there's never a question of "whose ERC do we trust." CI also
publishes the schematic PDF, Gerbers, and BOM as downloadable artifacts, and
mirrors the `design` results to the `ci-docs` branch for easy review.

## Issues

- **One issue = one item**, written "clear is kind": the specific change, a
  screenshot where it helps, and a link to the datasheet / application note /
  reference that backs it.
- **Assigned = agreed and ready to be worked.** An *unassigned* issue is still
  under discussion — don't start resolving it, and don't take offense if an
  unassigned one isn't picked up yet.
- **Closed only when the fix is in the design *and* confirmed by a second
  person, including the design authority.** A clean ERC/DRC is necessary but not
  sufficient — it lowers risk, it doesn't prove the design works.
- **Validate findings before acting on them** — especially automated/AI review
  output. Check every claim against the current design *and* the closed issues
  before treating it as real; a confident-sounding finding can still be wrong.
  If you're pointing an AI at the design, read **`docs/AI_REVIEW.md`** first — it
  is the same rule in full, with how to ground the model so it helps instead of
  misleads.

## One shared file to watch

`.kicad_pro` (board settings, DRC rules, net classes) is touched by **both**
lanes — KiCad rewrites it during design work, and it's also where net-class /
DRC infrastructure changes live. It's the one file where the two lanes can
collide. So: **board-settings and DRC-rule changes go through the design baton
too** (announce them, or hand them to the design authority to apply), rather
than landing on `dev` while the design is being edited.
