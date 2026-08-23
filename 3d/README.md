# 3d — vendored component 3D models (project-local)

3D models for the handful of components that have **no faithful equivalent in
KiCad's bundled 3D libraries** live here directly (`3d/*.step`); the standard
KiCad models the board uses are **vendored alongside** them under
`3d/kicad-stock/` (see below). Between the two, every model the design references
resolves from this checkout — no CI image models and no network required.

## Why these live in the repo — reproducibility

**Every model the board references is vendored in this checkout**, so the STEP
export and 3D renders build **identically in CI, offline, and in production** —
nothing depends on a machine-specific library or a network fetch. (Previously the
footprints pointed at a private `${TIS}` library that existed only on the
designer's machine, so CI couldn't build them — issue #45.)

Two-tier referencing, so a model is *never missing*:

| Tier | Variable | Resolves because | Used for |
|---|---|---|---|
| Stock | `${KICAD10_3DMODEL_DIR}` | vendored at `3d/kicad-stock/`; CI points the var there, a local KiCad install resolves it to its standard library | standard packages (0603, SOT/QFN/SO/BGA, headers, diodes, U.FL …) |
| Local | `${KIPRJMOD}/3d/…` | KiCad always sets `${KIPRJMOD}` to the project dir | the custom models below |

`scripts/check_3d_models.py` gates it: a missing model, or any legacy
`${TIS}`/`${KISYS3DMOD}` reference, fails the build before export — nothing is
silently dropped.

### Stock models — `3d/kicad-stock/`

The 22 standard KiCad models the board places are copied verbatim from the
official **`kicad-packages3D`** library at the **`10.0.4`** tag (matching the
project's KiCad baseline), preserving the `<Package>.3dshapes/<model>.step`
layout so the footprints' existing `${KICAD10_3DMODEL_DIR}/…` paths resolve
unchanged. They are the genuine standard models (CC-BY-SA 4.0, "kicad StepUp"),
cached in-repo purely for reproducibility — **not** a re-drawn or private set.

Why vendor them rather than fetch at build time: the `inti-cmnb/kicad*_auto` CI
image deliberately omits the 3D models (~10× the image size), and KiBot's
on-demand download **404s on KiCad 10** (URL structure changed upstream). Caching
the exact 22 (~2.7 MB) makes the STEP/renders build identically in CI, offline,
and years from now regardless of upstream library changes. To refresh or add one,
copy the file from the same tag into the matching `.3dshapes/` subdir.

## Files expected here

Drop each model in as a **STEP** file (`.step`/`.stp`) with the exact name
below — the footprints already point at these paths, so a drop-in "just works"
and the entry flips from *pending* to *present*. STEP is required because the
board **STEP export only consumes STEP-format models** (it ignores `.wrl`).

| File | Footprint | Refs | Part | LCSC # | License | Status |
|---|---|---|---|---|---|---|
| `SMA_Jack_EdgeMount_JLC.step` | `SMA_Jack_EdgeMount_JLC_With_Nut` | J1–J4 | Edge-mount SMA jack w/ nut | `C2874826` ² | _TBD_ | ⏳ pending |
| `USB-3.0.step` | `USB-3.0` | J5 | XUNPU USB-306BWD-ARW, USB 3.0 **Type-B** receptacle | `C2895032` | GSB3211311WEU ³ | ✅ present |
| `TCXO-3225.step` | `TCXO-3225` | X1 | 27 MHz TCXO, 3.2×2.5 mm | `C5203549` (alt `C46598427`) | _TBD_ | ⏳ pending |
| `LED_RGB_SIDE.step` | `LED_RGB_SIDE` | D3 | Side-view RGB LED | `C389528` | _TBD_ | ⏳ pending |
| `BUTTON-4p5X4p5.step` | `BUTTON-4p5X4p5` | B1 | 4.5×4.5 mm tact switch | `C410371` | _TBD_ | ⏳ pending |
| `SP3011.step` | `SP3011` | U7 | Littelfuse SP3011-06UTG TVS array, UDFN-14 (~3.5×1.35 mm) | `C207281` | _TBD_ | ⏳ pending |

¹ One model body covers all seven (identical 1008 package, differing inductance):
L8 180 nH `C162664`; L9/L12 820 nH `C701161`; L10/L11 120 nH `C2044072`;
L13/L14 150 nH `C2043109`. Grab any one's STEP.
² Correct part for all four is `C2874826`; J2–J4 currently carry the wrong
`C914558` in the BOM (tracked in #63). A single model body fits all four.

**Resolved to KiCad stock (no vendored model needed):**
- **U10** (`SMD-2520`, YXC OT2EL89 19.2 MHz osc, `C49304731`) →
  `Oscillator.3dshapes/Oscillator_SMD_SeikoEpson_SG210-4Pin_2.5x2.0mm.step`
  (same 2.5×2.0 mm 4-pin body). EasyEDA had no 3D model.
- **L8–L14** (`Murata2U`, 1008 wire-wound inductors, `C162664`/`C701161`/
  `C2044072`/`C2043109`) → `Inductor_SMD.3dshapes/L_1008_2520Metric.step`
  (body 2.5×2.0 mm; swapped off the EasyEDA model to drop its molded watermark —
  a plain chip body vs. the wire-wound coil, but dimensionally correct).

³ **J5 is USB 3.0 Type-B**, not Type-A — KiCad ships no full-size Type-B model,
and neither EasyEDA nor the CAD aggregators had the XUNPU part. Since the USB 3.0
Type-B shell is spec-standardized, `USB-3.0.step` uses the **GSB3211311WEU** USB
3.0 Type-B model (dimensionally equivalent shell) reused from the `usb3-fiber`
project.

The LCSC number is the fastest route to a STEP: the part's LCSC/JLCPCB page (or
its EasyEDA model) almost always has one. Fill the **License** cell — and confirm
redistribution — before committing each model.

**Before committing any model here**, fill its *Source / license* cell and
confirm the file is redistributable (manufacturer models usually are; a few
carry restrictive EULAs). Provenance lives in the table above.

## 3D model ↔ footprint alignment policy

Who owns the alignment correction depends on which side we control. The rule:
**where you do *not* control the geometry (a KiCad stock model, or a KiCad stock
footprint), correct in the footprint's model transform and leave the STEP
untouched; where you control *both* (custom footprint + custom model), make them
seat at identity by construction.**

| | **KiCad standard footprint** | **Custom footprint** |
|---|---|---|
| **KiCad standard model** | **(1)** Aligns at identity by design. The transform **must** be `offset 0/0/0`, `rotate 0/0/0`, `scale 1/1/1`; strip any stray transform that crept in. | **(2)** Never modify the stock STEP (it's shared and gets overwritten on library updates). Align in **Footprint Properties → 3D Models** (offset/rotate). |
| **Custom / vendor model** | **(3)** Never modify the stock footprint. Align in **Footprint Properties** (offset/rotate) — or fix the model's origin in the STEP. | **(4)** We own both, so make them align at **`offset 0/0/0`, `rotate 0/0/0`**: author/export the STEP with its origin and orientation matching the footprint (which sits at the standard origin). No transform hacks. |

Notes:
- **`scale` is always `1/1/1`.** A correct STEP is authored in real millimetres.
  Any non-unity or anisotropic scale is a hack forcing a wrong/mis-sized model to
  fit — fix the model or the mapping, don't scale.
- Alignment is a **footprint-level** property: apply a correction to *every*
  instance of a footprint type (keep them uniform) and to the `Library.pretty/`
  source, not to one placed instance.
- **How this project maps on:** the board's stock models sit on **custom** TIS
  footprints → **case 2** (align via footprint transform, STEP untouched — this is
  what the per-footprint calibration pass does). The custom parts in the table
  above are custom model **on** custom footprint → **case 4** (their footprint
  transform is reset to identity; author the vendored STEP to seat there).

## STEP + 3D renders in CI

The board STEP + renders are produced by `scripts/run_checks.sh` (dev-checks,
`kicad-cli … export step`) and `scripts/build_release.sh` (release, KiBot
`export_3d`/`render_3d`); `mechanical-build.yml` consumes the same vendored mirror
for the assembly STEP/GLB. All resolve every model from this checkout.
