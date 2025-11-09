#!/usr/bin/env python3
"""
Recipe Library – Mascot + Logo Generator (SVG-first, PNG exports)
- Cute cartoon French Bulldog chef (tan, white hat/apron)
- Horizontal & stacked logos, with/without tagline
- Social icon and favicons (16/32/64/128)
Outputs to ./out with both SVG and PNG variants.

Deps: pip install svgwrite cairosvg
"""

import os
from pathlib import Path
import math
import svgwrite
from cairosvg import svg2png

# ---------- Config ----------
BRAND_NAME = "Recipe Library"
TAGLINE = "Discover. Cook. Enjoy."
OUT_DIR = Path("out")
DPI = 72  # web use
TEXT_COLOR = "#1b1b1b"

# Palette (warm, approachable)
COLORS = {
    "stroke": "#2b2b2b",
    "tan": "#e9c9a5",
    "tan_shade": "#d7b38b",
    "ear_inner": "#f3d8be",
    "nose_mouth": "#5a463a",
    "white": "#ffffff",
    "shadow": "#000020",
}

STROKE_W = 4

# ---------- Helpers ----------
def ensure_out():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def export_svg_and_png(svg: svgwrite.Drawing, out_svg_path: Path, png_sizes=None):
    svg.saveas(out_svg_path)
    if png_sizes:
        for size in png_sizes:
            out_png = out_svg_path.with_suffix(f".{size}px.png")
            svg2png(url=str(out_svg_path), write_to=str(out_png), output_width=size, output_height=size, dpi=DPI)

def export_svg_and_png_any(svg: svgwrite.Drawing, out_svg_path: Path, png_width=None):
    svg.saveas(out_svg_path)
    if png_width:
        # Keep aspect ratio by letting CairoSVG infer height
        svg2png(url=str(out_svg_path), write_to=str(out_svg_path.with_suffix(".png")), output_width=png_width, dpi=DPI)

# ---------- Mascot Drawing ----------
def draw_bulldog_group(d: svgwrite.Drawing, scale=1.0, center=(0, 0)):
    """
    Returns a <g> group containing a cute French bulldog chef (front-facing),
    sized to ~300x300 at scale=1.
    """
    g = d.g()
    cx, cy = center
    s = scale

    stroke = {"stroke": COLORS["stroke"], "stroke_width": STROKE_W*s, "stroke_linecap": "round", "stroke_linejoin": "round"}
    fillnone = {"fill": "none", **stroke}

    # Base head ellipse
    head_w, head_h = 200*s, 170*s
    head = d.ellipse(center=(cx, cy), r=(head_w/2, head_h/2), fill=COLORS["tan"], **stroke)
    g.add(head)

    # Head center lighter mask stripe (optional subtle)
    stripe_w = 32*s
    head_stripe = d.rect(insert=(cx - stripe_w/2, cy - head_h/2 + 20*s),
                         size=(stripe_w, head_h - 40*s),
                         rx=14*s, ry=14*s,
                         fill=COLORS["tan_shade"], stroke="none")
    g.add(head_stripe)

    # Ears
    ear_offset_x = 88*s
    ear_top_y = cy - head_h/2 - 10*s
    for sign in (-1, 1):
        ear = d.path(d=("M {x1} {y1} "
                        "Q {x2} {y2} {x3} {y3} "
                        "Q {x4} {y4} {x1} {y1}").format(
            x1=cx + sign*(ear_offset_x), y1=cy - 30*s,
            x2=cx + sign*(ear_offset_x + 16*s), y2=ear_top_y,
            x3=cx + sign*(ear_offset_x - 10*s), y3=ear_top_y,
            x4=cx + sign*(ear_offset_x - 18*s), y4=cy - 30*s
        ), fill=COLORS["tan"], **stroke)
        g.add(ear)
        inner = d.ellipse(center=(cx + sign*(ear_offset_x-5*s), cy - 55*s),
                          r=(18*s, 26*s), fill=COLORS["ear_inner"], **stroke)
        g.add(inner)

    # Eyes
    eye_dx, eye_y = 42*s, cy - 10*s
    for sign in (-1, 1):
        g.add(d.circle(center=(cx + sign*eye_dx, eye_y), r=8*s, fill=COLORS["stroke"]))

    # Nose/muzzle
    muzzle = d.ellipse(center=(cx, cy + 32*s), r=(60*s, 42*s), fill=COLORS["tan_shade"], **stroke)
    g.add(muzzle)
    nose = d.path(d=f"M {cx-10*s} {cy+22*s} Q {cx} {cy+12*s} {cx+10*s} {cy+22*s}",
                  fill="none", **{"stroke": COLORS["nose_mouth"], "stroke_width": 5*s, "stroke_linecap": "round"})
    g.add(nose)
    mouth = d.path(d=f"M {cx-25*s} {cy+42*s} Q {cx} {cy+58*s} {cx+25*s} {cy+42*s}",
                   fill="none", **{"stroke": COLORS["nose_mouth"], "stroke_width": 5*s, "stroke_linecap": "round"})
    g.add(mouth)

    # Body (simple), apron
    body = d.rect(insert=(cx-85*s, cy+60*s), size=(170*s, 130*s), rx=28*s, ry=28*s, fill=COLORS["tan"], **stroke)
    g.add(body)
    apron = d.rect(insert=(cx-70*s, cy+70*s), size=(140*s, 120*s), rx=16*s, ry=16*s, fill=COLORS["white"], **stroke)
    g.add(apron)
    neck = d.rect(insert=(cx-36*s, cy+54*s), size=(72*s, 24*s), rx=8*s, ry=8*s, fill=COLORS["tan_shade"], **stroke)
    g.add(neck)

    # Arms (down, neutral)
    for sign in (-1, 1):
        arm = d.path(d=("M {x} {y} q {c1x} {c1y} {dx} {dy} "
                        "q {c2x} {c2y} {dx2} {dy2}").format(
            x=cx + sign*(75*s), y=cy+80*s,
            c1x=sign*(20*s), c1y=30*s, dx=sign*(0), dy=40*s,
            c2x=sign*(-20*s), c2y=30*s, dx2=sign*(-30*s), dy2=20*s
        ), fill=COLORS["tan"], **stroke)
        g.add(arm)

    # Chef hat
    hat_base = d.rect(insert=(cx-70*s, cy- head_h/2 - 8*s), size=(140*s, 36*s), rx=12*s, ry=12*s, fill=COLORS["white"], **stroke)
    g.add(hat_base)
    # three puffs
    for i, off in enumerate([-55, 0, 55]):
        puff = d.circle(center=(cx + off*s, cy - head_h/2 - 18*s), r=38*s if i==1 else 32*s, fill=COLORS["white"], **stroke)
        g.add(puff)

    # Ground shadow (subtle)
    g.add(d.ellipse(center=(cx, cy+200*s), r=(110*s, 16*s), fill=COLORS["shadow"], stroke="none"))

    return g
