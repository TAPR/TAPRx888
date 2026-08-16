#!/usr/bin/env python3
"""Assemble the TAPRX-888 mechanical fit-check STEP + emit placement matrices.

Places the four parts -- enclosure, main board, and the two end plates -- in one
shared coordinate frame using CadQuery (plus, optionally, the 8 M3 corner
screws), and:
  * writes the multi-component STEP (for any CAD viewer), and
  * writes each part's 4x4 placement matrix to JSON, plus the enclosure alone as
    a GLB, so scripts/assemble_glb.py can build the *coloured* GLB from KiCad's
    own per-board GLB exports (which carry the silkscreen/soldermask/pad colours
    that a STEP import drops).

This file is the mechanical *definition* of how the parts align. See the caveats
in the git history / mechanical/README.md.

Frames: the enclosure STEP is the master frame -- X = width (centred), Y = height
(floor = min-Y), Z = length (0..~100). Each KiCad board is exported in its own
frame (in-plane X/Y, stack along Z) and rotated/translated into the enclosure
frame here.
"""
import argparse
import json

import numpy as np
import cadquery as cq
from cadquery import importers, Assembly, Color

# ---- mechanical definition (mm, enclosure frame) ----------------------------
RAIL = 7.9              # board mid-plane height above the enclosure floor
BOARD_LEN_TO_Z_DEG = 90  # rotate board length (KiCad-Y) onto enclosure Z
BOARD_END_OVER_END = True   # 180 about the width axis -- flip the board over
FRONT_FLIP_FLOOR = True     # 180 about X so the front cutouts sit at the floor
REAR_FLIP_FLOOR = True
REAR_FACE_FLIP_DEG = 180    # rear panel faces the opposite way (mirror)

COL = {
    "enclosure":      Color(0.62, 0.64, 0.66, 0.35),  # translucent aluminium
    "main-board":     Color(0.10, 0.45, 0.20, 1.00),
    "endplate-front": Color(0.15, 0.35, 0.70, 1.00),
    "endplate-rear":  Color(0.15, 0.35, 0.70, 1.00),
    "screw":          Color(0.12, 0.12, 0.13, 1.00),  # black-oxide steel
    "sma-hardware":   Color(0.78, 0.62, 0.19, 1.00),  # gold, a touch darker than the SMA body
}

# Enclosure corner mounting holes, in the enclosure (master) frame [mm]. The M3
# pattern was taken from the box end profile: Ø3.4 clearance in the plates over a
# Ø2.4 self-tap channel in the box, at (+/-41, +/-14.21), at BOTH ends. An M3
# thread-forming screw ("for soft metal") passes through the plate and taps the
# channel. Source: mechanical/README.md + enclosure.step (verified). 8 holes =
# 4 corners x 2 ends.
HOLE_XY = [(sx * 41.0, sy * 14.21) for sx in (1, -1) for sy in (1, -1)]


def load(path):
    return importers.importStep(path).val()


def _rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _mat(R, t):
    m = np.eye(4)
    m[:3, :3] = R
    m[:3, 3] = t
    return m


def place_screws(path, eb, t_front, t_rear):
    """Place 8 M3 thread-forming screws in the enclosure corner holes.

    Returns (shapes, mats): a list of (shape, name) and a name->4x4 dict. The
    screw axis is the enclosure length (Z); each screw's head seats on the outer
    face of its end plate and the threads point inward into the box channel.
    """
    import math

    def rad(v):
        return math.hypot(v[0], v[1])

    def verts(shape):
        return [v.toTuple() for v in shape.Vertices()]

    s0 = load(path)                                  # screw long axis is Z
    sb = s0.BoundingBox()
    vv = verts(s0)
    zc = (sb.zmin + sb.zmax) / 2.0
    r_hi = max((rad(v) for v in vv if v[2] >= zc), default=0.0)
    r_lo = max((rad(v) for v in vv if v[2] < zc), default=0.0)
    if r_hi < r_lo:                                  # head sits at -Z -> flip up
        s0 = s0.rotate((0, 0, 0), (1, 0, 0), 180)
        sb = s0.BoundingBox()
    base = s0.translate((0, 0, -sb.zmin))            # tip at origin, head toward +Z

    # Head-bearing height above the tip = lowest vertex of the (wider) head.
    vb = verts(base)
    ztop = base.BoundingBox().zmax
    thread_r = max((rad(v) for v in vb if v[2] < 0.6 * ztop), default=1.75)
    head_z = [v[2] for v in vb if rad(v) >= 1.4 * thread_r]
    Hb = min(head_z) if head_z else 0.7 * ztop       # tip -> head-bearing distance

    shapes, mats = [], {}
    # +Z end: head already points +Z (outward), no flip. -Z end: flip 180 about X.
    ends = (("front", eb.zmax + t_front, False),
            ("rear",  eb.zmin - t_rear,  True))
    for end, p_out, flip in ends:
        for i, (hx, hy) in enumerate(HOLE_XY, start=1):
            shp, R = base, np.eye(3)
            if flip:
                shp = shp.rotate((0, 0, 0), (1, 0, 0), 180)
                R = _rot("x", 180)
                tz = p_out + Hb                       # head-bearing (-Hb) -> p_out
            else:
                tz = p_out - Hb                       # head-bearing (+Hb) -> p_out
            shp = shp.translate((hx, hy, tz))
            name = "screw-%s-%d" % (end, i)
            shapes.append((shp, name))
            mats[name] = _mat(R, np.array([float(hx), float(hy), tz]))
    return shapes, mats


