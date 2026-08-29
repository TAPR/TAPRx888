#!/usr/bin/env python3
"""Drop a netless perimeter stitching-via ring into a KiCad 10 PCB.

For the schematic-less end plates: derives the outer rounded-rect outline from
Edge.Cuts (straight edges + corner arcs), walks it at a fixed pitch inset from
the edge, skips positions too close to any Edge.Cuts hole/cutout circle, and
inserts through-vias on F.Cu+B.Cu, netless (net "") -- a through via is
copper on both layers, physically tying the two pours). Build-time design edit;
run once, eyeball + DRC in KiCad, commit the board.

Usage:
    stitch_perimeter.py PCB [--out PCB] [--dry-run]
Tunables are the constants below.
"""
import argparse, math, re, sys, uuid

INSET_MM      = 2.0    # via-center distance in from the board edge
PITCH_MM      = 2.5    # spacing between vias along the ring
DRILL_MM      = 0.3
PAD_MM        = 0.6
HOLE_KEEPOUT_MM = 1.5  # ring pull-back from thru-holes: min gap, pad edge to
                       # hole edge. Bump to open a bigger gap around the corner
                       # mounting holes; keep >= your DRC copper-edge min (0.5).
LAYERS        = ("F.Cu", "B.Cu")
ARC_TESS_MM   = 0.25   # corner-arc tessellation step


def _blocks(t, name):
    out, i = [], 0
    while True:
        j = t.find('(' + name, i)
        if j < 0:
            return out
        depth, k = 0, j
        while k < len(t):
            if t[k] == '(':
                depth += 1
            elif t[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append(t[j:k + 1]); i = k + 1


def _layer(b):
    m = re.search(r'\(layer "([^"]+)"', b); return m.group(1) if m else None


def _xy(b, key):
    m = re.search(r'\(' + key + r'\s+([-\d.]+)\s+([-\d.]+)', b)
    return (float(m.group(1)), float(m.group(2))) if m else None


def parse(t):
    lines, holes = [], []
    xs, ys = [], []
    for b in _blocks(t, 'gr_line'):
        if _layer(b) == 'Edge.Cuts':
            s, e = _xy(b, 'start'), _xy(b, 'end')
            lines.append((s, e)); xs += [s[0], e[0]]; ys += [s[1], e[1]]
    for b in _blocks(t, 'gr_arc'):
        if _layer(b) == 'Edge.Cuts':
            for key in ('start', 'mid', 'end'):
                p = _xy(b, key); xs.append(p[0]); ys.append(p[1])
    for b in _blocks(t, 'gr_circle'):
        if _layer(b) == 'Edge.Cuts':
            c, e = _xy(b, 'center'), _xy(b, 'end')
            r = math.hypot(e[0] - c[0], e[1] - c[1])
            holes.append((c[0], c[1], r))
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    # corner radius: gap between the outer bbox and where a straight edge starts
    horiz = [l for l in lines if abs(l[0][1] - l[1][1]) < 1e-6
             and abs(l[0][1] - miny) < 1e-6]              # top edge(s)
    if not horiz:
        sys.exit("could not identify top straight edge for corner radius")
    top_x0 = min(min(l[0][0], l[1][0]) for l in horiz)
    R = round(top_x0 - minx, 6)
    return dict(minx=minx, maxx=maxx, miny=miny, maxy=maxy, R=R, holes=holes)


def ring_path(g):
    """Ordered dense polyline of the inset ring (mm), clockwise, closed."""
    minx, maxx, miny, maxy, R = g['minx'], g['maxx'], g['miny'], g['maxy'], g['R']
    ins = INSET_MM
    ar = R - ins                                          # inset corner radius
    L, Rr, T, B = minx + ins, maxx - ins, miny + ins, maxy - ins
    # corner centers (bbox corners pulled in by R)
    cTL, cTR = (minx + R, miny + R), (maxx - R, miny + R)
    cBR, cBL = (maxx - R, maxy - R), (minx + R, maxy - R)
    pts = []

    def arc(cx, cy, a0, a1):
        n = max(2, int(abs(a1 - a0) * ar / ARC_TESS_MM))
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((cx + ar * math.cos(a), cy + ar * math.sin(a)))

    # Start on the TOP-CENTER symmetry axis and walk clockwise. Starting on an
    # axis (+ an even via count in resample) makes the ring mirror-symmetric
    # about both centerlines, since the four quarters are equal length. The
    # closing segment (last TL point -> start) is the left half of the top edge.
    xc = (minx + maxx) / 2.0                         # vertical centerline
    pts.append((xc, T))                             # top-center (start, on axis)
    pts.append((maxx - R, T))                        # top edge -> TR tangent
    arc(*cTR, -math.pi / 2, 0.0)                    # TR: up -> right
    pts.append((Rr, maxy - R))                      # right edge end
    arc(*cBR, 0.0, math.pi / 2)                     # BR: right -> down
    pts.append((minx + R, B))                       # bottom edge end
    arc(*cBL, math.pi / 2, math.pi)                 # BL: down -> left
    pts.append((L, miny + R))                        # left edge end
    arc(*cTL, math.pi, 3 * math.pi / 2)             # TL: left -> up (ends at minx+R,T)
    # dedupe consecutive
    ded = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - ded[-1][0], p[1] - ded[-1][1]) > 1e-6:
            ded.append(p)
    return ded


