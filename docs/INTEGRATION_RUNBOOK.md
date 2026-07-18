# Integration Runbook (maintainers)

For merging **infrastructure** changes (CI, design rules, net classes, BOM
scripts, docs) and keeping the `design` branch current afterward.

This is a rare procedure — most work (~90%) is design work on the `design`
branch and never touches this. This runbook is for the occasional `dev-*` change
that lands in `dev`.

**Owner: George (K9TRV).** Infra/procurement/BOM is George's lane; this is the
Git side of that same lane. David is break-glass backup only.

---

## The one rule that makes this safe

Because the design (`.kicad_pcb` / `.kicad_sch`) **cannot be merged**, the only
danger point is when `dev` moves ahead of `design`. If that gap is left open,
the designer's next `Pull` on `design` brings down a surprise, and it *looks*
like their work got clobbered even though it didn't.

So: **the sync-down is step 5 of this procedure, every time.** You never do steps
1–4 and walk away. Merging an infra change and re-syncing `design` are one job,
not two.

---

## The procedure (GitHub Desktop)

Do this **only when the design baton is free** (nobody is mid-edit on the
design). Announce in Signal that you're integrating.

1. **Merge the infra PR into `dev`.**
   The `dev-*` pull request → review → squash-merge into `dev`. CI runs. Confirm
   it's green.

2. **Switch to `design`.**
   Current Branch → `design`.

3. **Pull `design`.**
   Make sure you have the latest `design` before touching it.

4. **Merge `dev` into `design`.**
   Branch → "Merge into current branch…" → choose `dev`. This brings the infra
   change down onto `design` so the two no longer diverge. (Infra changes are
   mergeable — this is safe. You are *not* merging design files here.)

5. **Push `design`, then say "design synced" in Signal.**
   Push. Then post **"design synced"** so the designer knows their next Pull is
   clean and current.

That's the whole job. Steps 2–5 are what keep the designer safe; don't skip them.

---

## Guardrails / gotchas

- **Only ever do this with the baton free.** If the designer is mid-edit, wait —
  or hand the change to them to apply. Never run this while the board is being
  edited.
- **You are only ever merging the mergeable lane** (CI, DRU, net classes, BOM,
  docs) into `dev`, and syncing that down. The layout itself never passes through
  a merge — it moves by baton, one editor at a time. So the worst a fumble here
  can do is mangle recoverable infra state on `dev`/`design`, never the designer's
  live layout.
- **`.kicad_pro` is the one shared file** both lanes touch (KiCad rewrites it
  during design work; it's also where net-class/DRC settings live). To avoid a
  three-way tangle on it, board-settings / DRC-rule changes go through the design
  baton too — announce them, or hand them to the designer to apply — rather than
  landing on `dev` while the design is being edited.
- **Releases (`dev` → `main`) are separate** and by consensus between David and
  George — that's not this runbook. See `docs/RELEASE_STRATEGY.md`.

---

## If you get stuck

Ping David. But the point of this runbook is that you don't have to — it's the
same five steps every time. Break-glass, not default.
