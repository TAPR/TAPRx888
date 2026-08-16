# Mechanical — enclosure & end plates

The TAPRX-888 mechanical package: the enclosure model and the two end-plate
boards. It lives **in this repo** (not a separate one) because the plates are
mechanically coupled to the board — a connector move and its matching cutout move
land as one atomic commit and version together.

```
mechanical/
  enclosure.step    # case model — the EE↔ME interface artifact
  endplate-front/   # standalone KiCad project (front panel)
  endplate-rear/    # standalone KiCad project (rear panel)
```

## Enclosure

`enclosure.step` — the [JLCMC split aluminium box][box] (`K70-8838-H7`, 88 × 38),
**shortened 120 → 100 mm** with the **stock end plates removed** so the PCB plates
take their place. Two-piece (both clamshell halves); verified 88 × 38.02 ×
100 mm, 2 solids. The plate outline and M3 corner pattern (Ø3.4 at ±41, ±14.21
from centre) come from its end profile.

[box]: https://jlcmc.com/product/b/U01/BR9272/aluminum-box-%28jlc%29-88*38*120mm-split

Each plate is its own KiCad project (own `fp-lib-table`/`sym-lib-table`); the root
board is untouched. The plates are **non-functional PCBs** — Edge.Cuts, connector
cutouts, mounting holes, silk (labels + TAPR/HamSCI/TIS logos).

## Releases

Board and plates version separately on `main` (`vX.Y` vs independent
`endplates-vX.Y`); the `dev` `v0.x` pre-release folds board + both plates + the
mechanical assembly into one snapshot. See `docs/RELEASE_STRATEGY.md`. The board's
exported **STEP** is the EE↔ME interface, published standalone as
`TAPRX-888-v<REV>.step`.

## Fit-check CI

The reusable `mechanical-build.yml` (called by `mechanical-ci` on `design`/`dev-*`
and by `dev-release` on `dev`) assembles enclosure + board + both plates
(`assemble_mechanical.py`, CadQuery) into a multi-component STEP, a coloured GLB
(`assemble_glb.py`), and a self-contained viewer (`make_3d_viewer.py`), and
deploys the viewer to **<https://tapr.github.io/TAPRx888/>**. The viewer
(three.js) lets you toggle the four top-level parts -- enclosure, main board,
front / rear end plates -- on and off (turning the translucent enclosure off is
handy for seeing the board inside). `assemble_glb.py` recolours the boards'
soldermask to the Turn Island navy (KiCad's `Blue` stackup preset exports a
brighter cornflower blue), and the viewer's lighting is tuned so every face reads
the same colour. Non-gating; board **connector** 3D models are still missing (#45).

## Plate geometry

**Starter boards, not fab-ready** — open each in KiCad 10 to confirm it parses,
then overlay onto the enclosure end to confirm J1↔J1 / J5↔J5 orientation. Full
parameters live on each board's `Cmts.User` layer; key values:

| Item | Value |
|---|---|
| Outline | 88 × 38 mm, R4.5 |
| M3 mounting holes | Ø3.4 at (±41, ±14.21); plate screws on |
| SMA `J1/J3/J2/J4` (front) | X = −27 / −9 / +9 / +26.8, Y = 7.9; Ø7.0 |
| USB `J5` (rear, X-mirrored) | X = 25.04, Y = 14.79; 12.5 × 12.7 opening |
| JTAG `J11` | internal, no cutout |

Cutout X maps the real connector position via `plate-X = 44 + (board-X − 138)`; Y
from the 7.9 mm PCB rail height above the floor.
