#!/usr/bin/env python3
"""Wrap the mechanical-assembly GLB in a self-contained interactive HTML viewer.

Inlines the model-viewer library and base64-embeds the GLB, so the output is a
single .html file that spins the assembly in any browser -- no CAD tools, no
network. Built by mechanical-ci and uploaded as an artifact.
"""
import argparse
import base64


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glb", required=True)
    ap.add_argument("--lib", required=True, help="model-viewer bundle to inline")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rev", default="", help="short git sha for the header")
    a = ap.parse_args()

    glb_b64 = base64.b64encode(open(a.glb, "rb").read()).decode("ascii")
    lib = open(a.lib, encoding="utf-8").read()
    # A literal </script> would close our inline block; neutralise it (identical
    # semantics inside JS strings/regex).
    lib = lib.replace("</script", "<\\/script")

    rev = (" &middot; " + a.rev) if a.rev else ""
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TAPRX-888 - mechanical fit-check</title>
<script type="module">{lib}</script>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  html, body {{ height:100%; }}
  body {{ margin:0; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    background:#14171a; color:#e7ebee; display:flex; flex-direction:column; }}
  header {{ padding:14px 20px; border-bottom:1px solid #2a3037; flex:0 0 auto; }}
  h1 {{ margin:0; font-size:17px; font-weight:620; letter-spacing:-.01em; }}
  header p {{ margin:4px 0 0; font-size:12.5px; color:#98a1a7; }}
  /* the viewport fills the remaining height; min-height:0 lets the flex child
     actually shrink/grow instead of collapsing to model-viewer's default size */
  .wrap {{ position:relative; flex:1 1 auto; min-height:0; }}
  model-viewer {{ position:absolute; inset:0; width:100%; height:100%;
    background: radial-gradient(120% 120% at 50% 25%, #20262c 0%, #101315 70%); }}
  .legend {{ position:absolute; left:16px; bottom:14px; display:flex; gap:14px;
    flex-wrap:wrap; font-size:12px; background:rgba(20,23,26,.72); padding:8px 12px;
    border:1px solid #2a3037; border-radius:9px; backdrop-filter:blur(3px); }}
  .legend b {{ display:inline-block; width:11px; height:11px; border-radius:3px;
    margin-right:5px; vertical-align:-1px; }}
  .hint {{ position:absolute; right:16px; bottom:14px; font-size:11.5px;
    color:#8b939a; background:rgba(20,23,26,.72); padding:6px 10px;
    border:1px solid #2a3037; border-radius:9px; }}
</style>
</head><body>
<header>
  <h1>TAPRX-888 &mdash; mechanical fit-check</h1>
  <p>Enclosure &middot; main board &middot; front / rear end plates{rev}. Drag to orbit, scroll to zoom.</p>
</header>
<div class="wrap">
  <model-viewer
    src="data:model/gltf-binary;base64,{glb_b64}"
    alt="TAPRX-888 enclosure, board and end plates assembled"
    camera-controls touch-action="pan-y"
    camera-orbit="-40deg 62deg auto" orientation="180deg 0deg 0deg" interaction-prompt="none"
    shadow-intensity="0.6" exposure="1.05"
    environment-image="neutral" min-field-of-view="10deg" max-field-of-view="45deg">
  </model-viewer>
  <div class="legend">
    <span><b style="background:#9ea3a6"></b>enclosure</span>
    <span><b style="background:#1e4488"></b>main board</span>
    <span><b style="background:#1e4488"></b>end plates</span>
  </div>
  <div class="hint">no CAD tool needed &middot; opens offline</div>
</div>
</body></html>"""

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", a.out, len(doc), "bytes")


if __name__ == "__main__":
    main()