def _normalize_hw(path):
    """Load a flat piece of hardware (washer / nut) and normalise it: axis on Z,
    bore centred on the origin, base at z=0. Returns (shape, thickness). The
    thinnest bounding-box dimension is taken as the axis (true for a washer disk
    and a hex nut), and the part is symmetric about it, so the spin about Z is a
    don't-care."""
    s = load(path)
    bb = s.BoundingBox()
    ext = [bb.xlen, bb.ylen, bb.zlen]
    axis = ext.index(min(ext))
    if axis == 0:
        s = s.rotate((0, 0, 0), (0, 1, 0), 90)   # X -> Z
    elif axis == 1:
        s = s.rotate((0, 0, 0), (1, 0, 0), 90)   # Y -> Z
    bb = s.BoundingBox()
    s = s.translate((-bb.center.x, -bb.center.y, -bb.zmin))  # bore@origin, base@z=0
    return s, s.BoundingBox().zlen


def _sma_hole_centers(plate, rlo=3.4, rhi=3.6, row_tol=1.0):
    """(x, y) centres of the Ø7 SMA holes in the *placed* front plate, read
    straight from its geometry (so they're already in the enclosure frame). A
    radius gate isolates the Ø7 bores (M3 corners are Ø3.4, plate corners R4.5);
    top+bottom edges of each bore dedupe by rounded centre.

    The three real SMAs sit in a single horizontal row (one plate-Y). The STEP
    export can also throw a stray ~Ø7 circle elsewhere on the plate, so when more
    than three survive the gate we keep only the largest same-Y cluster (the row)
    and drop the outlier."""
    seen = {}
    for e in plate.Edges():
        try:
            if e.geomType() != "CIRCLE":
                continue
            r = e.radius()
        except Exception:
            continue
        if rlo <= r <= rhi:
            c = e.Center()
            seen[(round(c.x, 1), round(c.y, 1))] = (c.x, c.y)
    centers = sorted(seen.values())
    print("SMA Ø7 circles:", [(round(x, 1), round(y, 1)) for x, y in centers])
    if len(centers) > 3:
        best = []
        for x0, y0 in centers:
            row = [c for c in centers if abs(c[1] - y0) <= row_tol]
            if len(row) > len(best):
                best = row
        centers = best
        print("  -> kept SMA row:", [(round(x, 1), round(y, 1)) for x, y in centers])
    return centers