# 1) Update add_text()
def add_text(d, g, text, x, y, size_px, weight="700"):
    g.add(d.text(
        text,
        insert=(x, y),
        fill=TEXT_COLOR,
        font_family="Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
        font_weight=weight,             # "700" or "bold"
        font_size=f"{size_px}px",       # must include unit
        letter_spacing="0.2px"          # formerly in style string
    ))

# 2) Use SVG Full profile (or omit profile)
def logo_horizontal(with_tagline=True, width=1400, height=500):
    d = svgwrite.Drawing(size=(width, height), profile="full")  # was "tiny"
    ...
    return d

def logo_stacked(with_tagline=True, width=900, height=1000):
    d = svgwrite.Drawing(size=(width, height), profile="full")
    g = d.g()
    d.add(g)

    mascot = draw_bulldog_group(d, scale=1.0, center=(width//2, 340))
    g.add(mascot)

    add_text(d, g, BRAND_NAME, 140, 700, 90, "700")
    if with_tagline:
        add_text(d, g, TAGLINE, 140, 770, 40, "500")

    return d


def social_icon_square(width=1024, height=1024):
    d = svgwrite.Drawing(size=(width, height), profile="full")
    g = d.g()
    d.add(g)
    # Face larger, crop shoulders – just move center up
    mascot = draw_bulldog_group(d, scale=1.2, center=(width//2, height//2 - 40))
    g.add(mascot)
    return d

def favicon(size):
    d = svgwrite.Drawing(size=(size, size), profile="full")
    ...
    return d


    # Mascot
    s = 1.0
    mascot = draw_bulldog_group(d, scale=1.0, center=(260, height//2 - 20))
    g.add(mascot)

    # Text block
    left = 460
    add_text(d, g, BRAND_NAME.split()[0], left, 220, 120, "700")
    add_text(d, g, BRAND_NAME.split()[1], left, 340, 120, "700")
    if with_tagline:
        add_text(d, g, TAGLINE, left, 400, 44, "500")

    return d

# ---------- Main ----------
def main():
    ensure_out()

    # 1) Logos
    horiz_tag = logo_horizontal(True)
    export_svg_and_png_any(horiz_tag, OUT_DIR / "RecipeLibrary_Horizontal_Tagline.svg", png_width=1400)

    horiz = logo_horizontal(False)
    export_svg_and_png_any(horiz, OUT_DIR / "RecipeLibrary_Horizontal.svg", png_width=1400)

    stacked_tag = logo_stacked(True)
    export_svg_and_png_any(stacked_tag, OUT_DIR / "RecipeLibrary_Stacked_Tagline.svg", png_width=900)

    stacked = logo_stacked(False)
    export_svg_and_png_any(stacked, OUT_DIR / "RecipeLibrary_Stacked.svg", png_width=900)

    # 2) Social icon (square)
    social = social_icon_square(1024, 1024)
    export_svg_and_png_any(social, OUT_DIR / "Bulldog_Face_Social.svg", png_width=1024)

    # 3) Favicons
    for sz in (16, 32, 64, 128):
        fav = favicon(sz)
        export_svg_and_png(fav, OUT_DIR / f"favicon_{sz}.svg", png_sizes=[sz])

    print(f"Done. Assets written to: {OUT_DIR.resolve()}")

if __name__ == "__main__":
    main()
