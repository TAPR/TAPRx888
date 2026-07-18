# TAPR bring-over runbook — migrating ringof's work into TAPR

**Purpose.** The forward migration — the mirror of `docs/TAPR_rollback.md`. It
brings ringof's flattened design + CI/versioning/docs onto **TAPR/TAPRx888** as
the canonical repo, using the **replay-on-top-of-`c01bece8`** model: one
migration commit, `main` advances by a **fast-forward** (no force-push), and
`c01bece8` stays a real ancestor so rollback is trivial.

Cross-refs: `docs/TAPR_rollback.md` (undo), `docs/TAPR_manual_mode.md`
(de-automate but keep the flow).

---

## What we're bringing, and why it's safe

- **The design is materially identical.** TAPR's `c01bece8` ("proper update")
  and ringof's `dev` share ancestor `3fb7ab5`. The real design files
  (`.kicad_pcb/.sch/.pro`) differ by only ~5–9 lines each — ringof's provenance
  edits (silkscreen / `REPO` / rev), not electrical change.
- **What ringof fixes is the folder mess.** `c01bece8` still carries the old
  `TAPRX-888 KiCad/` **and** `TAPRX-888 KiCad - Copy/` duplicate directories —
  the "overlapping folders" that nearly triggered a delete-and-restart. ringof's
  tree is **flattened to the repo root** and adds CI, scripts, and docs.
- **Histories diverge**, so this is not a merge — we replay ringof's tree as one
  commit whose parent is `c01bece8`.

## Readiness (already true on ringof `dev`)

- **Tree is TAPR-ready — no content edits at migration time.** De-ringofed
  (`REPO` → `github.com/TAPR/TAPRx888`, wiki/release links → TAPR); workflows use
  `${GITHUB_REPOSITORY}` so they're portable; `VERSION.txt` is de-numbered. The
  only literal "ringof" strings left are inside these runbook docs, which
  legitimately describe the ringof→TAPR relationship.
- **CI is proven** green end-to-end in ringof (public INTI-CMNB image, the
  `design → ci-docs → dev → main` flow, release packaging).

---

## Settled decisions

1. **First `v1.0` is deferred — the migration is quiet.** GitHub Releases are
   per-repo, so TAPR starts with **zero** releases, and leaving Actions on while
   seeding would auto-cut a `v0.6` pre-release (first `dev` push) and a `v1.0`
   production release (first `main` push). To avoid that, **seed with Actions
   disabled** (step 1); the team cuts the first real `v1.0` deliberately later
   (step 8).
2. **Legacy PRs #4 and #30 are already closed.** Their `refs/pull/4/head` and
   `refs/pull/30/head` refs linger (GitHub keeps them after a PR closes) but are
   harmless and need no action — they target the pre-flatten `main` and stay
   closed.

---

## Repo settings to set on TAPR (once)

- **Settings → Actions → General → Workflow permissions → Read and write.** The
  `ci-docs` publish step and the release jobs push via the built-in
  `GITHUB_TOKEN`; the default read-only token would fail them. No external
  secrets are needed (public image, no registry auth).

---

## Dry-run rehearsal (do it once, in a throwaway repo)

The CI *behavior* is already proven in ringof; what this rehearses is the
**seeding sequence** against a `c01bece8`-shaped repo.

```sh
# 1. Create an empty scratch repo (GitHub UI, or: gh repo create you/tapr-mige --private)
git remote add scratch https://github.com/<you>/tapr-mige.git
# 2. Seed it with TAPR's current state:
git push scratch tapr/main:main
# 3. Run steps 0–7 below against 'scratch' instead of 'tapr'. Watch dev-checks go
#    green, ci-docs populate, and (optionally) a release cut. Then test the
#    rollback runbook against it.
# 4. Delete the scratch repo when satisfied.
```

---

## The live bring-over

Work from a local clone that has **both** remotes:

```sh
git remote -v      # origin -> ringof/TAPRx888 ; tapr -> TAPR/TAPRx888
git fetch tapr origin --tags
```

