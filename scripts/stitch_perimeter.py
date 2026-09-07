#!/usr/bin/env python3
"""Drop a netless perimeter stitching-via ring into a KiCad 10 PCB.

For the schematic-less end plates: derives the outer rounded-rect outline from
Edge.Cuts (straight edges + corner arcs), walks it at a fixed pitch inset from
the edge, skips positions too close to any Edge.Cuts hole/cutout circle, and
inserts through-vias on F.Cu+B.Cu, netless (net "") -- a through via is
copper on both layers, physically tying the two pours). Build-time design edit;
run once, eyeball + DRC in KiCad, commit the board.

With --cutout-stitch it also rings the perimeter of large *interior* cutouts
(perimeter >= CUTOUT_MIN_PERIMETER_MM): circular cutouts (SMA holes) get a
concentric ring just outside the hole, polygonal cutouts (the USB slot) get an
outward-offset ring. Small cutouts (M3 mounting, status LED) fall below the
threshold and are skipped.

Usage:
    stitch_perimeter.py PCB [--net GND] [--sma-keepout] [--screw-mask]
                            [--cutout-stitch] [--out PCB] [--dry-run]
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


def keep(p, holes, skip=None):
    for h in holes:
        if skip is not None and h == skip:
            continue                                  # allow proximity to own cutout
        hx, hy, hr = h
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


SMA_KEEPOUT_DIA_MM = 10.5  # copper-pour keepout diameter around big (SMA) holes.
                           # >= SMA washer Ø (~9.5) + margin, so the washer seats
                           # on bare laminate, never on the pour.
SMA_HOLE_MIN_R     = 3.0   # only holes with radius >= this get a keepout (Ø7 SMA
                           # qualifies, Ø3.4 M3 mounting holes do not)
_SMA_TAG = '(name "sma-keepout")'


def strip_sma_keepouts(t):
    """Remove keepout zones this script generated (tagged 'sma-keepout'), so a
    re-run replaces them instead of stacking."""
    out, i, removed = [], 0, 0
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
        end = k + 1 + (1 if k + 1 < len(t) and t[k + 1] == '\n' else 0)
        if _SMA_TAG in t[j:k + 1]:
            out.append(t[i:j]); removed += 1
        else:
            out.append(t[i:end])
        i = end
    return "".join(out), removed


def sma_keepout_zone(cx, cy, dia):
    """A circular copper-pour keepout (Rule Area) on F.Cu+B.Cu around a hole."""
    r = dia / 2.0
    n = max(24, int(2 * math.pi * r / 0.4))          # smooth circle polygon
    pts = [(cx + r * math.cos(2 * math.pi * i / n),
            cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    xy = "\n".join("\t\t\t\t" + " ".join("(xy %.4f %.4f)" % p for p in pts[a:a + 4])
                   for a in range(0, len(pts), 4))
    layers = " ".join('"%s"' % l for l in LAYERS)
    return (
        '\t(zone\n'
        '\t\t(layers %s)\n'
        '\t\t(uuid "%s")\n'
        '\t\t%s\n'
        '\t\t(hatch edge 0.5)\n'
        '\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n'
        '\t\t(min_thickness 0.25)\n'
        '\t\t(keepout\n'
        '\t\t\t(tracks allowed)\n\t\t\t(vias allowed)\n\t\t\t(pads allowed)\n'
        '\t\t\t(copperpour not_allowed)\n\t\t\t(footprints allowed)\n\t\t)\n'
        '\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)\n'
        '\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n'
        '\t\t\t(island_removal_mode 0)\n\t\t)\n'
        '\t\t(polygon\n\t\t\t(pts\n%s\n\t\t\t)\n\t\t)\n'
        '\t)\n' % (layers, uuid.uuid4(), _SMA_TAG, xy))


SCREW_MASK_DIA_MM = 7.0    # exposed-copper mask aperture Ø at M3 mounting holes,
                           # so the screw/washer bites bare GND copper and bonds
                           # the shield to the (grounded) enclosure. 0 = off.
MOUNT_HOLE_MIN_R  = 1.5    # mounting-hole radius band is [MIN, SMA_HOLE_MIN_R):
                           # catches M3 Ø3.4 (r1.7), skips STATUS Ø2.0 and SMA Ø7.


def mask_aperture(cx, cy, dia, layer):
    """A filled circle on a solder-mask layer = a mask OPENING (exposed copper)."""
    r = dia / 2.0
    return ('\t(gr_circle\n\t\t(center %.4f %.4f)\n\t\t(end %.4f %.4f)\n'
            '\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n'
            '\t\t(fill yes)\n\t\t(layer "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (cx, cy, cx + r, cy, layer, uuid.uuid4()))


def strip_mask_apertures(t, centers):
    """Remove filled F/B.Mask circles centered on any of `centers` (our screw
    apertures), so a re-run replaces them. Position-matched so it never touches
    an unrelated mask graphic."""
    out, i, removed = [], 0, 0
    while True:
        j = t.find('\t(gr_circle\n', i)
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
        end = k + 1 + (1 if k + 1 < len(t) and t[k + 1] == '\n' else 0)
        m = re.search(r'\(center ([-\d.]+) ([-\d.]+)\)', blk)
        onmask = re.search(r'\(layer "[FB]\.Mask"\)', blk) and '(fill yes)' in blk
        hit = m and onmask and any(abs(float(m.group(1)) - cx) < 0.5 and
                                   abs(float(m.group(2)) - cy) < 0.5 for cx, cy in centers)
        if hit:
            out.append(t[i:j]); removed += 1
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


CUTOUT_MIN_PERIMETER_MM = 15.0   # cutouts whose perimeter >= this get an inner
                                 # stitching ring. Ø7 SMA (22.0) and the USB slot
                                 # (~67 at the offset ring) qualify; Ø3.4 M3 (10.7)
                                 # and Ø2 status (6.3) do not. Raise past 22 for a
                                 # USB-only ring (excludes the SMAs).
CUTOUT_KEEPOUT_GAP_MM = 0.75     # for a circular cutout that also has an SMA pour
                                 # keepout, the ring is offset this far OUTSIDE the
                                 # keepout edge (not the hole), so its vias sit in
                                 # pour and clear the washer instead of landing in
                                 # the no-pour zone.


def _circumcenter(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by)) / d
    uy = ((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax)) / d
    return (ux, uy)


def _arc_points(s, m, e):
    """Tessellate a KiCad 3-point (start, mid, end) arc into an ordered list."""
    c = _circumcenter(s, m, e)
    if not c:
        return [s, e]
    r = math.hypot(s[0]-c[0], s[1]-c[1])
    a0 = math.atan2(s[1]-c[1], s[0]-c[0])
    a1 = math.atan2(e[1]-c[1], e[0]-c[0])
    am = math.atan2(m[1]-c[1], m[0]-c[0])
    tau = 2*math.pi
    sweep = (a1 - a0) % tau                            # CCW sweep a0 -> a1
    if ((am - a0) % tau) > sweep:                      # mid not on it -> go CW
        sweep -= tau
    n = max(2, int(abs(sweep) * r / ARC_TESS_MM))
    return [(c[0]+r*math.cos(a0+sweep*i/n), c[1]+r*math.sin(a0+sweep*i/n))
            for i in range(n+1)]


def _close(a, b, tol=1e-3):
    return math.hypot(a[0]-b[0], a[1]-b[1]) <= tol


def edge_loops(t):
    """Chain Edge.Cuts line/arc segments into closed loops (dense polylines)."""
    segs = []
    for b in _blocks(t, 'gr_line'):
        if _layer(b) == 'Edge.Cuts':
            segs.append([_xy(b, 'start'), _xy(b, 'end')])
    for b in _blocks(t, 'gr_arc'):
        if _layer(b) == 'Edge.Cuts':
            segs.append(_arc_points(_xy(b, 'start'), _xy(b, 'mid'), _xy(b, 'end')))
    used, loops = [False]*len(segs), []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        loop = list(segs[i])
        advanced = True
        while advanced:
            advanced = False
            for j in range(len(segs)):
                if used[j]:
                    continue
                s0, s1 = segs[j][0], segs[j][-1]
                if _close(loop[-1], s0):
                    loop += segs[j][1:]
                elif _close(loop[-1], s1):
                    loop += segs[j][-2::-1]
                else:
                    continue
                used[j] = True; advanced = True; break
        if len(loop) > 2 and _close(loop[0], loop[-1]):
            loops.append(loop[:-1])                    # drop duplicated closing pt
    return loops


def _perimeter(loop):
    n = len(loop)
    return sum(math.hypot(loop[(i+1) % n][0]-loop[i][0],
                          loop[(i+1) % n][1]-loop[i][1]) for i in range(n))


def _densify(loop, step):
    """Insert points along each edge so straight runs offset by the full normal
    distance (a sparse rectangle would otherwise drag its edges in at the corners)."""
    out, n = [], len(loop)
    for i in range(n):
        a, b = loop[i], loop[(i+1) % n]
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        k = max(1, int(d / step))
        for j in range(k):
            f = j / k
            out.append((a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f))
    return out


def offset_outward(loop, dist):
    """Push each vertex `dist` mm along its outward (away-from-centroid) normal."""
    cx = sum(p[0] for p in loop) / len(loop)
    cy = sum(p[1] for p in loop) / len(loop)
    n, out = len(loop), []
    for i in range(n):
        a, b, c = loop[(i-1) % n], loop[i], loop[(i+1) % n]
        nx, ny = -(c[1]-a[1]), (c[0]-a[0])            # normal = perp of tangent
        L = math.hypot(nx, ny) or 1.0
        nx, ny = nx/L, ny/L
        if nx*(b[0]-cx) + ny*(b[1]-cy) < 0:           # orient away from centroid
            nx, ny = -nx, -ny
        out.append((b[0]+dist*nx, b[1]+dist*ny))
    return out


def cutout_ring_pts(t, g, sma_keepout=False):
    """Stitch-via centers ringing every cutout with perimeter >= threshold:
    circular cutouts (g['holes']) as concentric rings just outside the hole;
    polygonal cutouts (assembled Edge.Cuts loops, minus the outer boundary) as
    outward-offset rings. Same pitch as the perimeter ring. A circular cutout that
    also carries an SMA pour keepout is ringed outside the KEEPOUT (so the vias
    stay in pour and clear the washer), otherwise INSET outside the hole."""
    pts = []
    for h in g['holes']:                              # circular cutouts (SMA)
        hx, hy, hr = h
        if 2*math.pi*hr < CUTOUT_MIN_PERIMETER_MM:
            continue
        if sma_keepout and hr >= SMA_HOLE_MIN_R:
            rr = SMA_KEEPOUT_DIA_MM / 2 + CUTOUT_KEEPOUT_GAP_MM   # clear the keepout
        else:
            rr = hr + INSET_MM
        nn = max(4, round(2*math.pi*rr / PITCH_MM))
        for i in range(nn):
            ang = 2*math.pi*i/nn
            p = (hx + rr*math.cos(ang), hy + rr*math.sin(ang))
            if keep(p, g['holes'], skip=h):
                pts.append(p)
    loops = edge_loops(t)                             # polygonal cutouts (USB)
    if loops:
        def bbox_area(L):
            xs = [p[0] for p in L]; ys = [p[1] for p in L]
            return (max(xs)-min(xs)) * (max(ys)-min(ys))
        outer = max(loops, key=bbox_area)
        for L in loops:
            if L is outer or _perimeter(L) < CUTOUT_MIN_PERIMETER_MM:
                continue
            ring = offset_outward(_densify(L, ARC_TESS_MM * 2), INSET_MM)
            for p in resample(ring, PITCH_MM):
                if keep(p, g['holes']):
                    pts.append(p)
    return pts


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
    ap.add_argument('--sma-keepout', action='store_true',
                    help='also emit Ø%.0f copper-pour keepout zones around holes '
                         'with r>=%.1f (SMA holes)' % (SMA_KEEPOUT_DIA_MM,
                                                       SMA_HOLE_MIN_R))
    ap.add_argument('--screw-mask', action='store_true',
                    help='open Ø%.0f exposed-copper mask apertures (F+B) at the M3 '
                         'mounting holes to ground the shield to the enclosure'
                         % SCREW_MASK_DIA_MM)
    ap.add_argument('--cutout-stitch', action='store_true',
                    help='also ring the perimeter of large interior cutouts '
                         '(perimeter >= %.0f mm: USB slot + SMA holes; skips M3 / '
                         'status)' % CUTOUT_MIN_PERIMETER_MM)
    a = ap.parse_args()
    t = open(a.pcb).read()
    removed = 0
    if not a.keep:
        t, removed = strip_matching_vias(t)
    g = parse(t)
    pts = [p for p in resample(ring_path(g), PITCH_MM) if keep(p, g['holes'])]
    cut_pts = cutout_ring_pts(t, g, a.sma_keepout) if a.cutout_stitch else []
    zoned = 0
    if a.net and not a.dry_run:
        t, zoned = set_zone_nets(t, a.net)
    sma_txt, nkeep, rmk = "", 0, 0
    if a.sma_keepout:
        if not a.dry_run:
            t, rmk = strip_sma_keepouts(t)
        big = [(hx, hy) for hx, hy, hr in g['holes'] if hr >= SMA_HOLE_MIN_R]
        nkeep = len(big)
        sma_txt = "".join(sma_keepout_zone(hx, hy, SMA_KEEPOUT_DIA_MM) for hx, hy in big)
    mask_txt, nmask, rmm = "", 0, 0
    if a.screw_mask:
        mounts = [(hx, hy) for hx, hy, hr in g['holes']
                  if MOUNT_HOLE_MIN_R <= hr < SMA_HOLE_MIN_R]
        if not a.dry_run:
            t, rmm = strip_mask_apertures(t, mounts)
        nmask = len(mounts)
        mask_txt = "".join(mask_aperture(hx, hy, SCREW_MASK_DIA_MM, lyr)
                           for hx, hy in mounts for lyr in ("F.Mask", "B.Mask"))
    print("outline %.2f x %.2f mm, corner R=%.2f, %d holes"
          % (g['maxx'] - g['minx'], g['maxy'] - g['miny'], g['R'], len(g['holes'])))
    print("removed %d ring via(s); placing %d (inset %.2f, pitch %.2f, net %r); "
          "netted %d fill zone(s)"
          % (removed, len(pts), INSET_MM, PITCH_MM, a.net, zoned))
    if a.sma_keepout:
        print("SMA keepout: removed %d, adding %d zone(s) of Ø%.1f"
              % (rmk, nkeep, SMA_KEEPOUT_DIA_MM))
    if a.screw_mask:
        print("screw mask: removed %d, adding %d aperture(s) x2 faces (Ø%.1f)"
              % (rmm, nmask, SCREW_MASK_DIA_MM))
    if a.cutout_stitch:
        print("cutout stitch: %d via(s) ringing cutouts with perimeter >= %.0f mm"
              % (len(cut_pts), CUTOUT_MIN_PERIMETER_MM))
    if a.dry_run:
        return
    inject = "".join(via_sexpr(x, y, a.net) for x, y in pts + cut_pts)
    cut = t.rstrip()
    assert cut.endswith(')'), "unexpected file tail"
    new = cut[:-1] + inject + sma_txt + mask_txt + ")\n"
    open(a.out or a.pcb, 'w').write(new)
    print("wrote", a.out or a.pcb)


if __name__ == '__main__':
    main()
