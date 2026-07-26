#!/usr/bin/env python3
"""Assemble the coloured mechanical GLB from KiCad's per-board GLB exports.

KiCad's own GLB export carries the silkscreen / soldermask / pad colours that a
STEP import drops -- but only one board per file. This places those coloured
GLBs (plus the grey enclosure GLB) into one scene, reusing the CadQuery
placement matrices so the result matches the STEP assembly exactly.

Frames -- the subtle part:
  * The placement matrices live in the *enclosure* frame, which is already
    Y-up (Y = height above the floor, Z = length down the case). The glTF
    viewer is also Y-up, so the matrices need NO outer frame conversion.
  * KiCad's STEP export (which the matrices were built against) is Z-up: board
    thickness on Z. But KiCad's GLB export is Y-up: thickness on Y (seen in the
    raw extents -- the ~2 mm thickness lands on the Y axis). So each *KiCad*
    part needs a one-time Rx(90) to move its thickness from Y onto Z, matching
    the STEP frame the matrix expects. The enclosure GLB (from CadQuery) is
    already in the matrix frame and needs no correction.

    m_glb = M @ C @ S      C = Rx(90) for KiCad parts, identity for enclosure.

(An earlier version conjugated by Rx(-90) . M . Rx(90); because every rotation
in M is about X and same-axis rotations commute, that conjugation cancelled to a
no-op and left the board standing on end. The per-part C correction is the fix.)
"""
import argparse
import json
import struct

import numpy as np
import trimesh


def Rx(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0])


# Materials at/above this opacity are treated as solid PCB layers and forced
# opaque; anything more transparent (the ~0.35 enclosure) stays translucent.
OPAQUE_ALPHA = 0.5

# Turn Island blue -- the boards' soldermask is recoloured to this so the PCBs
# read as TIS blue in the viewer (matching the TIS product finish). Linear-ish
# sRGB triple; tune here.
TIS_BLUE = (0.050, 0.130, 0.280)


def _is_soldermask(rgb):
    """Green-dominant and dark = soldermask (~0.08,0.20,0.14); the copper/pads
    are also green-ish but much brighter (r ~0.42), so gate on a low red to keep
    them gold/olive."""
    r, g, b = rgb[0], rgb[1], rgb[2]
    return g > r and g > b and r < 0.25


def fix_materials(path):
    """Make PCB layers opaque, recolour the soldermask TIS blue (in place, GLB
    byte level).

    KiCad exports every PCB layer as alphaMode BLEND with a near-opaque alpha
    (silk ~0.90, mask ~0.83, copper ~0.98). Transparent materials don't write
    depth and get re-sorted back-to-front per camera angle, so as the viewer
    orbits, the silk's draw order flips against the board underneath it and it
    pops in and out. Forcing the near-opaque layers to alphaMode OPAQUE (they
    then write depth and render stably) fixes it; the deliberately translucent
    enclosure (alpha ~0.35) is left BLEND so you can still see inside. Also keep
    doubleSided so thin decals never back-face cull.

    The green soldermask materials are recoloured to Turn Island blue (copper /
    silk left alone) so the boards read as the TIS finish.

    Done directly on the GLB (parse the JSON chunk, patch materials, rewrite the
    chunk lengths) so it does not depend on trimesh's material export path.
    """
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, total = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67, "not a GLB"
    off, chunks = 12, []
    while off < total:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunks.append([ctype, bytearray(data[off + 8:off + 8 + clen])])
        off += 8 + clen
    opaque = blend = blued = 0
    for ctype, cdata in chunks:
        if ctype != 0x4E4F534A:            # JSON chunk only
            continue
        gltf = json.loads(bytes(cdata).decode("utf-8"))
        for m in gltf.get("materials", []):
            m["doubleSided"] = True
            bcf = m.get("pbrMetallicRoughness", {}).get("baseColorFactor")
            alpha = bcf[3] if bcf and len(bcf) > 3 else 1.0
            if alpha >= OPAQUE_ALPHA:
                m["alphaMode"] = "OPAQUE"
                if bcf:
                    bcf[3] = 1.0
                opaque += 1
            else:
                m["alphaMode"] = "BLEND"
                blend += 1
            if bcf and _is_soldermask(bcf):
                bcf[0], bcf[1], bcf[2] = TIS_BLUE
                blued += 1
        newjson = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        newjson += b" " * ((4 - len(newjson) % 4) % 4)   # pad to 4 bytes
        cdata[:] = newjson
    body = b"".join(struct.pack("<II", len(c), t) + bytes(c) for t, c in chunks)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", magic, ver, 12 + len(body)) + body)
    print("[glb] materials -> opaque:%d  translucent(enclosure):%d  soldermask->blue:%d"
          % (opaque, blend, blued))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrices", required=True)
    ap.add_argument("--enclosure", required=True)
    ap.add_argument("--board", required=True)
    ap.add_argument("--front", required=True)
    ap.add_argument("--rear", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    mats = json.load(open(a.matrices))
    parts = {"enclosure": a.enclosure, "main-board": a.board,
             "endplate-front": a.front, "endplate-rear": a.rear}
    # KiCad exports GLB in METRES and Y-up (thickness on Y); the enclosure GLB
    # (CadQuery) is in mm and already in the matrix frame.
    UNIT = {"enclosure": 1.0, "main-board": 1000.0,
            "endplate-front": 1000.0, "endplate-rear": 1000.0}
    # Per-part frame correction: KiCad parts need thickness moved Y->Z to match
    # the STEP frame the placement matrices were built against.
    kicad_fix, eye = Rx(90), np.eye(4)
    CORR = {"enclosure": eye, "main-board": kicad_fix,
            "endplate-front": kicad_fix, "endplate-rear": kicad_fix}

    scene = trimesh.Scene()
    for name, path in parts.items():
        s = UNIT[name]
        m_glb = np.array(mats[name]) @ CORR[name] @ np.diag([s, s, s, 1.0])
        loaded = trimesh.load(path, force="scene")
        raw = loaded.bounding_box.extents
        meshes = loaded.dump()
        for i, mesh in enumerate(meshes):
            mesh.apply_transform(m_glb)
            scene.add_geometry(mesh, node_name="%s_%d" % (name, i))
        print("[glb] %-14s meshes=%2d  raw_extents=%s  placed_at=%s"
              % (name, len(meshes), np.round(raw, 3),
                 np.round(m_glb[:3, 3], 2)))
    print("[glb] combined extents=%s centroid=%s"
          % (np.round(scene.bounding_box.extents, 2),
             np.round(scene.bounding_box.centroid, 2)))
    scene.export(a.out)
    fix_materials(a.out)
    print("wrote", a.out, "-", len(scene.geometry), "geometries")


if __name__ == "__main__":
    main()