### 0. Anchor first — the restore point (see TAPR_rollback.md, step zero)

```sh
TAG="pre-migration-$(date +%Y-%m-%d)"
git tag -a "$TAG" tapr/main -m "TAPR state before the ringof bring-over"
git push tapr "$TAG"
git push tapr tapr/main:refs/heads/pre-migration    # human-friendly restore branch
```

### 1. Disable Actions (so seeding pushes don't fire CI / cut releases)

Settings → Actions → General → **Disable actions**. Re-enabled in step 6.

### 2. Build the migration commit (tree = ringof `dev`, parent = `c01bece8`)

```sh
MIG=$(git commit-tree "$(git rev-parse origin/dev^{tree})" -p tapr/main \
      -m "Bring over ringof: flatten to repo root; add CI, versioning, docs")
git branch -f dev "$MIG"
git diff --quiet origin/dev dev && echo "dev tree == ringof/dev ✓"
```

Intuitive equivalent, if you prefer working-tree steps:

```sh
git checkout -B dev tapr/main
git rm -rq .
git checkout origin/dev -- .
git commit -m "Bring over ringof: flatten to repo root; add CI, versioning, docs"
```

### 3. Push the branches to TAPR

```sh
git push tapr dev:dev       # new branch
git push tapr dev:main      # FAST-FORWARD c01bece8 -> migration commit (no --force)
git push tapr dev:design    # new branch (the designer's working branch)
```

(`ci-docs` is created automatically by the first `design`-push CI run — do not
seed it by hand.)

### 4. Set the default branch

Settings → General → **Default branch → `dev`**.

### 5. Turn on branch protection

- **`dev`** — require a PR; block force-push and deletion.
- **`main`** — same, as the stricter release gate.
- **`design`** — **no protection** (the designer pushes freely).

(Protection is added *after* the seeding pushes so it doesn't block them.)

### 6. Re-enable Actions

Settings → Actions → General → enable. Nothing fires from this alone: seeding
happened with Actions off, and all three branches already sit at the migration
commit (no pending design change).

### 7. Smoke test — prove the live flow, low-stakes

Push a trivial **non-design** change (e.g. a doc typo) to `design`:

```sh
git switch design && git pull
# edit any doc
git commit -am "smoke test: confirm CI on TAPR" && git push
```

Confirm: `dev-checks` runs **green**, and the **`ci-docs`** branch is created
with the review set (`erc.rpt`, `drc.rpt`, `bom.csv`, `bom_check.txt`,
schematic PDF). No release is cut (not a design file).

### 8. First real release — when the team is ready (deliberate)

Merge `design → dev` to cut the first pre-release, then `dev → main` (or dispatch
`main-release` manually) to cut **`v1.0`** production. See
`docs/RELEASE_STRATEGY.md`.

---

## Verification — TAPR is migrated

- **Branches:** `main`, `dev`, `design`, `ci-docs` (+ the `pre-migration` anchor,
  + any surviving PR refs).
- `git fetch tapr && git diff --quiet origin/dev tapr/dev && echo "dev == ringof/dev ✓"`
- **`main` is a fast-forward child of the restore point:**
  `git merge-base --is-ancestor c01bece8 tapr/main && echo "c01bece8 is an ancestor ✓"`
- **Default branch** = `dev`; **protection** = dev+main protected, design open.
- **Actions** green; **`ci-docs`** populated.

## If it goes wrong

Use `docs/TAPR_rollback.md`. Because `main` only **fast-forwarded**, the reverse
is especially clean: reset `main` back to the `pre-migration` anchor and delete
`dev` / `design` / `ci-docs`. Nothing was lost — `c01bece8` is both the anchor
and a live ancestor.

---

## Why this order

- **Anchor before touching anything** → the pre-migration state is unloseable.
- **Actions off during seeding** → no surprise `v0.6`/`v1.0` from the seed pushes;
  the team owns the first release.
- **Protection after the pushes** → protection would otherwise block seeding
  `dev`/`main`.
- **`main` by fast-forward, not force** → TAPR's history stays continuous and the
  rollback stays a one-liner.