def resample(path, pitch):
    """Evenly-spaced points along the closed path at ~pitch (mm)."""
    closed = path + [path[0]]
    seglen = [math.hypot(closed[i + 1][0] - closed[i][0],
                         closed[i + 1][1] - closed[i][1]) for i in range(len(closed) - 1)]
    total = sum(seglen)
    # multiple of 4 so the four equal quarters each get the same count -> the
    # ring is symmetric about both centerlines (start point is on the top axis).
    n = max(4, 4 * round(total / pitch / 4))
    step = total / n
    out, d, seg, acc = [], 0.0, 0, 0.0
    for k in range(n):
        target = k * step
        while seg < len(seglen) and acc + seglen[seg] < target:
            acc += seglen[seg]; seg += 1
        if seg >= len(seglen):
            break
        f = (target - acc) / seglen[seg] if seglen[seg] else 0.0
        a, b = closed[seg], closed[seg + 1]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def keep(p, holes):
    for hx, hy, hr in holes:
        if math.hypot(p[0] - hx, p[1] - hy) < hr + HOLE_KEEPOUT_MM + PAD_MM / 2:
            return False
    return True


def strip_matching_vias(t):
    """Remove ring vias this script places (netless, our size/drill/layers), so
    re-running with a new inset/pitch REPLACES the ring instead of stacking it.
    Only vias matching all four signature fields are removed; anything else (a
    netted via, a different size) is left untouched."""
    layers = " ".join('"%s"' % l for l in LAYERS)
    # net-agnostic: strip our ring by size/drill/layers so switching between
    # netless and a named net re-places cleanly.
    sig = ('(size %s)' % PAD_MM, '(drill %s)' % DRILL_MM,
           '(layers %s)' % layers)
    out, i, removed = [], 0, 0
    while True:
        j = t.find('\t(via\n', i)
        if j < 0:
            out.append(t[i:]); break
        depth, k = 0, j
        while k < len(t):
            if t[k] == '(':
                depth += 1
            elif t[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        end = k + 1 + (1 if k + 1 < len(t) and t[k + 1] == '\n' else 0)
        if all(s in t[j:k + 1] for s in sig):
            out.append(t[i:j]); removed += 1          # drop block + its newline
        else:
            out.append(t[i:end])
        i = end
    return "".join(out), removed


def via_sexpr(x, y, net):
    layers = " ".join('"%s"' % l for l in LAYERS)
    return ('\t(via\n\t\t(at %.4f %.4f)\n\t\t(size %s)\n\t\t(drill %s)\n'
            '\t\t(layers %s)\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (x, y, PAD_MM, DRILL_MM, layers, net, uuid.uuid4()))


def set_zone_nets(t, net):
    """Force every FILL zone's net to `net` (first child of the zone block).
    Replaces an existing (net ...) header line or inserts one; leaves keepout
    zones (no `fill yes`) untouched. Needed so the pour and the ring share a
    net and the fill floods solidly onto the vias instead of clearing around
    them."""
    out, i, count = [], 0, 0
    while True:
        j = t.find('\t(zone\n', i)
        if j < 0:
            out.append(t[i:]); break
        depth, k = 0, j
        while k < len(t):
            if t[k] == '(':
                depth += 1
            elif t[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blk = t[j:k + 1]
        out.append(t[i:j])
        if '(fill yes' in blk:
            m = re.match(r'(\t\(zone\n)(\t\t\(net "[^"]*"\)\n)?', blk)
            blk = m.group(1) + '\t\t(net "%s")\n' % net + blk[m.end():]
            count += 1
        out.append(blk); i = k + 1
    return "".join(out), count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pcb')
    ap.add_argument('--out')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--keep', action='store_true',
                    help="do not strip existing matching ring vias first")
    ap.add_argument('--net', default="",
                    help='net name for the vias AND fill zones (default "" = '
                         'netless). Use e.g. GND so the pour bonds to the ring.')
    a = ap.parse_args()
    t = open(a.pcb).read()
    removed = 0
    if not a.keep:
        t, removed = strip_matching_vias(t)
    g = parse(t)
    pts = [p for p in resample(ring_path(g), PITCH_MM) if keep(p, g['holes'])]
    zoned = 0
    if a.net and not a.dry_run:
        t, zoned = set_zone_nets(t, a.net)
    print("outline %.2f x %.2f mm, corner R=%.2f, %d holes"
          % (g['maxx'] - g['minx'], g['maxy'] - g['miny'], g['R'], len(g['holes'])))
    print("removed %d ring via(s); placing %d (inset %.2f, pitch %.2f, net %r); "
          "netted %d fill zone(s)"
          % (removed, len(pts), INSET_MM, PITCH_MM, a.net, zoned))
    if a.dry_run:
        return
    inject = "".join(via_sexpr(x, y, a.net) for x, y in pts)
    cut = t.rstrip()
    assert cut.endswith(')'), "unexpected file tail"
    new = cut[:-1] + inject + ")\n"
    open(a.out or a.pcb, 'w').write(new)
    print("wrote", a.out or a.pcb)


if __name__ == '__main__':
    main()
