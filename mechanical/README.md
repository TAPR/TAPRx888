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
board is untouched. The plates are **non-signal PCBs** — Edge.Cuts, connector
cutouts, mounting holes, silk (labels + TAPR/HamSCI/TIS logos), plus a
script-generated **GND shield pour + stitching-via ring** (see *Shield pour & GND
stitching* below).

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

## Shield pour & GND stitching

Each plate carries a **dual-layer copper pour** (F.Cu + B.Cu, the `shield` zone)
tied together by a **perimeter ring of 0.3 / 0.6 mm through-vias** — a grounded
EMI shield that also bonds the plate to the enclosure through the mounting screws.

The plates have **no schematic** (they're generated, PCB-only), so there is no net
list to draw a net from. Instead the pour and the via ring are put on a **`GND`
net written straight into the board** by `scripts/stitch_perimeter.py` (name-based
net, KiCad 10 `20260206` format). That shared net is what lets the pour flood
**solidly onto the ring** instead of clearing around it; KiCad keeps the injected
net across load and DRC is clean, so no stub schematic is needed.

**The via ring is generated — do not hand-edit it.** To change it, retune the
constants at the top of `scripts/stitch_perimeter.py` (`INSET_MM`, `PITCH_MM`,
`HOLE_KEEPOUT_MM`, drill/pad) and re-run against the plate:

```sh
python3 scripts/stitch_perimeter.py mechanical/endplate-rear/endplate-rear.kicad_pcb --net GND
```

then open the board in KiCad, **refill zones (`B`)**, and DRC. The script is
idempotent (it strips its own previous ring before placing), derives the outline
and hole keepouts from the board's own Edge.Cuts, lays the ring **symmetric about
both plate centrelines**, inset from the edge and stood off the mounting holes.
Run it per plate (front takes the same command on its own `.kicad_pcb`).
