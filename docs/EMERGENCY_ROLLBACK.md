# Emergency Rollback — read this first

This is the parachute. It turns off the CI/branch machinery and returns the repo
to a plain "one branch, push whenever" state — the way we worked before.

You can do all of this yourself. You do **not** need to wait for anyone.

---

## READ THIS ONE LINE BEFORE YOU PULL THE CORD

**Do not roll back in the middle of a release.**

If we are between "cut a release" and "the boards / ADCs are actually ordered,"
the CI fabrication gate is the only thing checking the package the money rides
on. Rolling back in that window removes that check. If you're in a release
cycle and something's on fire, **stop and call David** instead of rolling back —
that's the one situation where the 5-minute call is worth it.

Any other time — normal design work, general frustration, "this is more fuss
than it's worth today" — roll back freely. Nothing below is destructive to the
actual design; the schematic, PCB, libraries, and full Git history are all
preserved either way.

---

## The rollback is two steps, in two different places

The "off switch" is not all in one spot. Part of it is a **file** in the repo,
and part of it is a **repo setting** on GitHub. That's normal — don't be
surprised when deleting the file doesn't fully do it.

### Step 1 — Stop CI (delete one folder). Anyone can do this.

Delete the `.github/workflows` folder and commit.

- In GitHub Desktop: delete the folder locally, commit "Disable CI", push.
- Or on github.com: open `.github/workflows`, delete each file, commit.

The moment that folder is gone, **CI stops running.** No more automatic
ERC/DRC/BOM checks, no more generated documents. Nothing else changes. Your
design files are untouched.

> If a push to `design` or `dev` still kicks off a run afterward, it's because
> that branch still carries its own copy of `.github/workflows`. To remove it
> cleanly from every branch at once, see the workflow-deletion steps in
> `docs/TAPR_manual_mode.md`.

If all you wanted was to make the automation stop, **you're done here.** You can
keep the branches and just ignore them.

### Step 2 — Return to "push straight to main" (remove branch protection). Admin only.

Branch protection is a **repo setting**, not a file — so deleting the workflows
folder above does *not* remove it. As long as protection is on, you still can't
push directly to `main` or `dev`. To go all the way back to "one branch, push
whenever":

1. Go to **Settings → Branches** (github.com, in the TAPR/TAPRx888 repo).
2. Under "Branch protection rules," find the rule for **`main`** → click the
   trash/delete icon → confirm.
3. Do the same for the **`dev`** rule.

That's it. Direct pushes to `main` work again. You can now work however you
like — including treating `main` as the only branch and ignoring `dev` and
`design`.

George has admin and can do this. If you'd rather have a hand, ping David and
it's a ~5-minute call — but you don't need to wait on anyone.

---

## What this does NOT do (on purpose)

- It does **not** delete any branches, design files, or history. `dev` and
  `design` still exist; you just aren't forced through them anymore.
- It does **not** tell you how to set the structure back up. Teardown is easy and
  safe to do alone. **Rebuilding** the CI + branch protection is the fiddly part,
  and it's worth doing deliberately, with a clear head, together — so if you
  decide later you want the structure back, that's a "let's do this properly"
  call with David, not an emergency.

---

## One-paragraph summary

CI machinery = the `.github/workflows` folder. Delete it, CI stops. Branch
protection = a setting under Settings → Branches. Remove the `main` and `dev`
rules, and you're back to pushing straight to `main` like before. Safe to do
anytime **except mid-release**, where you call David instead. Nothing here
touches the actual design or its history.

---

## Related

- **Keep the branches, just run the checks/releases by hand** (a middle ground,
  not a full teardown): `docs/TAPR_manual_mode.md`.
- **Undo the whole migration** and return the repo to exactly the state it was in
  before CI/branches were introduced: `docs/TAPR_rollback.md`.
