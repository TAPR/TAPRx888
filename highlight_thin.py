# highlight_thin.py  --  TAPRX-888 DFM helper
# Paste into KiCad 10 PCB editor:  Tools -> Scripting Console
# Then call:   highlight()            # glow every track <= 0.1 mm
#              highlight(0.1)         # same, explicit threshold
#              highlight(net="/RESET_N")      # just one net
#              highlight(layer="F.Cu")        # just one layer
#              highlight(0.1, net="/SCL")     # combine
#              clear()                # remove the glow
#              upsize("/RESET_N", 0.2)         # see note at bottom
#
# "brighten" is a non-destructive display flag -- it changes nothing in the
# design, costs no undo step, and clear() fully reverts it.

import pcbnew

_b = pcbnew.GetBoard()
_TRACKISH = (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T)   # segments + arcs, NOT vias

def _tracks():
    for t in _b.GetTracks():
        if t.Type() in _TRACKISH:
            yield t

def highlight(width_mm=0.1, net=None, layer=None, tol_mm=1e-4):
    """Brighten every track at or below width_mm. Optional net/layer filter."""
    thr = pcbnew.FromMM(width_mm) + pcbnew.FromMM(tol_mm)
    n = 0
    total_nm = 0
    for t in _tracks():
        if t.GetWidth() > thr:
            continue
        if net is not None and t.GetNetname() != net:
            continue
        if layer is not None and _b.GetLayerName(t.GetLayer()) != layer:
            continue
        t.SetBrightened()
        n += 1
        total_nm += t.GetLength()
    pcbnew.Refresh()
    print("brightened %d tracks  (%.1f mm copper)" % (n, pcbnew.ToMM(total_nm)))
    return n

def clear():
    """Remove all brighten flags."""
    for t in _tracks():
        t.ClearBrightened()
    pcbnew.Refresh()
    print("cleared")

# --- escape-zone keep-outs: FX3 (U11) @ (156,81) body +-4.0, LTC2208 (U8) @
# (156,95) body +-4.4; +margin for the dog-bone fanout. Segments touching either
# box stay thin. Edit MARGIN to grow/shrink the protected ring. ----------------
MARGIN = 1.5
_ZONES = [(152.0-MARGIN, 160.0+MARGIN, 77.0-MARGIN, 85.0+MARGIN),   # U11 FX3
          (151.6-MARGIN, 160.4+MARGIN, 90.6-MARGIN, 99.4+MARGIN)]   # U8 LTC2208

def _in_zone(x, y):
    for x0, x1, y0, y1 in _ZONES:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False

def _touches_zone(t):
    s, e = t.GetStart(), t.GetEnd()
    sx, sy = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
    ex, ey = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
    return _in_zone(sx, sy) or _in_zone(ex, ey) or _in_zone((sx+ex)/2, (sy+ey)/2)

def upsize_open(from_mm=0.1, to_mm=0.15, layer=None, tol_mm=1e-4, dry=True):
    """Widen every <=from_mm track that is ENTIRELY outside the FX3/LTC2208
    escape zones, to to_mm. Leaves in-zone escape copper untouched.
    dry=True just reports; call upsize_open(dry=False) to actually change the
    board, then run DRC."""
    thr = pcbnew.FromMM(from_mm) + pcbnew.FromMM(tol_mm)
    neww = pcbnew.FromMM(to_mm)
    n = skipped = 0
    chg_nm = 0
    for t in _tracks():
        if t.GetWidth() > thr:
            continue
        if layer is not None and _b.GetLayerName(t.GetLayer()) != layer:
            continue
        if _touches_zone(t):
            skipped += 1
            continue
        chg_nm += t.GetLength()
        if not dry:
            t.SetWidth(neww)
        n += 1
    if not dry:
        pcbnew.Refresh()
    print("%s %d open-board tracks %.3f->%.3f mm (%.1f mm copper); kept %d in-zone"
          % ("WOULD widen" if dry else "WIDENED", n, from_mm, to_mm,
             pcbnew.ToMM(chg_nm), skipped))
    if not dry:
        print(">>> now run DRC (Inspect -> Design Rules Checker)")
    return n

def upsize(net, width_mm, only_width_mm=0.1, layer=None, tol_mm=1e-4):
    """Set every <=only_width_mm track on `net` to width_mm. Commits an undo-able
    change. Run DRC afterwards -- widening can shrink clearance to neighbours.
    Pass net=None to hit ALL nets at that width (use with care)."""
    thr = pcbnew.FromMM(only_width_mm) + pcbnew.FromMM(tol_mm)
    neww = pcbnew.FromMM(width_mm)
    n = 0
    for t in _tracks():
        if t.GetWidth() > thr:
            continue
        if net is not None and t.GetNetname() != net:
            continue
        if layer is not None and _b.GetLayerName(t.GetLayer()) != layer:
            continue
        t.SetWidth(neww)
        n += 1
    pcbnew.Refresh()
    print("set %d tracks to %.3f mm on net=%r -- now run DRC" % (n, width_mm, net))
    return n
