# TAPRX-888

A simplified, **HF-only** software-defined radio (SDR) receiver based on the
**RX-888** — a proof-of-concept on a larger 6-layer board with improved thermal
and RF layout.

The KiCad project lives at the repository root (`TAPRX-888.kicad_pro` /
`.kicad_sch` / `.kicad_pcb`). **KiCad 10.0** is the project baseline.

## Features

- HF-only — no VHF up/down converter
- Larger PCB, 6-layer
- No bottom-side components
- 0603 passive components
- Improved thermal layout
- Improved RF input filter(s) (bypassable)
- External reference clock input, auto-switching
- Attenuated filter-bypass injector port (used for timesync)
- SPI boot prom. configurable as USB boot, SPI boot, SPI boot with USB fallback.

Please see the schematic and layout documents for details.

## Core devices

| Function | Part |
|---|---|
| ADC | LTC2208 (16-bit) |
| Clock generator | Si5351 |
| USB3 controller | EZ-USB FX3 (CYUSB301x) |
| SPI boot flash | MX25L3233F |

## Repository & workflow

The KiCad project is at the repo root. Design/PCB, mechanical, and end-plate work
happens on the **`design`** branch (one person at a time — KiCad layout files
can't be merged); docs, CI, and tooling go on **`dev-*`** branches; flow is
`design → dev → main`. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for how we
collaborate and **[docs/RELEASE_STRATEGY.md](docs/RELEASE_STRATEGY.md)** for
branches, CI, and versioning.

## Releases

CI publishes version-stamped fabrication/design packages as GitHub Releases; the
`dev` `v0.x` pre-releases also bundle the end plates, the 3D enclosure assembly,
and a live viewer (**<https://tapr.github.io/TAPRx888/>**). Grab the latest from
the **[Releases page](https://github.com/TAPR/TAPRx888/releases)**; see
**[docs/RELEASE_STRATEGY.md](docs/RELEASE_STRATEGY.md)** for details.

## Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how we collaborate (the two-lane
  `design` / infra flow, the design baton)
- **[docs/RELEASE_STRATEGY.md](docs/RELEASE_STRATEGY.md)** — versioning, CI, and
  how releases are cut
- **[docs/AI_REVIEW.md](docs/AI_REVIEW.md)** — using AI review responsibly; read
  this before pointing an AI tool at the design
- **[docs/EMERGENCY_ROLLBACK.md](docs/EMERGENCY_ROLLBACK.md)** — the parachute:
  how to turn the CI/branch machinery off if it's ever too much

## Reference documents

Device datasheets (LTC2208, Si5351, EZ-USB FX3, MX25L3233F) and RX888 reference
material are on the [project wiki → Reference Documents](https://github.com/TAPR/TAPRx888/wiki/Reference-Documents).
