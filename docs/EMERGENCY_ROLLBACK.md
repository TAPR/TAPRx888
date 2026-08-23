# Emergency Rollback — read this first

The parachute. Turns off the CI/branch machinery and returns the repo to a plain
"one branch, push whenever" state. You can do all of this yourself — no waiting.

---

## READ THIS ONE LINE BEFORE YOU PULL THE CORD

**Do not roll back in the middle of a release.**

Between "cut a release" and "the boards / ADCs are actually ordered," the CI
fabrication gate is the only thing checking the package the money rides on.
Rolling back in that window removes that check. If you're in a release cycle and
something's on fire, **stop and call David** instead.

Any other time — normal design work, general frustration — roll back freely.
Nothing below is destructive to the design; schematic, PCB, libraries, and full
Git history are all preserved either way.

---

## The rollback is two steps, in two different places

Part of the "off switch" is a **file** in the repo, part is a **repo setting** on
GitHub. Deleting the file doesn't fully do it — that's expected.

### Step 1 — Stop CI (delete one folder). Anyone can do this.

Delete the `.github/workflows` folder and commit.

- GitHub Desktop: delete the folder locally, commit "Disable CI", push.
- github.com: open `.github/workflows`, delete each file, commit.

The moment that folder is gone, **CI stops running** — no more ERC/DRC/BOM checks,
no generated documents. Design files untouched.

> If a push to `design` or `dev` still kicks off a run afterward, that branch
> still carries its own copy of `.github/workflows`. To remove it from every
> branch at once, see the workflow-deletion steps in `docs/TAPR_manual_mode.md`.

If all you wanted was to make the automation stop, **you're done here.**

### Step 2 — Return to "push straight to main" (remove branch protection). Admin only.

Branch protection is a **repo setting**, not a file, so Step 1 doesn't remove it.
While protection is on you still can't push directly to `main` or `dev`.

1. **Settings → Branches** (in the TAPR/TAPRx888 repo).
2. Under "Branch protection rules," find the **`main`** rule → trash/delete → confirm.
3. Same for the **`dev`** rule.

Direct pushes to `main` work again. You can now treat `main` as the only branch
and ignore `dev` and `design`.

George has admin and can do this. David can help — a ~5-minute call — but you
don't need to wait on anyone.

---

## What this does NOT do (on purpose)

- Does **not** delete any branches, design files, or history. `dev` and `design`
  still exist; you just aren't forced through them.
- Does **not** tell you how to set the structure back up. Rebuilding CI + branch
  protection is the fiddly part — do it deliberately, together with David, not as
  an emergency.

---

## One-paragraph summary

CI machinery = the `.github/workflows` folder; delete it, CI stops. Branch
protection = a setting under Settings → Branches; remove the `main` and `dev`
rules and you're back to pushing straight to `main`. Safe anytime **except
mid-release**, where you call David instead. Nothing here touches the design or
its history.

---

## Related

- **Keep the branches, run checks/releases by hand:** `docs/TAPR_manual_mode.md`.
- **Undo the whole migration:** `docs/TAPR_rollback.md`.
