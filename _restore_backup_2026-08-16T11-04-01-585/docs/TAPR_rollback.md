# TAPR rollback runbook — undoing the ringof bring-over

**Purpose.** The bring-over restructures **TAPR/TAPRx888**: moves `main`, adds
`dev`, `design`, `ci-docs`, installs CI workflows, turns on branch protection.
This runbook restores TAPR to its **exact pre-migration state**.

> **This doc lives in ringof on purpose.** Rolling TAPR back deletes any copy
> stored on TAPR itself; ringof keeps the whole history (and the ability to retry).

---

## The restore point

Before the bring-over, TAPR is a **single-branch repo**:

```
tapr/main → c01bece8f9f490c37a96d8cb2675cc290c8f881a   ("proper update")
```

- No `dev`, `design`, or `ci-docs` branches.
- No CI workflows, no GitHub Releases, no version tags.
- Two open pull requests (**#4**, **#30**) predate the migration; neither
  bring-over nor rollback touches them.

Captured with `git ls-remote https://github.com/TAPR/TAPRx888` on 2026-07-18.
Re-confirm the SHA before relying on it — if `main` has moved, the current tip is
the real restore point and the anchor below must be re-cut.

---

## Step zero — anchor BEFORE the bring-over (always do this first)

The migration's very first action, *before any branch is moved*, is to make the
current state unloseable. A tagged commit is immutable and never GC'd, so the
pre-migration state is always one reset away.

```sh
# From a local clone that has the TAPR remote (here called "tapr"):
git fetch tapr
TAG="pre-migration-$(date +%Y-%m-%d)"          # e.g. pre-migration-2026-07-18
git tag -a "$TAG" c01bece8 -m "TAPR state before the ringof CI/branch bring-over"
git push tapr "$TAG"

# Recommended: also a human-friendly restore BRANCH at the same commit.
git push tapr c01bece8:refs/heads/pre-migration
```

Record once done:

- Anchor tag: `pre-migration-YYYY-MM-DD` → `c01bece8…`
- Anchor branch: `pre-migration` → `c01bece8…`

---

## The reverse procedure

Run **only** if TAPR abandons the workflow. Every destructive step needs TAPR
admin. Do them in order.

### 1. Lift branch protection

Settings → **Branches / Rulesets** → disable or delete the rules on `dev` and
`main`. A protected branch cannot be force-moved or deleted, so this comes first.

### 2. Reset `main` to the restore point

```sh
git fetch tapr
git push --force tapr pre-migration:main        # from the anchor branch
# or, equivalently, straight from the SHA:
# git push --force tapr c01bece8:main
```

Verify: `git ls-remote tapr refs/heads/main` → `c01bece8…`.

### 3. Delete the branches the bring-over added

```sh
git push tapr --delete dev design ci-docs
```

(If a CLI delete is blocked, do it from the GitHub UI: **Branches → trash icon**.)

### 4. Confirm CI and protection are gone

- Resetting `main` to `c01bece8` removes the workflow files (absent in that
  commit), so **Actions** shows no workflows once `design`/`dev` are also gone.
- Delete any remaining branch-protection rules from the trial.
- Keep the `pre-migration` tag/branch if a retry is possible.

### 5. Purge trial artifacts (Releases + their tags)

The trial cuts board releases (`v0.x` pre-releases, `v1.0` if production was cut)
**and** independent end-plate releases (`endplates-vX.Y`, published on `main` by
`endplate-release.yml`). Remove both for a clean slate:

```sh
gh release list --repo TAPR/TAPRx888
# Board releases (delete the tag too):
gh release delete v0.6 --repo TAPR/TAPRx888 --cleanup-tag --yes
# repeat for v0.7, v0.8, …, and v1.0 if present
# End-plate releases:
gh release delete endplates-v1.0 --repo TAPR/TAPRx888 --cleanup-tag --yes
# repeat for every endplates-v* release/tag
```

(Or **Releases** page → each release → **Delete**, then delete leftover tags
under **Tags** — including any `endplates-v*`.)

---

## Verification — TAPR is back where it started

- `git ls-remote tapr` shows only: `main = c01bece8…`, the open PR refs (#4,
  #30), and — if kept — the `pre-migration` anchor. No `dev` / `design` / `ci-docs`.
- **Actions** tab: no workflows.
- **Releases**: none from the trial (no `v*` and no `endplates-v*`).
- `git fetch tapr && git diff c01bece8 tapr/main` → **empty**.

---

## What rollback does NOT undo

- **Clones/forks made during the trial** keep their copies.
- **ringof is untouched** — a second attempt is possible.
- **Open PRs #4 and #30** are left as they were.

---

## Retrying later

A second attempt is just re-running the bring-over from ringof. **Re-cut a fresh
`pre-migration-<date>` anchor first** (Step zero) — the SHA differs if TAPR's
`main` moved.
