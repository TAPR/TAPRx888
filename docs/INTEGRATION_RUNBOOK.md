# Integration Runbook (maintainers)

For merging **infrastructure** changes (CI, design rules, net classes, BOM
scripts, docs) and keeping `design` current afterward. Rare — ~90% of work is
design work on `design` and never touches this. This is for the occasional
`dev-*` change that lands in `dev`.

**Owner: George (K9TRV).** David is break-glass backup only.

---

## The one rule that makes this safe

The design (`.kicad_pcb` / `.kicad_sch`) **cannot be merged**, so the only danger
is when `dev` moves ahead of `design`. Leave that gap open and the designer's next
`Pull` on `design` brings down a surprise that *looks* like clobbered work.

So: **the sync-down is step 5, every time.** Never do steps 1–4 and walk away —
merging an infra change and re-syncing `design` are one job.

---

## The procedure (GitHub Desktop)

Do this **only when the design baton is free** (nobody mid-edit). Announce in
Signal that you're integrating.

1. **Merge the infra PR into `dev`.** `dev-*` PR → review → squash-merge into
   `dev`. CI runs. Confirm green.
2. **Switch to `design`.** Current Branch → `design`.
3. **Pull `design`.** Get the latest before touching it.
4. **Merge `dev` into `design`.** Branch → "Merge into current branch…" → `dev`.
   Brings the infra change down so the two no longer diverge. (Infra is
   mergeable; you are *not* merging design files.)
5. **Push `design`, then say "design synced" in Signal** so the designer knows
   their next Pull is clean.

Steps 2–5 are what keep the designer safe; don't skip them.

---

## Guardrails / gotchas

- **Only ever do this with the baton free.** If the designer is mid-edit, wait —
  or hand them the change to apply.
- **You only ever merge the mergeable lane** (CI, DRU, net classes, BOM, docs)
  into `dev` and sync it down. The layout moves by baton, one editor at a time —
  so the worst a fumble does is mangle recoverable infra state, never the live
  layout.
- **`.kicad_pro` is the one shared file** both lanes touch (KiCad rewrites it; it
  also holds net-class/DRC settings). Board-settings / DRC-rule changes go through
  the design baton too — announce them or hand them to the designer — rather than
  landing on `dev` mid-edit.
- **Releases (`dev` → `main`) are separate** and by David+George consensus — not
  this runbook. See `docs/RELEASE_STRATEGY.md`.

---

## If you get stuck

Ping David. But it's the same five steps every time — break-glass, not default.