def place_sma_hardware(washer_path, nut_path, front):
    """Stack a washer then a nut on each SMA hole, flush to the front plate's
    outer (external) face: plate face -> washer -> nut, all coaxial on Z.
    Returns (shapes, mats)."""
    centers = _sma_hole_centers(front)
    z_face = front.BoundingBox().zmax                 # outer/external face of the front plate
    washer0, t_w = _normalize_hw(washer_path)
    nut0, t_n = _normalize_hw(nut_path)
    shapes, mats = [], {}
    for i, (x, y) in enumerate(centers, start=1):
        w = washer0.translate((x, y, z_face))         # flush against the plate face
        n = nut0.translate((x, y, z_face + t_w))       # flush against the washer
        shapes += [(w, "washer-%d" % i), (n, "nut-%d" % i)]
        mats["washer-%d" % i] = _mat(np.eye(3), np.array([x, y, z_face]))
        mats["nut-%d" % i] = _mat(np.eye(3), np.array([x, y, z_face + t_w]))
    return shapes, mats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("enclosure", "board", "front", "rear"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--board-bare", required=True,
                    help="component-free board datum STEP (kicad-cli --board-only): "
                         "its bbox is the substrate mid-plane + Edge.Cuts outline, "
                         "so the board seat never moves when parts change")
    ap.add_argument("--out", required=True, help="multi-component STEP")
    ap.add_argument("--matrices", required=True, help="placement matrices JSON")
    ap.add_argument("--enclosure-glb", required=True, help="enclosure-only GLB")
    ap.add_argument("--screw", default=None,
                    help="M3 thread-forming screw STEP; if given, 8 are placed "
                         "in the enclosure corner holes (and baked into the "
                         "enclosure GLB so they appear in the viewer too)")
    ap.add_argument("--washer", default=None, help="SMA washer STEP")
    ap.add_argument("--nut", default=None,
                    help="SMA nut STEP; with --washer, a washer+nut is stacked on "
                         "each SMA hole, flush to the front plate's outer face")
    a = ap.parse_args()

    enc = load(a.enclosure)
    eb = enc.BoundingBox()
    floor, ymid = eb.ymin, (eb.ymin + eb.ymax) / 2.0
    mats = {"enclosure": np.eye(4)}   # enclosure is the master (identity)

    # --- main board: length->Z, thickness->Y, end-over-end, then seat in case --
    # Seat off the component-free datum (--board-only), NOT the populated board:
    # a bounding box that includes the 3D component models drifts every time a
    # part changes height. The datum's bbox is the bare PCB, so its center is the
    # substrate mid-plane (vertical) and the Edge.Cuts outline center (lateral).
    # The datum shares the board's origin, so the transform we derive from it
    # applies verbatim to the populated board.
    def orient_board(shape):
        shape = shape.rotate((0, 0, 0), (1, 0, 0), BOARD_LEN_TO_Z_DEG)
        if BOARD_END_OVER_END:
            shape = shape.rotate((0, 0, 0), (1, 0, 0), 180)
        return shape

    R_board = _rot("x", BOARD_LEN_TO_Z_DEG)
    if BOARD_END_OVER_END:
        R_board = _rot("x", 180) @ R_board
    bb = orient_board(load(a.board_bare)).BoundingBox()   # bare PCB datum
    t_board = np.array([-bb.center.x,
                        (floor + RAIL) - bb.center.y,
                        (eb.zmin + (eb.zlen - bb.zlen) / 2.0) - bb.zmin])
    board = orient_board(load(a.board)).translate(tuple(t_board))  # populated
    mats["main-board"] = _mat(R_board, t_board)

    # --- end plates: fill the opening, seat just outside an end -----------------
    def place_plate(shape, at_z_max, face_flip_deg, floor_flip):
        R = np.eye(3)
        if face_flip_deg:
            shape = shape.rotate((0, 0, 0), (0, 1, 0), face_flip_deg)
            R = _rot("y", face_flip_deg) @ R
        if floor_flip:
            shape = shape.rotate((0, 0, 0), (1, 0, 0), 180)
            R = _rot("x", 180) @ R
        pb = shape.BoundingBox()
        dz = (eb.zmax - pb.zmin) if at_z_max else (eb.zmin - pb.zmax)
        t = np.array([-pb.center.x, ymid - pb.center.y, dz])
        return shape.translate((t[0], t[1], t[2])), _mat(R, t)

    front, mats["endplate-front"] = place_plate(
        load(a.front), at_z_max=True, face_flip_deg=0, floor_flip=FRONT_FLIP_FLOOR)
    rear, mats["endplate-rear"] = place_plate(
        load(a.rear), at_z_max=False, face_flip_deg=REAR_FACE_FLIP_DEG, floor_flip=REAR_FLIP_FLOOR)

    # --- corner screws: seat head on each plate's outer face, thread into box ----
    screws = []
    if a.screw:
        screws, screw_mats = place_screws(
            a.screw, eb, t_front=front.BoundingBox().zlen, t_rear=rear.BoundingBox().zlen)
        mats.update(screw_mats)
        print("placed %d screws" % len(screws))

    # --- SMA panel hardware: washer + nut on each SMA hole, outer face of front --
    sma_hw = []
    if a.washer and a.nut:
        sma_hw, hw_mats = place_sma_hardware(a.washer, a.nut, front)
        mats.update(hw_mats)
        print("placed %d SMA hardware pieces (%d washer+nut sets)"
              % (len(sma_hw), len(sma_hw) // 2))

    # --- STEP (for CAD) ---------------------------------------------------------
    assy = Assembly(name="TAPRX-888-mechanical")
    for shape, name in ((enc, "enclosure"), (board, "main-board"),
                        (front, "endplate-front"), (rear, "endplate-rear")):
        assy.add(shape, name=name, color=COL[name])
    for shape, name in screws:
        assy.add(shape, name=name, color=COL["screw"])
    for shape, name in sma_hw:
        assy.add(shape, name=name, color=COL["sma-hardware"])
    assy.save(a.out)
    print("wrote", a.out)

    # --- placement matrices + enclosure GLB (for the coloured GLB assembly) -----
    with open(a.matrices, "w") as f:
        json.dump({k: v.tolist() for k, v in mats.items()}, f, indent=1)
    print("wrote", a.matrices)
    # Bake the placed screws into the enclosure GLB: they live in the enclosure
    # (identity) frame, so assemble_glb.py -- which applies mats["enclosure"] to
    # this file -- carries them into the coloured viewer already seated.
    enc_root = Assembly(name="enc-root").add(enc, name="enclosure", color=COL["enclosure"])
    for shape, name in screws:
        enc_root.add(shape, name=name, color=COL["screw"])
    for shape, name in sma_hw:
        enc_root.add(shape, name=name, color=COL["sma-hardware"])
    enc_root.save(a.enclosure_glb, exportType="GLTF")
    print("wrote", a.enclosure_glb)


if __name__ == "__main__":
    main()
