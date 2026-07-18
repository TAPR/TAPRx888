# TAPR rollback runbook — undoing the ringof bring-over

**Purpose.** The TAPRX-888 CI + branch-model migration ("the bring-over")
restructures the **TAPR/TAPRx888** repo: it moves `main`, adds `dev`, `design`,
and `ci-docs` branches, installs the CI workflows, and turns on branch
protection. If the TAPR maintainers decide the full Git workflow is more than
they want and choose to go back to where they were, this runbook restores TAPR
to its **exact pre-migration state**.

> **This doc lives in ringof on purpose.** Rolling TAPR back would delete any
> copy stored on TAPR itself. ringof keeps the whole history through its fallow
> period, so the escape hatch (and the ability to retry later) always survives
> here.

---

## The restore point

Before the bring-over, TAPR is a **single-branch repo**:

```
tapr/main → c01bece8f9f490c37a96d8cb2675cc290c8f881a   ("proper update")
```

- No `dev`, `design`, or `ci-docs` branches.
- No CI workflows, no GitHub Releases, no version tags.
- Two open pull requests (**#4**, **#30**) predate the migration. Neither the
  bring-over nor this rollback touches them.

Captured with `git ls-remote https://github.com/TAPR/TAPRx888` on 2026-07-18.
Re-confirm the SHA before relying on it — if TAPR's `main` has moved since, the
current tip is the real restore point and the anchor below must be re-cut.

---

## Step zero — anchor BEFORE the bring-over (always do this first)

The migration's very first action, *before any branch on TAPR is moved*, is to
make the current state unloseable. A tagged commit is immutable and is never
garbage-collected, so from here on the pre-migration state is always one reset
away — even after `main` is force-moved.

```sh
# From a local clone that has the TAPR remote (here called "tapr"):
git fetch tapr
TAG="pre-migration-$(date +%Y-%m-%d)"          # e.g. pre-migration-2026-07-18
git tag -a "$TAG" c01bece8 -m "TAPR state before the ringof CI/branch bring-over"
git push tapr "$TAG"

# Recommended: also a human-friendly restore BRANCH at the same commit, so the
# restore point is visible in the branch list, not only under tags.
git push tapr c01bece8:refs/heads/pre-migration
```

Record the pushed tag name and SHA here once done:

- Anchor tag: `pre-migration-YYYY-MM-DD` → `c01bece8…`
- Anchor branch: `pre-migration` → `c01bece8…`

---

## The reverse procedure

Run **only** if TAPR decides to abandon the workflow. Every destructive step
needs TAPR admin (you hold it). Do them in order.

### 1. Lift branch protection

Settings → **Branches / Rulesets** → disable or delete the rules on `dev` and
`main`. A protected branch cannot be force-moved or deleted, so this must come
first.

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

(If a CLI delete is blocked by tooling/permissions, do it from the GitHub UI:
**Branches → trash icon** on each.)

### 4. Confirm CI and protection are gone

- Resetting `main` to `c01bece8` already removes the workflow files (they don't
  exist in that commit), so the **Actions** tab shows no workflows once the
  `design`/`dev` branches are also gone.
- Delete any remaining branch-protection rules created for the trial.
- Keep the `pre-migration` tag/branch if a retry is possible; delete them only
  once you're certain you're done.

### 5. Purge trial artifacts (Releases + their tags)

The CI cuts GitHub Releases during the trial (`v0.x` pre-releases, and `v1.0` if
a production release was cut). Remove them for a clean slate:

```sh
gh release list --repo TAPR/TAPRx888
# For each trial release (delete the tag too):
gh release delete v0.6 --repo TAPR/TAPRx888 --cleanup-tag --yes
# repeat for v0.7, v0.8, …, and v1.0 if present
```

(Or **Releases** page → each release → **Delete**, then delete the leftover tag
under **Tags**.)

---

## Verification — TAPR is back where it started

- `git ls-remote tapr` shows only: `main = c01bece8…`, the open PR refs (#4,
  #30), and — if you kept it — the `pre-migration` anchor. No `dev` / `design` /
  `ci-docs`.
- **Actions** tab: no workflows.
- **Releases**: none from the trial.
- `git fetch tapr && git diff c01bece8 tapr/main` → **empty** (byte-for-byte the
  pre-migration tree).

---

## What rollback does NOT undo

- **Clones/forks made during the trial** keep their copies — outside TAPR's
  control.
- **ringof is untouched.** It retains every piece of the bring-over, so nothing
  is lost and a second attempt is possible.
- **Open PRs #4 and #30** are left exactly as they were.

---

## Retrying later

Because ringof keeps everything, a second attempt is just re-running the
bring-over from ringof. **Re-cut a fresh `pre-migration-<date>` anchor first**
(Step zero) — the SHA will differ if TAPR's `main` moved in the meantime.
