"""Render entry.png: the world's news of Friday 20 November 2026.

A single 1024x1024 newspaper front page drawn entirely with Pillow:
masthead, a full-width UTC timeline ruler, four lead
stories (the S&P 500 card is a dark-navy anchor), twelve medium cards,
a world map with 16 numbered dots and 30 small brief dots (no leader
lines, no anchor dots), thirty briefs with real flags,
a Date Check strip, one Markets/Sport bar, and a
footer. No network at runtime: the brief and card flags are real
flag images (flagcdn.com) stored locally under assets/flags/ and
loaded from disk; every other picture on the page is an original
Pillow drawing.

Run:  python build.py   (writes entry.png next to this file)

Rendering quality: Pillow's ImageDraw shapes (polygons, lines,
circles, arcs) are NOT anti-aliased, so a 1x render leaves stepped
edges. The page is therefore drawn at SS x resolution (4096x4096)
in 1024-space coordinates — every coordinate, font size and line
width scaled by the same factor — and downscaled to exactly
1024x1024 with BOX before saving. BOX (not LANCZOS): at 4x
supersampling each output pixel still averages 16 source pixels,
so diagonals stay smooth, while 1px strokes keep full strength
instead of washing to ~87% grey. Layout, positions, sizes and
words are identical to a 1x render; only the edges are smoother.
If the file ever exceeds the 1 MiB cap, drop SS to 2.
"""

import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import stories as S

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE / "fonts"
FLAG_DIR = HERE / "assets" / "flags"
MERR = FONT_DIR / "Merriweather-VF.ttf"
INTER = FONT_DIR / "Inter-VF.ttf"
ARCHIVO = FONT_DIR / "Archivo-VF.ttf"

W = H = 1024
PAPER = (250, 247, 238)
PANEL = (255, 255, 255)
PANEL_BORDER = (210, 205, 192)
INK = (26, 26, 26)
DEK = (74, 72, 66)
MUTED = (110, 106, 96)
# SOURCE (2026-11-21, user order): the colour of EVERY source
# credit on the page — brief labels, card sources, lead sources.
# A deep violet (98, 56, 158), chosen because no violet/purple
# appears anywhere else in the paper (red, navy, ink, warm greys,
# gold, teal are all taken), so a source credit is instantly
# recognisable as a source, and because it is dark and saturated
# enough to read clearly at 8–9px against the cream paper — far
# more visible than the old muted greys (DEK/MUTED) it replaces.
SOURCE = (98, 56, 158)
RED = (176, 32, 32)
NAVY = (13, 27, 62)
NAVY2 = (16, 32, 74)
NAVY_PALE = (205, 214, 232)
NAVY_LABEL = (180, 195, 225)
ANCHOR_YELLOW = (250, 220, 130)
ANCHOR_RED = (220, 60, 50)

BADGES = {
    "CONFIRMED": ((213, 240, 216), (27, 94, 32)),
    "CLAIMED": ((255, 232, 204), (176, 86, 0)),
    "REPORTED": ((214, 232, 248), (30, 80, 150)),
}

_font_cache = {}

# ------------------------------------------------------- supersampling (SS)
# The whole page is drawn at SS x resolution in 1024-space
# coordinates, then downscaled with BOX (see build()). SSFont
# loads each font at SS x size for rendering while reporting 1x
# metrics, so every wrap/fit/leading calculation is unchanged;
# SSDraw scales every coordinate, radius and line width by SS.
# getbbox() is deliberately NOT overridden on SSFont: draw.text's
# anchor math needs it at render scale to match the scaled
# coordinates. All font sizes in this file are multiples of 0.5, so
# size * SS is always an exact integer (no rounding drift).
SS = 4


def _sc(v):
    return v * SS


def _sc_xy(xy):
    """Scale a Pillow coordinate argument by SS: a flat [x0, y0, ...]
    box, a list of (x, y) points, or a single (x, y) pair."""
    if isinstance(xy, (list, tuple)) and xy \
            and isinstance(xy[0], (int, float)):
        return [_sc(v) for v in xy]
    return [(_sc(px), _sc(py)) for px, py in xy]


def _sc_box(xy):
    """Scale an inclusive Pillow box [x0, y0, x1, y1] by SS. The 1x
    box covers output pixels x0..x1, so the SS box must run to
    SS*x1 + SS-1, not SS*x1: without the +SS-1 the fill ends 3/4 of a
    pixel early and the bottom/right outlines smear into the row
    above (the outer frame's right/bottom edges wash out)."""
    x0, y0, x1, y1 = xy
    return [_sc(x0), _sc(y0), _sc(x1) + SS - 1, _sc(y1) + SS - 1]


class SSFont(ImageFont.FreeTypeFont):
    """Variable font loaded at SS x size, reporting 1x metrics."""

    def __init__(self, path, size, axes=None):
        super().__init__(str(path), int(round(size * SS)))
        self.size = size
        if axes is not None:
            try:
                self.set_variation_by_axes(axes)
            except Exception:
                pass

    def getlength(self, text, *args, **kwargs):
        return super().getlength(text, *args, **kwargs) / SS


class SSDraw:
    """Wraps ImageDraw.Draw, scaling every coordinate, radius and
    line width by SS. Colours, strings, anchors and fonts pass
    through untouched (fonts are already SS-sized via SSFont)."""

    def __init__(self, draw, img=None):
        self._d = draw
        self._img = img

    def paste(self, im, xy):
        """Paste a PIL image at 1x coords (x, y), scaled to SS.
        An RGBA image pastes with its alpha as mask, so the
        transparent surround of a fitted flag shows whatever is
        underneath (paper in the briefs, art background in cards)."""
        x, y = int(_sc(xy[0])), int(_sc(xy[1]))
        if im.mode == "RGBA":
            self._img.paste(im.convert("RGB"), (x, y), im.split()[3])
        else:
            self._img.paste(im, (x, y))

    @staticmethod
    def _width(kw, default=1):
        """Line width, scaled; Pillow defaults outlines to 1px.
        Rounded to int: Pillow rejects float widths, and a 1.5px
        outline (6 SS px) must land exactly."""
        return int(round(kw.pop("width", default) * SS))

    def rectangle(self, xy, fill=None, outline=None, **kw):
        if outline is not None:
            kw["outline"] = outline
            kw["width"] = self._width(kw)
        if fill is not None:
            kw["fill"] = fill
        self._d.rectangle(_sc_box(xy), **kw)

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None,
                          **kw):
        if outline is not None:
            kw["outline"] = outline
            kw["width"] = self._width(kw)
        if fill is not None:
            kw["fill"] = fill
        self._d.rounded_rectangle(_sc_box(xy), radius=radius * SS, **kw)

    def ellipse(self, xy, fill=None, outline=None, **kw):
        if outline is not None:
            kw["outline"] = outline
            kw["width"] = self._width(kw)
        if fill is not None:
            kw["fill"] = fill
        self._d.ellipse(_sc_box(xy), **kw)

    def polygon(self, xy, fill=None, outline=None, **kw):
        pts = [(_sc(px), _sc(py)) for px, py in xy]
        if fill is not None:
            kw["fill"] = fill
        self._d.polygon(pts, **kw)
        if outline is not None:
            # Pillow polygon outlines are always 1px; redraw the edge
            # as a line so it scales like every other stroke.
            self._d.line(pts + [pts[0]], fill=outline, width=SS,
                         joint="curve")

    def line(self, xy, fill=None, width=None, joint=None, **kw):
        # Pillow's draw_lines needs int coordinates (integral floats
        # raise TypeError), so round the scaled values: every other
        # caller passes integer 1x coords, for which this is a no-op.
        # _sc_xy returns a flat list for [x0, y0, ...] but a list of
        # (x, y) tuples for a polyline — flatten both.
        pts = _sc_xy(xy)
        flat = []
        for p in pts:
            if isinstance(p, (list, tuple)):
                flat.extend(int(round(v)) for v in p)
            else:
                flat.append(int(round(p)))
        self._d.line(flat, fill=fill,
                     width=int(round((1 if width is None else width)
                                     * SS)),
                     joint=joint, **kw)

    def arc(self, xy, start, end, fill=None, width=None, **kw):
        self._d.arc(_sc_box(xy), start, end, fill=fill,
                    width=(1 if width is None else width) * SS, **kw)

    def text(self, xy, text, fill=None, font=None, anchor=None, **kw):
        self._d.text(_sc_xy(xy), text, fill=fill, font=font,
                     anchor=anchor, **kw)


_flag_cache = {}
_flag_src_size = {}


def _flag_fit(code, w, h):
    """Fitted flag size in render (SS) px inside a w x h slot (1x px),
    preserving the flag's true aspect ratio: most flags are 3:2 and
    fill the slot, 2:1 flags (US, GB, PH, NG) come out shorter,
    Denmark narrower, Nepal's pennant narrowest. Shared by
    _flag_image and _flag_outline, so the outline hugs the exact
    pixels the flag occupies — never the empty slot around it."""
    if code not in _flag_src_size:
        with Image.open(FLAG_DIR / (code.lower() + ".png")) as src:
            _flag_src_size[code] = src.size
    sw, sh = _flag_src_size[code]
    scale = min(w * SS / sw, h * SS / sh)
    return max(1, round(sw * scale)), max(1, round(sh * scale))


def _flag_outline(draw, x, y, code, w, h):
    """The uniform flag treatment, briefs and cards alike: one subtle
    1px hairline (180, 175, 165 — the page's hairline tone) hugging
    the flag's true fitted edges, centred in its slot. Pixel-level
    inspection of the 18 Nov winner shows its flags are in fact bare
    — no drawn border or shadow, just flag pixels on paper — but bare
    leaves a white field (Japan, Nepal) edgeless on paper, so the
    entry keeps this hairline: same tone, same weight, same fit on
    every flag. Offsets reuse _flag_image's integer-centred paste,
    so outline and flag share exact edges."""
    nw, nh = _flag_fit(code, w, h)
    ox = ((w * SS - nw) // 2) / SS
    oy = ((h * SS - nh) / 2) / SS
    draw.rectangle([x + ox, y + oy, x + ox + nw / SS, y + oy + nh / SS],
                   outline=(180, 175, 165))


def _flag_image(code, w, h):
    """Real flag from assets/flags, fitted inside a w x h box (1x px)
    at SS resolution, preserving its true aspect ratio and centred
    — the winner's style is a small real flag in a fixed slot next
    to each brief line, no chip. Most flags are 3:2 and fill the
    18x12 slot exactly; 2:1 flags (US, GB, PH, NG) sit 18x9 in it,
    Denmark 16x12, and Nepal's pennant ~10x12. Cached per
    (code, w, h). Returned RGBA on a transparent backing, so the
    unused part of the slot shows the page underneath. Loaded from
    local disk only — no network at runtime. Pair with
    _flag_outline for the hairline (same fit, same centring)."""
    key = (code, w, h)
    if key not in _flag_cache:
        src = Image.open(FLAG_DIR / (code.lower() + ".png")).convert("RGB")
        nw, nh = _flag_fit(code, w, h)
        flag = src.resize((nw, nh), Image.LANCZOS)
        tile = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        tile.paste(flag, ((w * SS - nw) // 2, (h * SS - nh) // 2))
        _flag_cache[key] = tile
    return _flag_cache[key]


def _load(path, size, axes):
    """Load a variable font at size, then set its axes; fall back to the
    font as loaded if the axes call fails."""
    return SSFont(path, size, axes)


def merr(size, weight=900, width=100):
    """Merriweather; its axes are [weight, width, optical size]. The
    width axis is only narrowed when a headline otherwise needs a
    smaller size: keeping 28px/18px matters more than the default
    width, and the spec's fit rule is about size, not width."""
    key = ("m", size, weight, width)
    if key not in _font_cache:
        path = MERR if MERR.exists() else ARCHIVO
        _font_cache[key] = _load(path, size, [weight, width])
    return _font_cache[key]


def inter(size, weight=400):
    """Inter; its axes are [optical size, weight], so weight is second."""
    key = ("i", size, weight)
    if key not in _font_cache:
        path = INTER if INTER.exists() else ARCHIVO
        _font_cache[key] = _load(path, size, [14, weight])
    return _font_cache[key]


def arch(size, weight=800, width=80):
    """Archivo; its axes are [weight, width]. Used for SOURCE
    credits (2026-11-21, user order): at small sizes a mildly
    condensed Archivo (width 80) reads clearer than Inter — its
    grotesque letterforms stay open and distinct even when bold,
    and being a different face from the Inter headlines it marks
    a credit as a credit at a glance. The condensation is also
    what makes the 3px source-to-divider gap affordable: at 8px
    it runs ~4–6px narrower per label than Inter 800, so the
    tightest briefs still fit whole with the gap (see
    draw_briefs)."""
    key = ("a", size, weight, width)
    if key not in _font_cache:
        path = ARCHIVO if ARCHIVO.exists() else INTER
        _font_cache[key] = _load(path, size, [weight, width])
    return _font_cache[key]


def title_font(size):
    """Merriweather SemiBold for the masthead title. WEIGHT (2026-11-21,
    user order): 600, down from 900 Black — the "Friday 20 November
    2026" line must read visibly lighter than the old heavy black
    while staying bold enough to anchor the page. SIZE: 68px, down
    from 80px (-15%), which shortens the masthead band by ~15px;
    the freed space goes to the briefs (see draw_briefs). At 68px
    the width axis stays at its default 100 (847px) — no narrowing
    needed, well inside the 1000px content area."""
    key = ("t", size)
    if key not in _font_cache:
        _font_cache[key] = SSFont(MERR, size, [600, 100])
    return _font_cache[key]


def wrap(text, font, width):
    """Word-wrap without hyphenation; returns a list of lines."""
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if font.getlength(trial) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_lines(text, font, width, max_lines):
    """Wrap text and, if it overflows max_lines, trim the last line
    with an ellipsis."""
    lines = wrap(text, font, width)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    while lines and font.getlength(lines[-1] + "…") > width:
        lines[-1] = lines[-1][:-1]
    lines[-1] = lines[-1] + "…"
    return lines


def fit_headline(text, sizes, width, max_lines=3):
    """Try (size, width) pairs in order; return the first that fits in
    max_lines, else the smallest size at the narrowest width anyway.
    Size is preferred over width: a headline only narrows after its
    size has been tried at the default width."""
    combos = []
    for size, leading in sizes:
        for w in (100, 92, 87):
            combos.append((size, leading, w))
    for size, leading, w in combos:
        font = merr(size, 900, w)
        lines = wrap(text, font, width)
        if len(lines) <= max_lines:
            return font, lines, leading
    size, leading, w = combos[-1]
    return merr(size, 900, w), wrap(text, merr(size, 900, w), width), leading


def fit_dek(text, width, base=10.5, max_lines=2):
    """Dek at its base size; only a dek that overflows its box steps
    down 0.5px at a time (never below base - 1) so the full spec text
    survives instead of being cut with an ellipsis."""
    size = base
    while size >= base - 1:
        font = inter(size, 400)
        lines = wrap(text, font, width)
        if len(lines) <= max_lines:
            return font, lines
        size -= 0.5
    font = inter(base - 1, 400)
    return font, fit_lines(text, font, width, max_lines)


def badge(draw, x, y, status, height, font_size):
    """Status pill; returns its width."""
    fill, colour = BADGES[status]
    font = inter(font_size, 800)
    width = font.getlength(status) + 12
    draw.rounded_rectangle([x, y, x + width, y + height],
                           radius=height // 2, fill=fill)
    draw.text((x + width / 2, y + height / 2), status, font=font,
              fill=colour, anchor="mm")
    return width


def number_circle(draw, cx, cy, diameter, fill, number, font_size,
                  text_fill=(255, 255, 255)):
    r = diameter / 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    draw.text((cx, cy), str(number), font=inter(font_size, 800),
              fill=text_fill, anchor="mm")


def star(draw, cx, cy, outer, inner, colour, points=8):
    """A simple spiky star (explosion flash)."""
    verts = []
    for i in range(points * 2):
        angle = math.pi * i / points - math.pi / 2
        radius = outer if i % 2 == 0 else inner
        verts.append((cx + radius * math.cos(angle),
                      cy + radius * math.sin(angle)))
    draw.polygon(verts, fill=colour)


def stamp(img, cx, cy, text, font, colour, angle, fill=None):
    """A rotated outline stamp (e.g. GUILTY, TAX) pasted onto img.
    fill: optional solid backing for the tile — used where the stamp
    sits on a busy background that would otherwise swallow the text
    (GUILTY's red on the orange wildfire sky, ~2.4:1)."""
    pad = 12 * SS
    w = int(font.getlength(text) * SS) + pad * 2
    h = 22 * SS
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    if fill is not None:
        td.rectangle([0, 0, w - 1, h - 1], fill=fill + (255,))
    td.rectangle([SS, SS, w - SS - 1, h - SS - 1],
                 outline=colour + (255,), width=2 * SS)
    td.text((w / 2, h / 2), text, font=font, fill=colour + (255,),
            anchor="mm")
    tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.paste(tile, (int(cx * SS - tile.width / 2),
                     int(cy * SS - tile.height / 2)),
              tile)


def dashed_curve(draw, points, colour, width, dash=6, gap=4):
    """Draw a polyline as dashes (used for the missile arcs)."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(length / (dash + gap)))
        for i in range(steps):
            t0 = i / steps
            t1 = (i + dash / (dash + gap)) / steps
            ax, ay = x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0
            bx, by = x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1
            draw.line([ax, ay, bx, by], fill=colour, width=width)


def quad(p0, p1, p2, n=24):
    """Points along a quadratic Bezier curve."""
    out = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        out.append((x, y))
    return out


# ---------------------------------------------------------------- masthead

def draw_masthead(draw):
    # MASTHEAD (2026-11-21, reference-layout rebuild): the title is
    # 64px SemiBold (was 68px) and the REGION KEY IS GONE — dropped
    # entirely (user order: it had no good home; the reference works
    # without a separate key — the region colours live in the
    # kickers, the map dots and the briefs group headers). The
    # kicker line is back to just the two texts: "THE DAY IN WORLD
    # NEWS" left, "40 STORIES · 8 REGIONS · ALL FROM THIS FRIDAY"
    # right. Title at y=8, 64px: its caps start ~y=18 (the kicker's
    # ink ends ~y=17, so ~1px clear — the same tightness the 68px
    # title had at y=7). The 'y' descender now ends ~y=87 (was
    # 91): the masthead band shrinks ~4px, given to the timeline
    # and leads below.
    draw.text((12, 6), "THE DAY IN WORLD NEWS", font=inter(12, 800),
              fill=RED, anchor="la")
    draw.text((1012, 6), "40 STORIES · 8 REGIONS · ALL FROM THIS FRIDAY",
              font=inter(10.5, 700), fill=DEK, anchor="ra")
    size = 64
    while size >= 64:
        font = title_font(size)
        if font.getlength("Friday 20 November 2026") <= 1000:
            break
        size -= 2
    draw.text((12, 8), "Friday 20 November 2026",
              font=title_font(size), fill=(20, 20, 20), anchor="la")


def draw_timeline(draw):
    # TIMELINE, COMPACT (2026-11-21, reference-layout rebuild): one
    # tight band, ~50px (was 62px) — the reference's timeline is a
    # single compact line, and ours was the tallest element after
    # the masthead. Event type is 10.5px (was 12px), dots 12px
    # diameter (was 14px), hour labels 9px (was 10px), and the
    # "THE DAY / IN UTC" label 11px (was 12px). Same 5 events, same
    # times/labels/anchors/regions, same stem-and-rule connectors
    # (colour-coded by region), same 25 hourly ticks (numbers only
    # on 00/06/12/18/24). Geometry (band caps ~91 .. descenders
    # ~144, leads start at y=147):
    #   above-event labels, baseline 99 (caps ~91, ~4px clear of
    #     the title descender at ~87); connector rule y=103..105;
    #     stem y=105..108
    #   ruler line y=112..115 (3px), dots centred on y=113.5,
    #     12px diameter (6px white halo / 5px colour centre)
    #   hour ticks below the line, hour labels (every 6h, 9px)
    #     baseline 128
    #   below-event labels, baseline 141 (descenders to ~144, 4px
    #     clear of the lead row at 148); stem y=120..130
    draw.text((12, 110), "THE DAY", font=inter(11, 800), fill=RED,
              anchor="ls")
    draw.text((12, 122), "IN UTC", font=inter(11, 800), fill=RED,
              anchor="ls")
    draw.rectangle([88, 112, 1012, 115], fill=INK)
    hour_font = inter(9, 700)
    for hour in range(25):
        x = 88 + hour * 38.5
        if hour % 6 == 0:
            # Axis NUMBER labels only on 00/06/12/18/24 (2026-11-21):
            # the 03/09/15/21 labels collided with event labels.
            # Tick marks stay hourly (long tick every 3h, short else).
            draw.rectangle([x - 1, 116, x + 1, 121], fill=INK)
            label = "%02d:00" % hour
            cx = min(max(x, 88 + hour_font.getlength(label) / 2),
                     1012 - hour_font.getlength(label) / 2)
            draw.text((cx, 128), label, font=hour_font, fill=DEK,
                      anchor="ms")
        else:
            draw.rectangle([x, 116, x, 119], fill=MUTED)
    time_font = inter(10.5, 800)
    label_font = inter(10.5, 700)
    space = label_font.getlength(" ")
    for time, x, label, above, anchor, region in S.TIMELINE:
        colour = S.REGION_COLOURS[region]
        draw.ellipse([x - 6, 107.5, x + 6, 119.5],
                     fill=(255, 255, 255))
        draw.ellipse([x - 5, 108.5, x + 5, 118.5], fill=colour)
        total = (time_font.getlength(time) + space
                 + label_font.getlength(label))
        if anchor == "left":
            lx = x + 6
        elif anchor == "right":
            lx = x - 6 - total
        else:
            lx = x - total / 2
        if above:
            # Connector rule under the label, joined to the dot by the
            # stem: for displaced labels the rule runs from the dot's
            # x to the label's far end; for centred labels it spans
            # the label and the stem meets it at its midpoint.
            if anchor == "left":
                rx0, rx1 = x, lx + total
            elif anchor == "right":
                rx0, rx1 = lx, x
            else:
                rx0, rx1 = lx, lx + total
            draw.rectangle([rx0, 103, rx1, 105], fill=colour)
            draw.rectangle([x - 1, 105, x, 108], fill=colour)
            base = 99
        else:
            # Stem drops from the dot to 1px above the label caps.
            draw.rectangle([x - 1, 120, x, 130], fill=colour)
            base = 141
        draw.text((lx, base), time, font=time_font, fill=colour,
                  anchor="ls")
        draw.text((lx + time_font.getlength(time) + space, base), label,
                  font=label_font, fill=INK, anchor="ls")


# ------------------------------------------------------- lead illustrations
# ILLUSTRATION ROUND (2026-11-21): every lead redrawn around ONE
# big focal idea that reads at a glance — bigger map / bigger
# bursts / a second plunging market line / the struck draft as
# the hero — flat graphic shapes in the paper palette only.

def lead_art_akvan(draw, x, y0):
    """Cyclone Akvan as a LEAD (2026-11-21, lead reorder): the old
    card art scaled up to the 244x72 lead band — a BIG saturated-blue
    spiral over a pale sky, green/tan coastline along the bottom,
    diagonal rain top-right, ODISHA label on the land. First glance:
    a cyclone hitting the coast — blue spiral on pale sky, never
    white-on-navy."""
    draw.rectangle([x, y0, x + 244, y0 + 72], fill=(205, 225, 240))
    # --- Dominant focal: the spiral, centre-left ---
    # Outer ring 52px tall (r=26, ~72% of the 72px band), centred
    # at (x+85, y0+32) so it spans y0+6..y0+58 and touches the
    # coastline below. Each ring is an arc with a staggered gap,
    # so the gaps step round the swirl like a rotating storm.
    cx, cy = x + 85, y0 + 32
    draw.arc([cx - 26, cy - 26, cx + 26, cy + 26], 15, 285,
             fill=(25, 90, 165), width=4)
    draw.arc([cx - 20, cy - 20, cx + 20, cy + 20], 105, 15,
             fill=(45, 130, 200), width=4)
    draw.arc([cx - 14, cy - 14, cx + 14, cy + 14], 195, 105,
             fill=(25, 90, 165), width=3)
    draw.arc([cx - 8, cy - 8, cx + 8, cy + 8], 285, 195,
             fill=(45, 130, 200), width=3)
    # Calm eye at the centre.
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3],
                 fill=(15, 60, 120))
    # --- Supporting cue 1: coastline along the bottom ---
    # Tan sand edge on top of a green land strip; the wavy top
    # edge is the shore the cyclone is crossing.
    draw.polygon([(x, y0 + 72), (x, y0 + 60), (x + 60, y0 + 56),
                  (x + 120, y0 + 60), (x + 180, y0 + 56),
                  (x + 244, y0 + 60), (x + 244, y0 + 72)],
                 fill=(46, 125, 60))
    draw.line([(x, y0 + 60), (x + 60, y0 + 56), (x + 120, y0 + 60),
               (x + 180, y0 + 56), (x + 244, y0 + 60)],
              fill=(194, 178, 128), width=3)
    # --- Supporting cue 2: diagonal rain streaks, top-right ---
    for rx, ry in [(170, 8), (185, 5), (200, 9), (215, 6),
                   (230, 8), (178, 20), (193, 17), (208, 21),
                   (223, 18)]:
        draw.line([x + rx, y0 + ry, x + rx - 7, y0 + ry + 12],
                  fill=(60, 120, 190), width=2)
    # Label on the land strip.
    draw.text((x + 200, y0 + 68), "ODISHA", font=inter(10, 800),
              fill=(255, 255, 255), anchor="ls")

def lead_art_2(draw, x, y0):
    """Kyiv bridge attack — REBUILT BRIGHT: a pale dawn sky over a
    pale river, one huge bold suspension bridge in dark slate
    spanning the whole band, its deck BROKEN at the impact point
    by a giant layered orange fireball, with a second smaller
    burst on the left deck and three bright missile trails
    falling into the bursts. First glance: a bridge burning
    under attack — dark bridge on light sky, never dark-on-dark."""
    # Pale dawn sky and pale river.
    draw.rectangle([x, y0, x + 244, y0 + 72], fill=(205, 222, 238))
    draw.rectangle([x, y0 + 50, x + 244, y0 + 72], fill=(170, 200, 225))
    # Bridge: two tall towers with pointed caps, dark slate.
    for tx in (48, 188):
        draw.rectangle([x + tx, y0 + 14, x + tx + 8, y0 + 47],
                       fill=(35, 40, 60))
        draw.polygon([(x + tx, y0 + 16), (x + tx + 8, y0 + 16),
                      (x + tx + 4, y0 + 7)], fill=(35, 40, 60))
    # Fan cables from each tower top down to the deck.
    for (cx, cy, px) in [(52, 14, 14), (52, 14, 32), (52, 14, 74),
                         (52, 14, 98), (192, 14, 170), (192, 14, 210),
                         (192, 14, 230)]:
        draw.line([x + cx, y0 + cy, x + px, y0 + 40],
                  fill=(60, 70, 110), width=2)
    # Deck, BROKEN at the impact point (gap x+116..x+152).
    draw.rectangle([x + 4, y0 + 40, x + 116, y0 + 47], fill=(35, 40, 60))
    draw.rectangle([x + 152, y0 + 40, x + 240, y0 + 47],
                   fill=(35, 40, 60))
    # Missile trails falling into the bursts (bright core over
    # an orange outer line), drawn before the bursts so the
    # fireballs cover their ends.
    for (x1, y1, x2, y2) in [(196, 2, 152, 23), (222, 4, 168, 27),
                             (64, 2, 74, 29)]:
        draw.line([x + x1, y0 + y1, x + x2, y0 + y2],
                  fill=(255, 150, 40), width=3)
        draw.line([x + x1, y0 + y1, x + x2, y0 + y2],
                  fill=(255, 230, 150), width=1)
    # Small burst on the left deck.
    star(draw, x + 76, y0 + 36, 11, 3, (255, 150, 40))
    star(draw, x + 76, y0 + 36, 6, 2, (255, 210, 80))
    # GIANT fireball at the broken deck: round glow, spiky
    # layered stars, radiating ticks.
    draw.ellipse([x + 106, y0 + 11, x + 162, y0 + 61],
                 fill=(255, 120, 40))
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        draw.line([x + 134 + 32 * math.cos(a), y0 + 36 + 32 * math.sin(a),
                   x + 134 + 38 * math.cos(a), y0 + 36 + 38 * math.sin(a)],
                  fill=(255, 150, 40), width=2)
    star(draw, x + 134, y0 + 36, 28, 8, (255, 160, 50), points=12)
    star(draw, x + 134, y0 + 36, 19, 6, (255, 200, 60), points=12)
    star(draw, x + 134, y0 + 36, 10, 3, (255, 240, 160), points=12)
    # Two small smoke puffs drifting right of the fireball.
    for sx, sy, sr in [(160, 14, 6), (170, 9, 4)]:
        draw.ellipse([x + sx - sr, y0 + sy - sr, x + sx + sr,
                      y0 + sy + sr], fill=(100, 105, 120))
    # Orange reflections in the river under the fireball.
    for rx, y2 in [(126, 63), (134, 67), (142, 61)]:
        draw.line([x + rx, y0 + 52, x + rx, y0 + y2],
                  fill=(255, 150, 40), width=3)
    draw.text((x + 8, y0 + 62), "KYIV 00:30", font=inter(10, 800),
              fill=INK, anchor="la")
def lead_art_4(draw, x, y0):
    """COP31 overtime / fossil fuels dropped — REBUILD: one BIG globe
    as the single focal (70px of the 80px band height), a LARGE
    red-rimmed clock at right with its hands past midnight
    (overtime) and a bold red OVERTIME label under it, and a black
    oil drop between them crossed by a THICK red X (fossil fuels
    dropped). Three bold flat shapes only — no document, no
    thermometer, no small text."""
    draw.rectangle([x, y0, x + 244, y0 + 72], fill=(242, 236, 220))
    # FOCAL: big globe, left — thick dark outline, bold continents.
    draw.ellipse([x + 17, y0 + 4, x + 87, y0 + 68], fill=(56, 128, 180),
                 outline=INK, width=3)
    draw.ellipse([x + 28, y0 + 13, x + 50, y0 + 31], fill=(84, 168, 92))
    draw.ellipse([x + 44, y0 + 27, x + 62, y0 + 45], fill=(84, 168, 92))
    draw.ellipse([x + 58, y0 + 47, x + 78, y0 + 61], fill=(84, 168, 92))
    draw.ellipse([x + 60, y0 + 13, x + 74, y0 + 23], fill=(84, 168, 92))
    # Shine on the globe.
    draw.ellipse([x + 26, y0 + 11, x + 36, y0 + 18],
                 fill=(150, 205, 235))
    # SUPPORTING 1: dropped fossil fuel — black oil drop, thick red X.
    draw.polygon([(x + 118, y0 + 32), (x + 132, y0 + 50),
                  (x + 104, y0 + 50)], fill=INK)
    draw.ellipse([x + 104, y0 + 47, x + 132, y0 + 68], fill=INK)
    draw.ellipse([x + 110, y0 + 52, x + 116, y0 + 59],
                 fill=(255, 255, 255))
    draw.line([x + 100, y0 + 31, x + 136, y0 + 70], fill=RED, width=4)
    draw.line([x + 136, y0 + 31, x + 100, y0 + 70], fill=RED, width=4)
    # SUPPORTING 2: overtime clock — big, red rim, hands past 12.
    draw.ellipse([x + 166, y0 + 5, x + 226, y0 + 59],
                 fill=(255, 255, 255), outline=RED, width=3)
    # Tick marks (longer at 12/3/6/9).
    for i in range(12):
        a = math.radians(i * 30 - 90)
        r1 = 22 if i % 3 == 0 else 24
        draw.line([x + 196 + r1 * math.cos(a), y0 + 32 + r1 * math.sin(a),
                   x + 196 + 27 * math.cos(a), y0 + 32 + 27 * math.sin(a)],
                  fill=INK, width=2)
    # Hour hand just past 12, minute hand (red) at ~1: past midnight.
    draw.line([x + 196, y0 + 32, x + 199, y0 + 16], fill=INK, width=3)
    draw.line([x + 196, y0 + 32, x + 212, y0 + 18], fill=RED, width=2)
    draw.ellipse([x + 193, y0 + 30, x + 199, y0 + 35], fill=RED)
    draw.text((x + 196, y0 + 63), "OVERTIME", font=inter(9, 800),
              fill=RED, anchor="ma")

# LEAD ART (2026-11-21, lead reorder): keyed by the NEW lead ids —
# 1 Kyiv (lead_art_2, the bridge), 2 Akvan (lead_art_akvan, the
# cyclone), 4 COP31 (lead_art_4, the globe/clock). Lead 3 (S&P) is
# drawn inline in draw_lead. The old lead_art_1 (Poland map) is
# gone — Poland is now card 14, drawn by card_art_poland.
LEAD_ART = {1: lead_art_2, 2: lead_art_akvan, 4: lead_art_4}


def draw_lead(draw, img, lead, x, y0):
    """One lead card; lead 3 is the market-fall anchor — BRIGHT
    (rebuild: pale green band, dark-red "-3.7%", bright red
    falling chart; the old navy band is gone).
    LAYOUT (2026-11-21, reference rebuild): the card is 233px
    tall (was 240) — the art band is 72px (was 80) and the whole
    text block shifts up 8px with its internal spacing unchanged
    (kicker, 3-line headline at 28px/31 leading, 2-line dek,
    badge + source)."""
    w = 244
    region = S.REGION_COLOURS[lead["region"]]
    if lead["id"] == 3:
        # DESIGN (bright rebuild 2026-11-21): the top illustration
        # band (y0..y0+72) is a PALE green tint, not navy — the
        # rest of the card is the standard white panel, so the
        # headline, dek, badge and source sit on white like the
        # other leads. The band ALSO carries the same thin
        # region-coloured top rule as the other leads (N. America
        # green, 3px at the very top).
        # ART: TWO focal elements only, side by side, filling the
        # full band width — the huge dark-red "-3.7%" on the left,
        # and a steep falling bright-red chart with a big arrowhead
        # on the right. The fall reads at a glance, with or without
        # the headline. Measured: "-3.7%" at merr 44 is 129px wide
        # (x+10..x+139), so the chart zone starts at x+148 with a
        # clear gap. (Band 72px, 2026-11-21: all y-offsets scaled
        # x0.9 from the 80px band; sizes unchanged.)
        draw.rectangle([x, y0, x + w, y0 + 233], fill=PANEL,
                       outline=PANEL_BORDER)
        draw.rectangle([x, y0, x + w, y0 + 72], fill=(232, 238, 228))
        draw.rectangle([x, y0, x + w, y0 + 3], fill=region)
        draw.text((x + 10, y0 + 44), "-3.7%", font=merr(44, 900),
                  fill=RED, anchor="ls")
        draw.text((x + 10, y0 + 64), "S&P 500 · 6,910",
                  font=inter(13, 700), fill=INK, anchor="ls")
        # CHART (rebuilt 2026-11-21, user order): the filled area
        # under the falling line made the chart read as a big red
        # TRIANGLE — the area fill is deleted. Now it is a clean
        # line chart only: two faint gridlines, a thick steep red
        # falling line, one red dot marking the high at the start,
        # and a large arrowhead at the end. No filled polygon.
        for gy in (28, 47):
            draw.line([(x + 144, y0 + gy), (x + 240, y0 + gy)],
                      fill=(150, 160, 150), width=1)
        sp = [(x + 148, y0 + 11), (x + 174, y0 + 25),
              (x + 200, y0 + 41), (x + 226, y0 + 58)]
        draw.line(sp, fill=ANCHOR_RED, width=5, joint="curve")
        draw.ellipse([x + 144, y0 + 7, x + 152, y0 + 15],
                     fill=RED)
        draw.polygon([(x + 235, y0 + 63), (x + 222, y0 + 63),
                      (x + 230, y0 + 52)], fill=ANCHOR_RED)
        kick_fill, kick_num = region, (255, 255, 255)
        kick_colour, head_colour, dek_colour = region, INK, DEK
        src_colour = SOURCE
    else:
        draw.rectangle([x, y0, x + w, y0 + 233], fill=PANEL,
                       outline=PANEL_BORDER)
        LEAD_ART[lead["id"]](draw, x, y0)
        draw.rectangle([x, y0, x + w, y0 + 3], fill=region)
        kick_fill, kick_num = region, (255, 255, 255)
        kick_colour, head_colour, dek_colour = region, INK, DEK
        src_colour = SOURCE
    cy = y0 + 82
    number_circle(draw, x + 8 + 6.5, cy, 13, kick_fill, lead["id"], 9,
                  text_fill=kick_num)
    draw.text((x + 26, y0 + 89), lead["kicker"], font=inter(10.5, 800),
              fill=kick_colour, anchor="ls")
    font, lines, leading = fit_headline(
        lead["headline"], [(28, 31), (26, 29), (24, 27)], 228)
    ty = y0 + 93
    for line in lines:
        draw.text((x + 8, ty), line, font=font, fill=head_colour, anchor="la")
        ty += leading
    dek_font, dek_lines = fit_dek(lead["dek"], 228, base=11)
    ty = y0 + 189
    for line in dek_lines:
        draw.text((x + 8, ty), line, font=dek_font, fill=dek_colour,
                  anchor="la")
        ty += dek_font.size + 2.5
    badge(draw, x + 8, y0 + 219, lead["status"], 12, 9)
    # SOURCE 11px (was 9.5px, 2026-11-21 user order: bigger so it
    # reads clearly). Widest lead source ("Kyiv Independent · BBC",
    # 117px) clears the badge (ends ~x+75) by ~44px.
    draw.text((x + w - 8, y0 + 230), lead["source"].upper(),
              font=arch(11, 700, 80), fill=src_colour, anchor="rs")


# ------------------------------------------------------ medium illustrations
# ILLUSTRATION ROUND (2026-11-21): every card redrawn around ONE
# big focal idea that reads at a glance — a hero number, a hero
# stamp, a giant spike, a broken line — flat graphic shapes in
# the paper palette only. Card 11's in-art label changes
# "1 IN 12" -> "61 PATIENTS": the trial size straight from the
# dek; "1 IN 12" appears in no source for this story.

def card_art_5(draw, x, y0):
    """UK-EU — BEFORE: 32x20 flags, a 4px teal link, a modest red
    "3" seal (r=13) and a small "DEALS" label. AFTER: BIGGER flags
    (40x20, filling the full band height), a THICKER 6px teal
    bridge joining them, and a LARGER red "3" seal (r=14, 20px
    "3") sitting on the bridge like a wax seal, with a bold
    "3 DEALS" caption underneath — inside the band, in the free
    strip below the seal. First glance: UK + EU + 3 deals."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(214, 226, 240))
    # UK flag, left — real flag, 40x20, top of the band.
    draw.paste(_flag_image("GB", 40, 20), (x + 3, y0 + 5))
    _flag_outline(draw, x + 3, y0 + 5, "GB", 40, 20)
    # EU flag, right — drawn by hand (no eu.png in assets):
    # blue field with a circle of 12 gold stars.
    draw.rectangle([x + 117, y0 + 5, x + 157, y0 + 23],
                   fill=(0, 51, 153))
    for i in range(12):
        a = 2 * math.pi * i / 12
        sx = x + 137 + 12 * math.cos(a)
        sy = y0 + 14 + 7 * math.sin(a)
        draw.ellipse([sx - 1.2, sy - 1.2, sx + 1.2, sy + 1.2],
                     fill=(255, 204, 0))
    draw.rectangle([x + 117, y0 + 5, x + 157, y0 + 23],
                   outline=(180, 175, 165))
    # THICK teal bridge joining the two flags, mid-flag height.
    draw.rectangle([x + 43, y0 + 11, x + 117, y0 + 16],
                   fill=(14, 124, 123))
    # LARGE red "3" seal overlapping the bridge, centre of the band.
    draw.ellipse([x + 66, y0 + 1, x + 94, y0 + 26], fill=RED,
                 outline=(255, 255, 255), width=2)
    draw.text((x + 80, y0 + 14), "3", font=inter(20, 800),
              fill=(255, 255, 255), anchor="mm")
    # Bold caption in the free strip below the seal (seal ends
    # y0 + 26): top at y0 + 31, ~9px tall, so it ends ~y0 + 39, fully
    # inside the band (ends y0 + 42).
    draw.text((x + 80, y0 + 31), "3 DEALS", font=inter(9, 800),
              fill=INK, anchor="ma")

def card_art_6(draw, x, y0):
    """UN chief race — stalled after the ninth vote. A BIG white
    ballot box (focal, ~60% of the band) on a PALE UN-blue field,
    a huge navy "9" on its front, a ballot slip sticking out of
    the slot — and a LARGE red veto circle with a bold white X
    and a small VETO label at right. First glance: ninth vote,
    vetoed / blocked. Bright: pale sky-blue field, never the
    old saturated UN blue."""
    UN_BLUE = (0, 91, 172)
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(200, 222, 240))
    # Ballot slip sticking out of the slot.
    draw.rectangle([x + 46, y0 + 1, x + 58, y0 + 11],
                   fill=(255, 255, 255), outline=NAVY)
    # Ballot-box lid (two segments, gap in the middle = the slot).
    draw.rectangle([x + 2, y0 + 7, x + 44, y0 + 13], fill=NAVY)
    draw.rectangle([x + 60, y0 + 7, x + 98, y0 + 13], fill=NAVY)
    # Ballot-box body.
    draw.rectangle([x + 6, y0 + 13, x + 94, y0 + 40],
                   fill=(255, 255, 255), outline=NAVY, width=2)
    # Huge "9" — the ninth vote — on the box front.
    draw.text((x + 50, y0 + 28), "9", font=inter(24, 800), fill=NAVY,
              anchor="mm")
    # Veto: big red circle with a bold white X.
    draw.ellipse([x + 108, y0 + 4, x + 146, y0 + 38], fill=RED,
                 outline=(255, 255, 255), width=2)
    draw.line([x + 118, y0 + 10, x + 136, y0 + 26],
              fill=(255, 255, 255), width=4)
    draw.line([x + 136, y0 + 10, x + 118, y0 + 26],
              fill=(255, 255, 255), width=4)
    draw.text((x + 127, y0 + 33), "VETO", font=inter(6, 800),
              fill=(255, 255, 255), anchor="mm")

def card_art_7(draw, x, y0):
    """Iran war, ninth month, no decision until 2027 — AFTER: one
    GIANT clock fills the left half of the band (r=21, face 42px
    tall in a 46px band), its hands set to 9 o'clock, with a HUGE
    navy "9" (20px) at the centre of the face — month nine, time
    dragging on. Right side: a bold red "UNTIL 2027" chip, and
    beneath it a red pause glyph + "NO RUSH" — the decision is
    on hold. First glance: a clock stuck on 9, nothing decided
    until 2027."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(233, 229, 218))
    # --- Giant clock (dominant focal, left half) ---
    cx, cy, r = x + 34, y0 + 21, 21
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255),
                 outline=INK, width=3)
    # Tick marks at 12 / 3 / 6 / 9.
    draw.line([cx, cy - r + 3, cx, cy - r + 7], fill=INK, width=2)
    draw.line([cx + r - 3, cy, cx + r - 7, cy], fill=INK, width=2)
    draw.line([cx, cy + r - 3, cx, cy + r - 7], fill=INK, width=2)
    draw.line([cx - r + 3, cy, cx - r + 7, cy], fill=INK, width=2)
    # Hands: hour hand to 9 o'clock (left), minute hand to 12 (up).
    # Drawn BEFORE the "9" so the digit sits on top of their bases.
    draw.line([cx, cy, cx - r + 5, cy], fill=INK, width=3)
    draw.line([cx, cy, cx, cy - r + 5], fill=INK, width=3)
    draw.text((cx, cy + 1), "9", font=inter(20, 800), fill=NAVY2,
              anchor="mm")
    # --- "UNTIL 2027" chip (top right) ---
    draw.rectangle([x + 62, y0 + 6, x + 156, y0 + 23], fill=RED)
    draw.text((x + 109, y0 + 15), "UNTIL 2027", font=inter(11, 800),
              fill=(255, 255, 255), anchor="mm")
    # --- Pause glyph + "NO RUSH" (bottom right, the wait) ---
    draw.rectangle([x + 70, y0 + 29, x + 75, y0 + 38], fill=RED)
    draw.rectangle([x + 78, y0 + 29, x + 83, y0 + 38], fill=RED)
    draw.text((x + 88, y0 + 34), "NO RUSH", font=inter(9, 800),
              fill=INK, anchor="lm")

def card_art_8(draw, x, y0):
    """Hodeidah port strike — REBUILT BRIGHT: a pale warm sky over
    a pale blue sea, a BIG cargo ship in deep navy filling the
    whole band (hull x+6..x+154, containers flanking a central
    explosion), ONE huge layered burst (r=16) erupting from the
    middle of the ship, one crane silhouette at each end for the
    port, and a small drone silhouette top-right struck through
    with a red x (intercepted). First glance: a ship exploding
    at a port — dark hull on light sea, never dark-on-dark."""
    # Pale warm sky over a pale blue sea.
    draw.rectangle([x, y0, x + 160, y0 + 27], fill=(250, 225, 190))
    draw.rectangle([x, y0 + 27, x + 160, y0 + 42], fill=(185, 210, 230))
    # Two crane silhouettes, one at each end of the port.
    for cx, jib in [(12, (6, 36)), (148, (138, 156))]:
        draw.line([x + cx, y0 + 7, x + cx, y0 + 27], fill=(45, 38, 32),
                  width=3)
        draw.line([x + jib[0], y0 + 9, x + jib[1], y0 + 9],
                  fill=(45, 38, 32), width=2)
        draw.line([x + cx, y0 + 7, x + jib[1], y0 + 9],
                  fill=(45, 38, 32), width=1)
    # The cargo ship: wide deep-navy hull with a red waterline.
    draw.polygon([(x + 6, y0 + 27), (x + 154, y0 + 27), (x + 148, y0 + 38),
                  (x + 12, y0 + 38)], fill=(20, 35, 75))
    draw.rectangle([x + 10, y0 + 35, x + 150, y0 + 37], fill=RED)
    # Container stacks flanking the explosion, two high each.
    draw.rectangle([x + 18, y0 + 22, x + 52, y0 + 27], fill=(200, 60, 40))
    draw.rectangle([x + 22, y0 + 16, x + 48, y0 + 22], fill=(40, 120, 130))
    draw.rectangle([x + 108, y0 + 22, x + 142, y0 + 27],
                   fill=(220, 150, 40))
    draw.rectangle([x + 112, y0 + 16, x + 138, y0 + 22],
                   fill=(50, 90, 150))
    # ONE huge explosion burst erupting from the middle of the ship.
    star(draw, x + 80, y0 + 15, 16, 5, (255, 150, 40))
    star(draw, x + 80, y0 + 15, 11, 4, (255, 200, 60))
    star(draw, x + 80, y0 + 15, 6, 2, RED)
    # One intercepted drone, top-right, struck through with a red x.
    draw.line([x + 128, y0 + 5, x + 144, y0 + 5], fill=(20, 20, 25),
              width=1)
    draw.rectangle([x + 131, y0 + 5, x + 141, y0 + 8], fill=(20, 20, 25))
    draw.line([x + 129, y0 + 3, x + 143, y0 + 10], fill=RED, width=2)
    draw.line([x + 143, y0 + 3, x + 129, y0 + 10], fill=RED, width=2)
def card_art_9(draw, x, y0):
    """Peru quake — HUGE bold red "6.7" (36px, ~78% of the band
    height) as the dominant focal on the left: the magnitude IS the
    story. One thick red seismograph trace on the right with a HUGE
    central spike nearly touching the top of the band, and two
    simple Andes triangles along the bottom-right. A dark
    "FRI 19:09 LOCAL" chip top-right (user order, 2026-11-21):
    the quake's Friday local time, so no Saturday appears anywhere
    on the card — the old "SAT 00:09 UTC" chip is gone and the
    Date Check EDGE line naming Sat 21 Nov is deleted too.
    First glance: a 6.7 earthquake."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(240, 236, 224))
    # Andes: two simple triangles along the bottom-right, behind
    # the trace, low so they never fight the "6.7".
    draw.polygon([(x + 70, y0 + 42), (x + 100, y0 + 31),
                  (x + 130, y0 + 42)], fill=(150, 110, 70))
    draw.polygon([(x + 114, y0 + 42), (x + 138, y0 + 33),
                  (x + 160, y0 + 42)], fill=(120, 85, 55))
    # Seismograph trace: thick red, one huge central spike that
    # nearly touches the top of the band. Starts right of the
    # "6.7" so it never crosses the number.
    pts = [(x + 70, y0 + 24), (x + 82, y0 + 20),
           (x + 90, y0 + 4), (x + 98, y0 + 27),
           (x + 108, y0 + 16), (x + 118, y0 + 24),
           (x + 130, y0 + 20), (x + 152, y0 + 20)]
    draw.line(pts, fill=RED, width=4, joint="curve")
    # The magnitude, huge and bold, filling most of the band.
    draw.text((x + 4, y0 + 3), "6.7", font=merr(36, 900), fill=RED,
              anchor="la")
    # FRI chip (user order, 2026-11-21): dark chip top-right with
    # the quake's Friday local time in white. Placed x+96..x+158,
    # y0 + 3..y0 + 13 — right of the trace spike (x+90) and above the
    # trace's right run (top y0 + 16 at x+108), so it never covers
    # the spike, the trace, or the "6.7".
    draw.rectangle([x + 96, y0 + 3, x + 158, y0 + 13], fill=INK)
    draw.text((x + 127, y0 + 7.5), "FRI 19:09 LOCAL",
              font=inter(7, 800), fill=(255, 255, 255), anchor="mm")

def card_art_10(img, draw, x, y0):
    """Palisades Fire — REBUILT BRIGHT: a pale warm smoke sky, a
    WALL of tall layered flames in deep red-orange / orange /
    gold filling the whole band, and one LARGE white-backed
    GUILTY stamp (15px) front and centre. First glance: a
    wildfire, and a guilty verdict — saturated flames on light
    sky, never dark-on-dark."""
    # Pale warm smoke sky: maximum contrast for the flames and
    # the white stamp.
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(245, 235, 220))
    # Three big overlapping flame tongues (outer deep red-orange,
    # mid orange, inner gold core). Tips reach y0 + 2..y0 + 6 so fire
    # peaks above the stamp; bases fill the bottom of the band.
    # Left flame.
    draw.polygon([(x + 15, y0 + 42), (x + 14, y0 + 29), (x + 20, y0 + 18),
                  (x + 27, y0 + 9), (x + 32, y0 + 5), (x + 38, y0 + 13),
                  (x + 44, y0 + 22), (x + 52, y0 + 31), (x + 51, y0 + 42)],
                 fill=(210, 60, 15))
    draw.polygon([(x + 21, y0 + 42), (x + 20, y0 + 31), (x + 25, y0 + 22),
                  (x + 29, y0 + 15), (x + 32, y0 + 11), (x + 36, y0 + 18),
                  (x + 41, y0 + 27), (x + 43, y0 + 42)],
                 fill=(245, 130, 20))
    draw.polygon([(x + 26, y0 + 42), (x + 27, y0 + 33), (x + 30, y0 + 26),
                  (x + 32, y0 + 22), (x + 35, y0 + 27), (x + 37, y0 + 35),
                  (x + 37, y0 + 42)], fill=(255, 190, 40))
    # Centre flame — the tallest, tip at y0 + 2.
    draw.polygon([(x + 58, y0 + 42), (x + 57, y0 + 27), (x + 67, y0 + 16),
                  (x + 74, y0 + 7), (x + 80, y0 + 2), (x + 87, y0 + 11),
                  (x + 93, y0 + 22), (x + 99, y0 + 31), (x + 99, y0 + 42)],
                 fill=(210, 60, 15))
    draw.polygon([(x + 68, y0 + 42), (x + 68, y0 + 29), (x + 73, y0 + 20),
                  (x + 77, y0 + 13), (x + 80, y0 + 9), (x + 84, y0 + 16),
                  (x + 89, y0 + 26), (x + 91, y0 + 42)],
                 fill=(245, 130, 20))
    draw.polygon([(x + 74, y0 + 42), (x + 74, y0 + 33), (x + 77, y0 + 25),
                  (x + 80, y0 + 20), (x + 83, y0 + 26), (x + 85, y0 + 35),
                  (x + 85, y0 + 42)], fill=(255, 190, 40))
    # Right flame.
    draw.polygon([(x + 108, y0 + 42), (x + 107, y0 + 29), (x + 117, y0 + 19),
                  (x + 123, y0 + 10), (x + 128, y0 + 6), (x + 134, y0 + 14),
                  (x + 140, y0 + 23), (x + 145, y0 + 31), (x + 144, y0 + 42)],
                 fill=(210, 60, 15))
    draw.polygon([(x + 118, y0 + 42), (x + 118, y0 + 31), (x + 122, y0 + 23),
                  (x + 126, y0 + 16), (x + 128, y0 + 13), (x + 132, y0 + 19),
                  (x + 137, y0 + 28), (x + 139, y0 + 42)],
                 fill=(245, 130, 20))
    draw.polygon([(x + 122, y0 + 42), (x + 123, y0 + 34), (x + 126, y0 + 26),
                  (x + 128, y0 + 23), (x + 131, y0 + 28), (x + 133, y0 + 36),
                  (x + 133, y0 + 42)], fill=(255, 190, 40))
    # The verdict: one LARGE white-backed GUILTY stamp, front and
    # centre, over the flames.
    stamp(img, x + 80, y0 + 21, "GUILTY", inter(15, 800), RED, -8,
          fill=(255, 255, 255))
def card_art_11(img, draw, x, y0):
    """Pill vs pancreatic cancer — REBUILT (2026-11-21, user order):
    a CHUNKIER capsule (120x30, taller than before) with real
    pill depth: a soft drop shadow under it, a glossy white
    highlight streak across the top, and a subtle darker shade
    along the bottom — so it reads as a solid 3D pill, not a
    flat bar. Teal left half / white right half, thick dark-teal
    outline, centre seam, and the vivid-green check badge at the
    right as the "it works" cue. No text, no tumours, no rotation
    — the pill alone is the story, instantly readable at a glance.
    First glance: a pill that works."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(238, 244, 240))
    # Soft drop shadow, drawn first so the capsule sits on it:
    # a pale-grey rounded rect offset 2px down-right.
    draw.rounded_rectangle([x + 6, y0 + 12, x + 126, y0 + 37],
                           radius=15, fill=(210, 218, 210))
    # Chunkier horizontal capsule, built as a tile so the two halves
    # keep perfect rounded ends and a straight centre seam.
    cap = Image.new("RGBA", (120 * SS, 30 * SS), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cap)
    # Left half: teal (rectangle + end cap).
    cd.rectangle([15 * SS, 0, 60 * SS, 30 * SS], fill=(14, 124, 123))
    cd.ellipse([0, 0, 30 * SS, 30 * SS], fill=(14, 124, 123))
    # Right half: white (rectangle + end cap).
    cd.rectangle([60 * SS, 0, 105 * SS, 30 * SS], fill=(255, 255, 255))
    cd.ellipse([90 * SS, 0, 120 * SS, 30 * SS], fill=(255, 255, 255))
    # Glossy highlight streak across the top (inside the capsule),
    # semi-transparent white — the 3D sheen.
    cd.rounded_rectangle([10 * SS, 4 * SS, 110 * SS, 11 * SS],
                         radius=3 * SS, fill=(255, 255, 255, 110))
    # Subtle darker shade along the bottom, for depth.
    cd.rounded_rectangle([10 * SS, 24 * SS, 110 * SS, 28 * SS],
                         radius=2 * SS, fill=(10, 90, 90, 45))
    # Thick outline around the whole capsule, plus a thin seam.
    cd.rounded_rectangle([0, 0, 120 * SS - 1, 30 * SS - 1],
                         radius=15 * SS, outline=(10, 90, 90),
                         width=2 * SS)
    cd.line([60 * SS, 2 * SS, 60 * SS, 28 * SS], fill=(10, 90, 90),
            width=SS)
    img.paste(cap, ((x + 4) * SS, (y0 + 7) * SS), cap)
    # Green check badge — the supporting "it works" cue.
    draw.ellipse([x + 128, y0 + 8, x + 156, y0 + 34],
                 fill=(22, 163, 74), outline=(255, 255, 255), width=2)
    draw.line([x + 135, y0 + 21, x + 140, y0 + 26],
              fill=(255, 255, 255), width=3)
    draw.line([x + 140, y0 + 26, x + 150, y0 + 16],
              fill=(255, 255, 255), width=3)

def card_art_12(img, draw, x, y0):
    """Merged Nvidia + AI-tax — Nvidia's chip driven down 14%, with a
    tax (%) on AI. Light background (238,240,236) so the green chip
    and red elements pop. Left: a Nvidia-green NVDA chip (66px wide,
    70% of band height) with dark pins and a darker die. A thick red
    down-arrow presses on the chip's right edge, its head driving
    down to the band's lower edge. Beside the arrowhead, a large red
    "-14%". Right: a small white disc with a red "%" — the tax cue.
    First glance: Nvidia's chip is being driven down 14%, with a
    tax (%) on AI."""
    # Light background — green chip and red elements pop.
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(238, 240, 236))
    # --- Nvidia-green chip, left (66 wide x 32 tall) ---
    # Dark pins: top and bottom.
    for px in (14, 26, 38, 50, 62):
        draw.line([x + px, y0 + 2, x + px, y0 + 5], fill=(60, 90, 0),
                  width=3)
        draw.line([x + px, y0 + 37, x + px, y0 + 40], fill=(60, 90, 0),
                  width=3)
    # Chip body with darker die and white "NVDA".
    draw.rectangle([x + 4, y0 + 6, x + 70, y0 + 36], fill=(118, 185, 0),
                   outline=(60, 90, 0), width=2)
    draw.rectangle([x + 18, y0 + 13, x + 56, y0 + 29], fill=(60, 130, 0))
    draw.text((x + 37, y0 + 21), "NVDA", font=inter(10, 800),
              fill=(255, 255, 255), anchor="mm")
    # --- Thick red down-arrow pressing on the chip's right edge ---
    draw.rectangle([x + 72, y0 + 2, x + 84, y0 + 20], fill=RED)
    draw.polygon([(x + 66, y0 + 20), (x + 90, y0 + 20),
                  (x + 78, y0 + 37)], fill=RED)
    # --- Large red "-14%" beside the arrowhead ---
    draw.text((x + 105, y0 + 21), "-14%", font=inter(13, 800), fill=RED,
              anchor="mm")
    # --- Small white disc with red "%" — the tax cue, right ---
    draw.ellipse([x + 123, y0 + 7, x + 155, y0 + 35],
                 fill=(255, 255, 255), outline=RED, width=2)
    draw.text((x + 139, y0 + 21), "%", font=inter(16, 800), fill=RED,
              anchor="mm")
def card_art_13(draw, x, y0):
    """Phillips hits 118 vs India; first NZ century in all three
    formats — a cricket scorecard. REBUILT BRIGHT: a pale green
    field, one GIANT dark-green "118" (38px, ~83% of the band
    height) as the dominant focal on the left, a thin dark-green
    divider, and on the right "PHILLIPS" in bold dark green over
    a small red cricket ball with white seams — the only
    supporting cue. First glance: 118 runs by Phillips —
    dark green on pale green, never white-on-dark."""
    GREEN = (18, 77, 44)
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(220, 235, 220))
    # Giant score — the focal, left, vertically centred.
    draw.text((x + 6, y0 + 21), "118", font=inter(38, 800),
              fill=(15, 85, 48), anchor="lm")
    # Thin dark-green divider between score and name.
    draw.rectangle([x + 70, y0 + 5, x + 71, y0 + 37],
                   fill=GREEN)
    # Name, bold dark green, top right.
    draw.text((x + 116, y0 + 13), "PHILLIPS", font=inter(12, 800),
              fill=GREEN, anchor="mm")
    # Small red cricket ball, bottom right, with white seams.
    cx, cy, r = x + 116, y0 + 30, 10
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED,
                 outline=GREEN, width=1)
    draw.arc([cx - r, cy - r, cx + r, cy + r], 115, 245,
             fill=(255, 255, 255), width=1)
    draw.arc([cx - r, cy - r, cx + r, cy + r], 295, 65,
             fill=(255, 255, 255), width=1)
def card_art_poland(draw, x, y0):
    """Poland as a CARD (2026-11-21, lead reorder): the old lead
    art scaled down to the 160x42 card band — a cream Poland map
    on a blue field, a thick red EASTERN BORDER, and TWO red
    missile trails from the east edge ending in layered impact
    bursts. Same visual language as the lead, simplified for the
    small band (one label, smaller bursts)."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(190, 210, 232))
    # Poland map, scaled from the lead art (~0.65 x, ~0.58 y).
    land = [(x + 5, y0 + 16), (x + 25, y0 + 6), (x + 62, y0 + 3),
            (x + 98, y0 + 6), (x + 133, y0 + 8), (x + 151, y0 + 13),
            (x + 156, y0 + 22), (x + 148, y0 + 30), (x + 133, y0 + 38),
            (x + 98, y0 + 39), (x + 62, y0 + 39), (x + 29, y0 + 37),
            (x + 9, y0 + 29), (x + 5, y0 + 22)]
    draw.polygon(land, fill=(240, 232, 205), outline=(90, 85, 75))
    draw.line(land + [land[0]], fill=(90, 85, 75), width=2,
              joint="curve")
    # Thick red eastern border, just inside the map's east edge.
    draw.line([(x + 142, y0 + 9), (x + 150, y0 + 13),
               (x + 155, y0 + 21), (x + 150, y0 + 29),
               (x + 139, y0 + 35)], fill=RED, width=3, joint="curve")
    # Two missile trails from the east edge to their impact points.
    for (x1, y1, x2, y2) in [(160, 4, 129, 15), (160, 35, 134, 30)]:
        draw.line([(x + x1, y0 + y1), (x + x2, y0 + y2)], fill=RED,
                  width=3)
        draw.line([(x + x1, y0 + y1), (x + x2, y0 + y2)],
                  fill=(255, 120, 90), width=1)
    # Layered impact bursts with radiating ticks and a white core.
    for bx, by, r in [(129, 15, 11), (134, 30, 9)]:
        for ang in range(0, 360, 30):
            a = math.radians(ang)
            draw.line([x + bx + (r + 2) * math.cos(a),
                       y0 + by + (r + 2) * math.sin(a),
                       x + bx + (r + 5) * math.cos(a),
                       y0 + by + (r + 5) * math.sin(a)],
                      fill=(255, 150, 40), width=1)
        star(draw, x + bx, y0 + by, r, r // 3 + 1, (255, 190, 40))
        star(draw, x + bx, y0 + by, r * 2 // 3, 2, (255, 120, 40))
        star(draw, x + bx, y0 + by, r // 2, 2, RED)
        draw.ellipse([x + bx - 2, y0 + by - 2, x + bx + 2, y0 + by + 2],
                     fill=(255, 255, 255))
    draw.text((x + 10, y0 + 34), "POLAND", font=inter(8, 800),
              fill=INK, anchor="ls")
def card_art_15(draw, x, y0):
    """Gaza — truce line breaking. AFTER: a HUGE red "6" (six killed)
    on a white tile dominates the left two-thirds of the band, with
    the THICK Yellow Line running behind it across the whole band
    and snapping apart at a single restrained orange explosion burst
    on the right. One focal (the 6), two supports (broken yellow
    line, one burst). No gore, no bodies, no clutter."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(238, 232, 214))
    # The Yellow Line: dark underlay for edge contrast, bright yellow
    # on top, in two segments with a wide gap where it breaks.
    for x1, x2 in ((x, x + 68), (x + 110, x + 160)):
        draw.line([x1, y0 + 31, x2, y0 + 31], fill=(120, 100, 10),
                  width=9)
        draw.line([x1, y0 + 31, x2, y0 + 31], fill=(230, 200, 40),
                  width=7)
    # Jagged teeth at the snapped ends of the line.
    draw.polygon([(x + 68, y0 + 27), (x + 76, y0 + 31), (x + 68, y0 + 35)],
                 fill=(210, 170, 25))
    draw.polygon([(x + 110, y0 + 27), (x + 102, y0 + 31),
                  (x + 110, y0 + 35)], fill=(210, 170, 25))
    # White tile + HUGE red "6" — the focal, ~2/3 of the band height.
    draw.rectangle([x + 14, y0 + 4, x + 48, y0 + 38], fill=PANEL,
                   outline=INK)
    draw.text((x + 31, y0 + 21), "6", font=inter(44, 800), fill=RED,
              anchor="mm")
    # Single restrained explosion burst filling the break in the line.
    star(draw, x + 89, y0 + 18, 15, 6, (245, 170, 40), points=8)
    draw.ellipse([x + 83, y0 + 13, x + 95, y0 + 24], fill=RED)
    # Two short crack ticks radiating from the burst.
    draw.line([x + 102, y0 + 9, x + 110, y0 + 5], fill=INK, width=2)
    draw.line([x + 76, y0 + 7, x + 70, y0 + 4], fill=INK, width=2)

def card_art_16(draw, x, y0):
    """Gen Z protests — REBUILT: a BIG march fills the whole band.
    Seven large figures shoulder-to-shoulder, heads and bodies
    filling the lower band to the bottom edge, two raised fists
    punching up at the sides, holding aloft one HUGE central
    placard with a giant red "25" (24px) — the count is the story
    — flanked by two small blank side placards. First glance: a
    youth crowd marching, 25 countries."""
    draw.rectangle([x, y0, x + 160, y0 + 42], fill=(238, 236, 230))
    shirts = [(200, 80, 60), (43, 92, 168), (26, 110, 74),
              (198, 110, 28), (123, 75, 166), (14, 124, 123),
              (200, 80, 60)]
    # Crowd: 7 big figures, heads + bodies filling the lower band.
    for i in range(7):
        px = x + 2 + i * 22
        draw.ellipse([px + 5, y0 + 23, px + 15, y0 + 32],
                     fill=(40, 35, 30))
        draw.rectangle([px, y0 + 31, px + 20, y0 + 42],
                       fill=shirts[i])
    # Raised fists on the two figures flanking the central placard
    # (edge figures hold the side placards; centre figures hold the
    # big one). Fists sit above the side placards so nothing overlaps.
    for i in (1, 5):
        px = x + 2 + i * 22
        draw.line([px + 17, y0 + 33, px + 22, y0 + 9],
                  fill=shirts[i], width=3)
        draw.ellipse([px + 19, y0 + 4, px + 26, y0 + 10],
                     fill=(40, 35, 30))
    # Placard sticks (drawn before the placards, so the placards
    # cover the stick tops).
    for sx in (x + 58, x + 102):
        draw.line([sx, y0 + 26, sx, y0 + 37], fill=(90, 85, 75),
                  width=2)
    for sx in (x + 16, x + 144):
        draw.line([sx, y0 + 20, sx, y0 + 29], fill=(90, 85, 75),
                  width=2)
    # Small blank side placards.
    draw.rectangle([x + 4, y0 + 11, x + 28, y0 + 20], fill=PANEL,
                   outline=(60, 55, 50))
    draw.rectangle([x + 132, y0 + 11, x + 156, y0 + 20], fill=PANEL,
                   outline=(60, 55, 50))
    # Central placard with the giant "25".
    draw.rectangle([x + 50, y0 + 3, x + 110, y0 + 26], fill=PANEL,
                   outline=(60, 55, 50))
    draw.text((x + 80, y0 + 15), "25", font=inter(24, 800), fill=RED,
              anchor="mm")

CARD_ART = {
    5: card_art_5, 6: card_art_6, 7: card_art_7, 8: card_art_8,
    9: card_art_9, 13: card_art_13, 14: card_art_poland,
    15: card_art_15, 16: card_art_16,
}


def draw_card(img, draw, card, x, y0):
    # LAYOUT (2026-11-21, reference rebuild): the card is 154px
    # tall (was 157) — the art band is 42px (was 46) and the whole
    # text block shifts up 4px with its internal spacing unchanged
    # (kicker, 3-line headline at 18px/19 leading, 2-line dek,
    # badge + source).
    w = 160
    region = S.REGION_COLOURS[card["region"]]
    draw.rectangle([x, y0, x + w, y0 + 154], fill=PANEL,
                   outline=PANEL_BORDER)
    art = CARD_ART.get(card["id"])
    if art is not None:
        art(draw, x, y0)
    elif card["id"] == 10:
        card_art_10(img, draw, x, y0)
    elif card["id"] == 11:
        card_art_11(img, draw, x, y0)
    elif card["id"] == 12:
        card_art_12(img, draw, x, y0)
    draw.rectangle([x, y0, x + w, y0 + 3], fill=region)
    cy = y0 + 50
    number_circle(draw, x + 6 + 6, cy, 12, region, card["id"], 8.5)
    draw.text((x + 21, y0 + 55), card["kicker"], font=inter(9.5, 800),
              fill=region, anchor="ls")
    font, lines, leading = fit_headline(
        card["headline"], [(18, 19), (16, 18)], 148)
    ty = y0 + 57
    for line in lines:
        draw.text((x + 6, ty), line, font=font, fill=INK, anchor="la")
        ty += leading
    dek_font, dek_lines = fit_dek(card["dek"], 148)
    ty = y0 + 116
    for line in dek_lines:
        draw.text((x + 6, ty), line, font=dek_font, fill=DEK,
                  anchor="la")
        ty += dek_font.size + 1.5
    # BADGE RULE (2026-11-21, user-confirmed): medium cards show NO
    # CONFIRMED badge — an unmarked medium card reads as confirmed
    # (see the footer legend). REPORTED / CLAIMED badges stay exactly
    # as they are. Leads (draw_lead) keep their CONFIRMED badges.
    if card["status"] != "CONFIRMED":
        badge(draw, x + 6, y0 + 142, card["status"], 10, 8.5)
    # SOURCE 11px (was 9px, 2026-11-21 user order: bigger so it
    # reads clearly). Widest source ("PassBlue · Apex Wire", 107px)
    # is on a CONFIRMED card (no badge); the widest badged source
    # ("The Guardian" / "Reuters · BBC", ~71px) clears the badge
    # (ends ~x+76) by ~7px. Uppercase has no descenders, so the
    # baseline at y0+151 stays 3px clear of the card bottom.
    draw.text((x + w - 6, y0 + 151), card["source"].upper(),
              font=arch(11, 700, 80), fill=SOURCE, anchor="rs")


# Real coastline data: Natural Earth 110m country shapes (public
# domain, github.com/nvkelso/natural-earth-vector), prepared exactly
# as in makefun-news19 (prep_geo.py): Antarctica dropped, outer
# rings only, coordinates rounded to 0.1 deg. Copied to
# data/world.json — loaded from local disk, no network at runtime.
WORLD = json.load(open(HERE / "data" / "world.json"))


# ------------------------------------------------------------- map + briefs

# World map projection (redrawn 2026-11-21 — real coastlines replace
# the old crude polygons). Equirectangular, cropped to the inhabited
# world so the panel fills: lon -135..155 (Alaska west of -135,
# New Zealand east of 155 and Chukotka are cut at the frame, as on a
# cropped atlas map), lat 62..-44 (2026-11-21, reference rebuild:
# was 70..-46 — the high Arctic and deep Antarctic are empty sea,
# and the crop saves ~9px of height; every dot is inside it: the
# northernmost dot is Tallinn at 59.44N, the southernmost is
# Wellington at -41.3). X scale 0.862 px/deg, Y scale 0.95 px/deg —
# the map is 250x101px (was 196x110), aspect 2.48, nearly true
# equirectangular (2.5) — and the wider panel gives the Europe
# cluster more horizontal room. The panel is 250px wide (the full
# left column) and 108px tall; the map is centred in it with
# ~3.7px sea margins top/bottom.
# (Round 5, 2026-11-21: panel grew 154 -> 172px tall so the block
# reaches down toward the Date Check; the map stays centred, sea
# margins 24.9px top/bottom, dots shift down ~9px with it.)
# (Reference rebuild, 2026-11-21: the panel is now 250x108 in the
# 3-column bottom section, and the caption is DROPPED — the
# reference has no caption, and the numbered dots match the story
# numbers. The Date Check box sits directly below the map.)
MAP_LON0, MAP_LON1 = -135.0, 155.0
MAP_LAT_TOP, MAP_LAT_BOT = 62.0, -44.0
MAP_TILE_W, MAP_TILE_H = 250, 108
# MAP_OY = the tile's top edge in page coords. The bottom section
# (reference layout) starts at y=726: the map tile is 250x108 at
# (12, 726) and the Date Check box sits below it (840..998).
# MAP_TOP centres the 100.7px of geography inside the 108px tile.
MAP_OY = 726
# Dot-layout clamp box (7px inset from the tile edges): the dots'
# anchors span x 12..262 / y 732..828, so this box barely moves
# them — unlike the old [19, 201] x [762, 900] clamps, which were
# left over from the 196px tile and shoved every dot off its place.
MAP_DOT_XMIN, MAP_DOT_XMAX = 19, 255
MAP_DOT_YMIN, MAP_DOT_YMAX = 733, 827
MAP_XSCALE = MAP_TILE_W / (MAP_LON1 - MAP_LON0)
MAP_YSCALE = 0.95
MAP_TOP = MAP_OY + (MAP_TILE_H - (MAP_LAT_TOP - MAP_LAT_BOT)
                    * MAP_YSCALE) / 2
# Numbered dots: 11px white halo / 10px coloured disc / 7px number
# (was 13px / 12px / 8px). The smaller disc is what lets the dots
# sit on (or just beside) their true countries now that no leader
# line ties a displaced dot back to its place: in the Europe
# cluster five stories sit within a 21px band, and at 13px the
# layout had to push dots 9-13px off their anchors, into the
# wrong country. Minimum centre distance is _min_sep (10.5px
# numbered-numbered, 7.0px numbered-brief, 5.0px brief-brief):
# the white halos may kiss — white on white is invisible — and
# a brief disc may overlap a numbered disc by at most 1px, but
# both dots stay visible and readable. The DIGITS are protected
# separately, by two guarantees in draw_map / _clear_digits:
# (a) paint order — brief dots are drawn first, numbered dots
# (disc + digit) second, so a brief dot can never cover a digit;
# (b) _clear_digits nudges any brief dot whose disc comes within
# 1px of a digit's ink away from it (ink-accurate; caged dots
# with no full-clear spot get the best small maximin move).
# A halo-based separation
# (11.5px / 9.5px) left no feasible spot for the German briefs
# at all: the nearest separation-satisfying position for the
# Gottingen dot was 15px away in the Norwegian Sea.
# Brief dots: 7px white halo / 6px coloured disc, no number —
# visibly smaller than the numbered dots. There are NO leader
# lines and NO anchor dots anywhere on the map: the dots are laid
# out by a spring force (each dot pulled to its true anchor,
# pushed apart from any dot closer than _min_sep, so a
# dot sits on its true place unless a neighbour forced the minimum
# nudge — and when two dots collide, the smaller one does the
# moving (brief dots are laid out against fixed numbered dots).
# Dots that the layout leaves in the sea are pulled back toward
# their anchor until they sit on land, where the separations allow.
MAP_DOT_OUTER = 5.5
MAP_DOT_R = 5.0
MAP_DOT_MIN_SEP = 10.5
MAP_DOT_FONT = 7
BRIEF_DOT_OUTER = 3.5
BRIEF_DOT_R = 3.0


def _min_sep(ri, rj):
    """Minimum centre distance for two dots with disc radii ri, rj.
    Numbered-numbered: 10.5px (discs 0.5px apart). Numbered-brief:
    7.0px (the brief disc overlaps the numbered disc by at most
    1px — both stay visible, and the brief stays in its country).
    Brief-brief: 5.0px (discs overlap at most 1px)."""
    if ri > 4.0 and rj > 4.0:
        return 10.5
    if ri > 4.0 or rj > 4.0:
        return 7.0
    return 5.0


def _map_xy(lon, lat):
    """Project lon/lat to panel coordinates (1x space)."""
    return (12 + (lon - MAP_LON0) * MAP_XSCALE,
            MAP_TOP + (MAP_LAT_TOP - lat) * MAP_YSCALE)


def _map_lonlat(x, y):
    """Inverse of _map_xy: panel coordinates back to lon/lat."""
    return (MAP_LON0 + (x - 12) / MAP_XSCALE,
            MAP_LAT_TOP - (y - MAP_TOP) / MAP_YSCALE)


# Land grid: the coastline polygons rasterised at 2 px/deg, used only
# to test whether a dot centre sits on land (so a dot the layout
# pushed off its anchor can be pulled back onto land instead of
# floating in the sea). Antimeridian-split exactly like draw_map.
_LAND_PX = 2
_LAND_W = int((MAP_LON1 - MAP_LON0) * _LAND_PX)
_LAND_H = int((MAP_LAT_TOP - MAP_LAT_BOT) * _LAND_PX)
_LAND = Image.new("L", (_LAND_W, _LAND_H), 0)
_LAND_DRAW = ImageDraw.Draw(_LAND)
for _ring in WORLD:
    _sub, _prev = [], None
    for _lon, _lat in _ring:
        if _prev is not None and abs(_lon - _prev) > 180:
            if len(_sub) >= 3:
                _LAND_DRAW.polygon(
                    [((_lo - MAP_LON0) * _LAND_PX,
                      (MAP_LAT_TOP - _la) * _LAND_PX)
                     for _lo, _la in _sub], fill=255)
            _sub = []
        _sub.append((_lon, _lat))
        _prev = _lon
    if len(_sub) >= 3:
        _LAND_DRAW.polygon(
            [((_lo - MAP_LON0) * _LAND_PX,
              (MAP_LAT_TOP - _la) * _LAND_PX)
             for _lo, _la in _sub], fill=255)
# One-cell dilation: at 2 px/deg a coastal dot can rasterise
# just offshore (Caracas, Durban); land really extends 0.5 deg
# further out than the raw grid says.
_LAND = _LAND.filter(ImageFilter.MaxFilter(3))
_LAND_PXDATA = _LAND.load()


def _panel_on_land(x, y):
    """True if panel point (x, y) sits on land (per the land grid)."""
    lon, lat = _map_lonlat(x, y)
    gx = int((lon - MAP_LON0) * _LAND_PX)
    gy = int((MAP_LAT_TOP - lat) * _LAND_PX)
    return (0 <= gx < _LAND_W and 0 <= gy < _LAND_H
            and _LAND_PXDATA[gx, gy] > 0)


def _split_dir(ax, ay, dist):
    """Split direction for two dots on the same anchor: the first of
    8 compass directions that puts both split points on land, else
    due east. Deterministic."""
    best, best_score = (1.0, 0.0), -1
    for k in range(8):
        ang = math.radians(45 * k)
        ux, uy = math.cos(ang), math.sin(ang)
        score = (1 if _panel_on_land(ax + ux * dist, ay + uy * dist)
                 else 0)
        score += (1 if _panel_on_land(ax - ux * dist, ay - uy * dist)
                  else 0)
        if score > best_score:
            best, best_score = (ux, uy), score
    return best


def _layout_dots(anchors, radii, fixed=(), iters=4000, spring=0.03):
    """Deterministic force layout of dot centres. Every free dot is
    spring-pulled to its anchor and pushed away from any dot closer
    than _min_sep(radii[i], radii[j]); fixed dots never move
    (numbered dots, when the brief dots are laid out against them).
    The target separation is inflated by 0.6px: the spring holds each
    dot slightly inside its target, so the settled distance lands
    just above the true minimum instead of just below it. A dot
    sitting in the sea pulls three times harder toward its anchor
    than a dot on land, so the layout spends displacement on land
    dots rather than parking a dot offshore — but the repulsion
    itself is full strength on both dots, so a sea dot is never
    left inside a violation by a weakened push. Two dots on the
    same anchor (3 and 6, both New York; 31 and 33; 34, 38 and 39,
    all Washington DC) split along _split_dir. Clamped inside the
    panel (MAP_DOT_XMIN..MAP_DOT_XMAX, MAP_DOT_YMIN..MAP_DOT_YMAX —
    7px inset from the 250x108 tile at (12, 726); in practice the
    dots sit near their anchors, so the caps rarely bind)."""
    n = len(anchors)
    fixed = set(fixed)
    free = [i for i in range(n) if i not in fixed]
    pos = [[x, y] for x, y in anchors]

    def sep(i, j):
        return _min_sep(radii[i], radii[j]) + 0.6

    rep, max_step = 1.0, 0.5
    for _ in range(iters):
        max_move = 0.0
        for i in free:
            x, y = pos[i]
            ax, ay = anchors[i]
            pull = spring * (3.0 if not _panel_on_land(x, y) else 1.0)
            fx = (ax - x) * pull
            fy = (ay - y) * pull
            for j in range(n):
                if j == i:
                    continue
                dx, dy = x - pos[j][0], y - pos[j][1]
                d = math.hypot(dx, dy)
                target = sep(i, j)
                if d < target:
                    if d < 1e-9:
                        ux, uy = _split_dir(ax, ay, target / 2)
                    else:
                        ux, uy = dx / d, dy / d
                    push = (target - d) * rep
                    fx += ux * push
                    fy += uy * push
            step = math.hypot(fx, fy)
            if step > max_step:
                fx, fy = fx / step * max_step, fy / step * max_step
                step = max_step
            pos[i][0] = min(MAP_DOT_XMAX, max(MAP_DOT_XMIN, x + fx))
            pos[i][1] = min(MAP_DOT_YMAX, max(MAP_DOT_YMIN, y + fy))
            max_move = max(max_move, step)
        if max_move < 0.005:
            break
    return [(x, y) for x, y in pos]


def _project_dots(pos, radii, fixed=(), iters=3000):
    """Hard enforcement of the minimum separations: any pair closer
    than _min_sep(radii[i], radii[j]) is pushed apart (half
    the needed push per pass, which damps the bounce of a dot
    caged between several neighbours). A dot in the sea moves a
    quarter of the push and its land neighbour three quarters, so
    the sea dot keeps its place; fixed dots never move. Runs after
    _layout_dots, whose spring balance can leave a pair a fraction
    of a pixel inside its minimum."""
    fixed = set(fixed)
    n = len(pos)
    pos = [list(p) for p in pos]
    for _ in range(iters):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                need = _min_sep(radii[i], radii[j])
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                d = math.hypot(dx, dy)
                if d < need:
                    if d < 1e-9:
                        ux, uy = _split_dir(pos[i][0], pos[i][1],
                                            need / 2)
                    else:
                        ux, uy = dx / d, dy / d
                    push = (need - d) * 0.5
                    # Heaviness: fixed is infinite, sea is 3, land 1.
                    # A dot moves in inverse proportion to its weight.
                    wi = 1e9 if i in fixed else (
                        3 if not _panel_on_land(*pos[i]) else 1)
                    wj = 1e9 if j in fixed else (
                        3 if not _panel_on_land(*pos[j]) else 1)
                    pos[i][0] -= ux * push * wj / (wi + wj)
                    pos[i][1] -= uy * push * wj / (wi + wj)
                    pos[j][0] += ux * push * wi / (wi + wj)
                    pos[j][1] += uy * push * wi / (wi + wj)
                    moved = True
        for q in pos:
            q[0] = min(MAP_DOT_XMAX, max(MAP_DOT_XMIN, q[0]))
            q[1] = min(MAP_DOT_YMAX, max(MAP_DOT_YMIN, q[1]))
        if not moved:
            break
    return [(x, y) for x, y in pos]


def _escape_caged_dots(pos, anchors, radii, fixed=()):
    """Deterministic escape for dots the projection could not
    separate: a dot caged between several neighbours bounces
    between their exclusion zones forever. Scan expanding rings
    around the dot's current position (0.5px steps to 25px, 32
    compass directions — fine enough to find the lens-shaped gap
    between two numbered dots) and take the nearest position
    that satisfies every separation. Land is preferred over sea
    across the whole range: a dot in the Norwegian Sea is worse
    than the same dot 2px further on in Norway. Fixed dots are
    never moved."""
    fixed = set(fixed)
    n = len(pos)
    pos = [list(p) for p in pos]

    def ok(i, x, y):
        if not (MAP_DOT_XMIN <= x <= MAP_DOT_XMAX
                and MAP_DOT_YMIN <= y <= MAP_DOT_YMAX):
            return False
        return all(j == i or math.hypot(x - pos[j][0], y - pos[j][1])
                   >= _min_sep(radii[i], radii[j])
                   for j in range(n))

    for i in range(n):
        if i in fixed:
            continue
        # Only escape a dot whose worst shortfall exceeds 2px: the
        # layout already leaves the dots within ~1px of their
        # minimum, discs just kissing, and a sub-2px overlap keeps
        # both dots visible in the right country — while the escape
        # would fling the dot 10px+ to the nearest feasible spot
        # (measured: the Gottingen brief to the Norwegian Sea).
        worst = 0.0
        for j in range(n):
            if j == i:
                continue
            short = (_min_sep(radii[i], radii[j])
                     - math.hypot(pos[i][0] - pos[j][0],
                                  pos[i][1] - pos[j][1]))
            worst = max(worst, short)
        if worst <= 2.0:
            continue
        # Scan around the dot's CURRENT position, not its anchor:
        # the layout already put it as close to home as the pack
        # allows, so the nearest feasible spot is a short hop, not
        # a 15px fling to the other side of the cage.
        ax, ay = pos[i]
        placed = None
        for want_land in (True, False):
            for r10 in range(0, 251, 5):
                r = r10 / 10.0
                for k in range(32):
                    ang = math.radians(11.25 * k)
                    x = ax + r * math.cos(ang)
                    y = ay + r * math.sin(ang)
                    if ok(i, x, y) and (
                            not want_land or _panel_on_land(x, y)):
                        placed = (x, y)
                        break
                if placed:
                    break
            if placed:
                break
        if placed is not None:
            pos[i] = list(placed)
    return [(x, y) for x, y in pos]


def _rescue_sea_dots(pos, anchors, radii, fixed=()):
    """Pull any free dot whose centre is in the sea back toward its
    anchor until it sits on land, keeping every separation at
    _min_sep(radii[i], radii[j]) - 0.3 or better. Dots whose
    anchor is itself at sea (36 Qeshm Island, too small to draw at
    this scale) are left where the layout put them."""
    fixed = set(fixed)
    n = len(pos)
    pos = [list(p) for p in pos]
    for i in range(n):
        if i in fixed or _panel_on_land(*pos[i]):
            continue
        if not _panel_on_land(*anchors[i]):
            continue
        cx, cy = pos[i]
        ax, ay = anchors[i]
        dist = math.hypot(ax - cx, ay - cy)
        if dist < 0.25:
            continue
        ux, uy = (ax - cx) / dist, (ay - cy) / dist
        for s in range(1, int(dist / 0.25) + 1):
            nx, ny = cx + ux * 0.25 * s, cy + uy * 0.25 * s
            if not _panel_on_land(nx, ny):
                continue
            if all(j == i or math.hypot(nx - pos[j][0],
                                        ny - pos[j][1])
                   >= _min_sep(radii[i], radii[j]) - 0.3
                   for j in range(n)):
                pos[i] = [nx, ny]
                break
    return [(x, y) for x, y in pos]


_DIGIT_INK = {}


def _digit_ink(nid):
    """Ink sample points of numbered dot nid's digit, centre-relative
    1x coords, sampled every 0.25px (1 SS px) from the rendered
    glyph mask. Cached. The digit is white on its coloured disc; a
    brief dot's disc (r 3) must stay >= 4.0px from every ink point:
    3.0 (its own radius) + 1.0px of clear air. Ink-accurate, not
    bbox: a digit's bbox corners are empty, so a bbox rule would
    fling caged dots 8-16px to the wrong country (measured:
    Gottingen -> Italy, Cologne -> the North Sea, Washington DC
    -> North Dakota)."""
    if nid not in _DIGIT_INK:
        font = inter(MAP_DOT_FONT, 800)
        tile = Image.new("L", (400, 400), 0)
        ImageDraw.Draw(tile).text((200, 200), str(nid), font=font,
                                  fill=255, anchor="mm")
        px = tile.load()
        bb = tile.getbbox()
        pts = [((xx - 200) / SS, (yy - 200) / SS)
               for yy in range(bb[1], bb[3])
               for xx in range(bb[0], bb[2])
               if px[xx, yy] > 127]
        _DIGIT_INK[nid] = pts
    return _DIGIT_INK[nid]


def _digit_gap(bx, by, nx, ny, nid):
    """Distance from a brief-dot centre to the nearest ink pixel of
    numbered dot nid's digit. >= 4.0 means the brief disc (r 3)
    clears the digit by >= 1px."""
    return min(math.hypot(bx - (nx + ix), by - (ny + iy))
               for ix, iy in _digit_ink(nid))


def _brief_digit_clear(bx, by, centres):
    """True if a brief dot at (bx, by) clears every numbered digit
    by >= 1px. Only nearby numbered dots can matter: ink reaches
    at most 4px from a numbered centre, so a centre distance over
    9px is clear by construction."""
    for (nid, _, _, _), (nx, ny) in zip(S.MAP_ANCHORS, centres):
        if abs(bx - nx) > 9 or abs(by - ny) > 9:
            continue
        if _digit_gap(bx, by, nx, ny, nid) < 4.0:
            return False
    return True


def _worst_digit_gap(bx, by, centres):
    """Smallest ink gap over all numbered digits (centre-to-ink
    distance minus the brief disc radius 3)."""
    worst = 99.0
    for (nid, _, _, _), (nx, ny) in zip(S.MAP_ANCHORS, centres):
        if abs(bx - nx) > 9 or abs(by - ny) > 9:
            continue
        worst = min(worst, _digit_gap(bx, by, nx, ny, nid) - BRIEF_DOT_R)
    return worst


# Effective white-halo radius of a numbered dot: nominal
# MAP_DOT_OUTER is 5.5px, but _sc_box's inclusive box widens every
# ellipse by 0.5px of diameter, so the halo really spans 12px
# (verified on isolated dot 7: solid halo to +-6px). A brief dot
# whose centre sits inside a numbered halo has its core painted
# over by that halo (numbered dots paint on top), so a visible
# brief dot needs its centre outside every halo.
HALO_EFF = 6.0


def _halo_clearance(bx, by, centres):
    """How far a brief-dot centre sits outside the nearest numbered
    halo (>= 0 means its core shows)."""
    return min(math.hypot(bx - nx, by - ny)
               for (_, _, _, _), (nx, ny) in zip(S.MAP_ANCHORS, centres)) \
        - HALO_EFF


def _clear_digits(centres, brief_centres):
    """Nudge brief dots off the numbered digits. Numbered dots never
    move; brief dots do the moving. Two stages, deterministic:
    1. FULL CLEAR: ring-scan (0.25px steps to 6px, 32 directions)
       for the nearest spot clearing every digit by >= 1px
       (ink-accurate, see _digit_ink) AND sitting outside every
       numbered halo (so the brief dot's core stays visible now
       that numbered dots paint on top), keeping brief-brief
       separation >= 5px and the panel bounds. Land preferred at
       each ring.
    2. MAXIMIN: dots with no full-clear spot in range — caged
       between three numbered digits — get the best small move
       (<= 1.5px) on the combined worst of (digit ink gap, halo
       clearance), but only if it improves that worst by >= 0.2px.
    Returns the new brief centres."""
    brief = [list(p) for p in brief_centres]

    def brief_ok(i, x, y):
        return all(j == i or math.hypot(x - brief[j][0],
                                        y - brief[j][1]) >= 5.0
                   for j in range(len(brief)))

    def combined_worst(x, y):
        return min(_worst_digit_gap(x, y, centres),
                   _halo_clearance(x, y, centres))

    for i in range(len(brief)):
        if (_brief_digit_clear(brief[i][0], brief[i][1], centres)
                and _halo_clearance(brief[i][0], brief[i][1],
                                    centres) >= 0.0
                and brief_ok(i, brief[i][0], brief[i][1])):
            continue
        ox, oy = brief[i]
        placed = None
        for r10 in range(0, 25):
            r = r10 / 4.0
            cands = []
            for k in range(32):
                ang = math.radians(11.25 * k)
                x = ox + r * math.cos(ang)
                y = oy + r * math.sin(ang)
                if not (MAP_DOT_XMIN <= x <= MAP_DOT_XMAX
                        and MAP_DOT_YMIN <= y <= MAP_DOT_YMAX):
                    continue
                if not _brief_digit_clear(x, y, centres):
                    continue
                if _halo_clearance(x, y, centres) < 0.0:
                    continue
                if not brief_ok(i, x, y):
                    continue
                cands.append((x, y))
            if cands:
                land = [c for c in cands if _panel_on_land(*c)]
                placed = land[0] if land else cands[0]
                break
        if placed is not None:
            brief[i] = list(placed)
            continue
        cur = combined_worst(ox, oy)
        best, best_gap = None, cur
        for r10 in range(1, 7):
            r = r10 / 4.0
            for k in range(32):
                ang = math.radians(11.25 * k)
                x = ox + r * math.cos(ang)
                y = oy + r * math.sin(ang)
                if not (MAP_DOT_XMIN <= x <= MAP_DOT_XMAX
                        and MAP_DOT_YMIN <= y <= MAP_DOT_YMAX):
                    continue
                if not brief_ok(i, x, y):
                    continue
                g = combined_worst(x, y)
                if g > best_gap + 1e-9:
                    best, best_gap = (x, y), g
        if best is not None and best_gap - cur >= 0.2:
            brief[i] = list(best)
    return [(x, y) for x, y in brief]


def draw_map(img, draw):
    # MAP, FIXED + RESIZED (2026-11-21, reference layout): the tile
    # is now 250x108 at (12, 726) — the full left column, matching
    # the projection constants (MAP_TILE_W=250, MAP_OY=726) that the
    # previous rebuild set but never wired up (the old code still
    # pasted a 196x169 tile at (12, 740) with the old clamps, so
    # East Asia was clipped off and every dot was shoved off its
    # anchor). The geography (100.7px) is centred in the 108px
    # tile with ~3.7px sea margins; the dots' anchors span
    # y 732..828, inside the tile. The CAPTION IS DROPPED — the
    # reference has none, and the Date Check box sits directly
    # below the map (840..998); the numbered dots match the story
    # numbers, so no legend is needed.
    ox, oy = 12, 726
    tile = Image.new("RGB", (250 * SS, 108 * SS), (222, 232, 240))
    td = SSDraw(ImageDraw.Draw(tile), tile)

    def T(lon, lat):
        """Project lon/lat to tile-local coordinates."""
        x, y = _map_xy(lon, lat)
        return (x - ox, y - oy)

    for ring in WORLD:
        # Split the ring wherever it jumps across the antimeridian
        # (Russia, Fiji): without the split Pillow would draw a line
        # right across the Pacific.
        sub, prev = [], None
        for lon, lat in ring:
            if prev is not None and abs(lon - prev) > 180:
                if len(sub) >= 3:
                    td.polygon([T(lo, la) for lo, la in sub],
                               fill=(238, 232, 214),
                               outline=(200, 192, 170))
                sub = []
            sub.append((lon, lat))
            prev = lon
        if len(sub) >= 3:
            td.polygon([T(lo, la) for lo, la in sub],
                       fill=(238, 232, 214), outline=(200, 192, 170))
    anchors = [_map_xy(lon, lat) for _, _, lon, lat in S.MAP_ANCHORS]
    n_radii = [MAP_DOT_R] * len(anchors)
    centres = _layout_dots(anchors, n_radii)
    centres = _project_dots(centres, n_radii)
    centres = _escape_caged_dots(centres, anchors, n_radii)
    centres = _rescue_sea_dots(centres, anchors, n_radii)
    centres = _project_dots(centres, n_radii)
    # Brief dots: small unnumbered discs in their region colour, laid
    # out against the FIXED numbered dots — the brief dot does the
    # moving, never the numbered one.
    b_anchors = [_map_xy(lon, lat) for _, _, lon, lat in S.BRIEF_ANCHORS]
    all_anchors = anchors + b_anchors
    all_radii = n_radii + [BRIEF_DOT_R] * len(b_anchors)
    # Start the numbered dots at their phase-1 centres (they are
    # fixed here, so starting them on their anchors would leave
    # coincident pairs — 3 and 6, both New York — on top of each
    # other); the brief dots start on their anchors.
    all_pos = _layout_dots(centres + b_anchors, all_radii,
                           fixed=set(range(len(anchors))))
    all_pos = _project_dots(all_pos, all_radii,
                            fixed=set(range(len(anchors))))
    all_pos = _escape_caged_dots(all_pos, all_anchors, all_radii,
                                 fixed=set(range(len(anchors))))
    all_pos = _rescue_sea_dots(all_pos, all_anchors, all_radii,
                               fixed=set(range(len(anchors))))
    all_pos = _project_dots(all_pos, all_radii,
                            fixed=set(range(len(anchors))))
    all_pos = _escape_caged_dots(all_pos, all_anchors, all_radii,
                                 fixed=set(range(len(anchors))))
    brief_centres = all_pos[len(anchors):]
    # Digit clearance: nudge brief dots off the numbered digits
    # (ink-accurate, numbered dots fixed). See _clear_digits.
    brief_centres = _clear_digits(centres, brief_centres)
    # PAINT ORDER (numbered dots on top): the brief dots are drawn
    # FIRST and the numbered dots SECOND, so a numbered disc and
    # its white digit always paint over any brief dot beneath them
    # — a brief dot can never cover or obscure a digit, and the
    # numbered disc's own coloured ring (>= 1px between digit ink
    # and disc edge) always separates digit ink from any visible
    # brief pixel. Reversing this order would let brief dots sit
    # on top of the digits.
    for (sid, region, _, _), (cx, cy) in zip(S.BRIEF_ANCHORS,
                                            brief_centres):
        lx, ly = cx - ox, cy - oy
        td.ellipse([lx - BRIEF_DOT_OUTER, ly - BRIEF_DOT_OUTER,
                    lx + BRIEF_DOT_OUTER, ly + BRIEF_DOT_OUTER],
                   fill=(255, 255, 255))
        td.ellipse([lx - BRIEF_DOT_R, ly - BRIEF_DOT_R,
                    lx + BRIEF_DOT_R, ly + BRIEF_DOT_R],
                   fill=S.REGION_COLOURS[region])
    for (sid, region, _, _), (cx, cy) in zip(S.MAP_ANCHORS, centres):
        lx, ly = cx - ox, cy - oy
        td.ellipse([lx - MAP_DOT_OUTER, ly - MAP_DOT_OUTER,
                    lx + MAP_DOT_OUTER, ly + MAP_DOT_OUTER],
                   fill=(255, 255, 255))
        td.ellipse([lx - MAP_DOT_R, ly - MAP_DOT_R,
                    lx + MAP_DOT_R, ly + MAP_DOT_R],
                   fill=S.REGION_COLOURS[region])
        td.text((lx, ly), str(sid), font=inter(MAP_DOT_FONT, 800),
                fill=(255, 255, 255), anchor="mm")
    img.paste(tile, (ox * SS, oy * SS))


def _wrap_segments(segments, font, width):
    """Wrap (text, fill) segments into lines of (text, fill) runs.
    Segments are split into words (the '·' separators are their own
    tokens, space-separated in the source); words are packed
    greedily, each carrying its fill, so a wrapped Markets line
    keeps its red negatives red. Returns a list of lines, each a
    list of (word, fill)."""
    tokens = []
    for text, fill in segments:
        for word in text.split(" "):
            if word:
                tokens.append((word, fill))
    lines, cur, cur_w = [], [], 0
    space_w = font.getlength(" ")
    for word, fill in tokens:
        ww = font.getlength(word)
        add = ww if not cur else space_w + ww
        if cur and cur_w + add > width:
            lines.append(cur)
            cur, cur_w = [(word, fill)], ww
        else:
            cur.append((word, fill))
            cur_w += add
    if cur:
        lines.append(cur)
    return lines


def _wrap_with_head(segments, font, first_width, width):
    """Wrap (text, fill) segments where the FIRST line has less room
    (a bold head precedes it) and continuation lines have the full
    width — used by the MARKETS/SPORT brief rows (2026-11-21).
    Greedy word packing, with one refinement: a negative percentage
    (a word starting with "-") never starts a line on its own — the
    previous word (its label) is pulled onto the new line with it,
    so "Nikkei -5.06%" never splits across a line break."""
    tokens = []
    for text, fill in segments:
        for word in text.split(" "):
            if word:
                tokens.append((word, fill))
    lines, cur, cur_w = [], [], 0
    space_w = font.getlength(" ")
    cap = first_width
    for word, fill in tokens:
        ww = font.getlength(word)
        add = ww if not cur else space_w + ww
        if cur and cur_w + add > cap:
            if word.startswith("-") and len(cur) >= 1:
                prev_word, prev_fill = cur.pop()
                cur_w -= space_w + font.getlength(prev_word)
                lines.append(cur)
                cur = [(prev_word, prev_fill), (word, fill)]
                cur_w = (font.getlength(prev_word) + space_w + ww)
            else:
                lines.append(cur)
                cur, cur_w = [(word, fill)], ww
            cap = width
        else:
            cur.append((word, fill))
            cur_w += add
    if cur:
        lines.append(cur)
    return lines


def _draw_seg_line(draw, x, base, line, font):
    """Draw one wrapped segment line: words left to right, each in
    its own fill, single spaces between words."""
    cx = x
    for i, (word, fill) in enumerate(line):
        if i > 0:
            cx += font.getlength(" ")
        draw.text((cx, base), word, font=font, fill=fill, anchor="ls")
        cx += font.getlength(word)


def draw_flag(draw, x, y, code):
    """Real flag image in an 18x12 slot (see _flag_image), with the
    uniform hairline from _flag_outline hugging its true fitted
    edges — not the slot, so a 2:1 flag (US) or a pennant (Nepal)
    gets no empty box around it. The 18 Nov winner's brief flags
    are bare real flags in the same fixed slot (verified
    pixel-level: no border, no shadow, just flag pixels on paper);
    the hairline is the entry's polish on that style, and it is
    what keeps a white field (Japan, Nepal) readable on paper.
    The GTA and CLAIM chips are retained but no longer used by any
    brief: brief 51 (GTA VI, set in Leonida — Rockstar's Florida,
    "Vice City, USA") now flies the US flag, and brief 52
    (Riemann, German mathematician, 1859 hypothesis) the German
    flag."""
    if code == "GTA":
        draw.rectangle([x, y, x + 18, y + 12], fill=(0, 0, 0))
        draw.text((x + 9, y + 6), "VI", font=inter(9, 800),
                  fill=(212, 175, 55), anchor="mm")
        return
    if code == "CLAIM":
        draw.rectangle([x, y, x + 18, y + 12], fill=(220, 220, 220))
        draw.text((x + 9, y + 6), "π", font=inter(10, 700),
                  fill=(60, 60, 60), anchor="mm")
        return
    draw.paste(_flag_image(code, 18, 12), (x, y))
    _flag_outline(draw, x, y, code, 18, 12)


def draw_markets_icon(draw, x, y):
    """MARKETS logo in the 18x12 flag slot (2026-11-21, user order):
    a small line chart — a volatile polyline in INK with a red
    arrowhead at the end — on paper, with the same 1px hairline
    (180, 175, 165) around the slot as the flags. Clean vector
    shapes, no emoji, no text."""
    draw.line([(x + 1, y + 9), (x + 6, y + 5), (x + 11, y + 7),
               (x + 16, y + 2)], fill=INK, width=2, joint="curve")
    draw.polygon([(x + 17, y + 0), (x + 12, y + 1), (x + 16, y + 6)],
                 fill=RED)
    draw.rectangle([x, y, x + 18, y + 12], outline=(180, 175, 165))


def draw_sport_icon(draw, x, y):
    """SPORT logo in the 18x12 flag slot (2026-11-21, user order):
    a small gold trophy — cup with handles, stem and base — with
    the same 1px hairline (180, 175, 165) around the slot as the
    flags. Clean vector shapes, no emoji, no text."""
    gold = (212, 175, 55)
    # Cup body with an ink outline.
    draw.polygon([(x + 5, y + 1), (x + 13, y + 1), (x + 12, y + 7),
                  (x + 6, y + 7)], fill=gold, outline=INK)
    # Handles (arcs opening outward).
    draw.arc([x + 1, y + 2, x + 6, y + 7], 90, 270, fill=gold,
             width=2)
    draw.arc([x + 12, y + 2, x + 17, y + 7], 270, 90, fill=gold,
             width=2)
    # Stem and base.
    draw.rectangle([x + 8, y + 7, x + 10, y + 9], fill=gold)
    draw.rectangle([x + 6, y + 9, x + 12, y + 11], fill=gold)
    draw.rectangle([x, y, x + 18, y + 12], outline=(180, 175, 165))


def draw_briefs(draw):
    # LAYOUT, REFERENCE REBUILD (2026-11-21): the 24 briefs are now
    # TWO region-grouped columns (not 3 plain columns), with a
    # header + count per column, like the reference's bottom
    # section. Middle column (x 274..638): Americas + Africa +
    # Middle East = 13 briefs (N. America 3, Latin America 2,
    # Africa 4, Middle East 4). Right column (x 650..1012):
    # Europe + Asia + Global = 11 briefs (Europe 4, Asia 6,
    # Global 1). Headers carry the region list (left) and the
    # count (right-aligned). Briefs keep their flag, bold head and
    # text, no sources.
    # FONT 14px, PITCH 18px (2026-11-21, user order: bigger so it
    # reads clearly): the columns are ~364px wide, so every brief
    # fits whole with room to spare (longest brief 260.0px at 14px
    # vs 344px text width). First row top 728, baseline top+12.
    # SEPARATORS (2026-11-21, user order): a 1px hairline
    # (205, 200, 190) between every brief row, and between the
    # last brief and the MARKETS/SPORT row — drawn at top+17.7,
    # 2.2px clear of the descenders above and the caps below
    # (14px text, 18px pitch). No separator after the MARKETS/
    # SPORT row (its descenders end ~996, footer rule 1001 — no
    # room for a 2px-clear line).
    # MARKETS + SPORT (2026-11-21, user order): they are now
    # BRIEF-STYLE ROWS closing their columns — a logo in the flag
    # slot (chart icon for MARKETS, trophy for SPORT), a bold head
    # ("MARKETS: " / "SPORT: ") and the figures/results wrapped
    # with _wrap_with_head, NOT the old plain wrapped lines. They
    # run at 12.5px (not 14px): at 13.5px+ the bold head pushes
    # MARKETS to 3 lines, which does not fit — at 12.5px it is a
    # clean 2 lines and SPORT is 4 lines, both with the label kept
    # with its value ("Nikkei -5.06%" never splits). A +2px gap
    # precedes each row so the separator above it clears the icon
    # by 3.3px. Nothing is lost: every figure and every sport
    # result survives, negatives stay red.
    bold = inter(14, 700)
    regular = inter(14, 400)
    head_font = inter(12, 800)
    # Brief groups, in original BRIEFS order within each group.
    mid = [b for b in S.BRIEFS if b[1] in ("North America",
                                           "Latin America", "Africa",
                                           "Middle East")]
    right = [b for b in S.BRIEFS if b[1] in ("Europe", "Asia",
                                            "Global")]
    # Column headers (baseline 722): region list left, count right.
    draw.text((274, 722), "AMERICAS · AFRICA · MIDDLE EAST",
              font=head_font, fill=RED, anchor="ls")
    draw.text((638, 722), str(len(mid)), font=head_font, fill=RED,
              anchor="rs")
    draw.text((650, 722), "EUROPE · ASIA · GLOBAL",
              font=head_font, fill=RED, anchor="ls")
    draw.text((1012, 722), str(len(right)), font=head_font, fill=RED,
              anchor="rs")
    pitch = 18
    top0 = 728
    SEP = (205, 200, 190)
    for col_x, items, col_right in ((274, mid, 638), (650, right, 1012)):
        for i, (sid, region, flag, text) in enumerate(items):
            top = top0 + i * pitch
            draw_flag(draw, col_x, top + 1, flag)
            tx = col_x + 20
            row_limit = col_right - tx
            if ": " in text:
                head, _, tail = text.partition(": ")
                head += ": "
            else:
                head, tail = (text.split(" ", 1)[0] + " ",
                              text.split(" ", 1)[1])
            shown = head + tail
            while (bold.getlength(head) + regular.getlength(tail)
                   > row_limit and len(tail) > 1):
                tail = tail[:-1]
                shown = head + tail + "…"
            draw.text((tx, top + 12), head, font=bold, fill=INK,
                      anchor="ls")
            draw.text((tx + bold.getlength(head), top + 12), tail,
                      font=regular, fill=INK, anchor="ls")
            if shown.endswith("…"):
                draw.text((tx + bold.getlength(head)
                           + regular.getlength(tail), top + 12), "…",
                          font=regular, fill=INK, anchor="ls")
            # Separator below this row (also after the last brief,
            # where it separates the briefs from MARKETS/SPORT).
            draw.line([(col_x, top + 17.7), (col_right, top + 17.7)],
                      fill=SEP, width=1)
    # MARKETS closes the middle column; SPORT closes the right
    # column — as BRIEF-STYLE ROWS (logo + bold head + wrapped
    # text), 12.5px, 18px pitch, with a +2px gap above each row.
    # The segments carry (text, is_red) booleans — convert to real
    # colours here (RED for the negatives, INK otherwise) so the
    # wrap keeps the red negatives red.
    ms_font = inter(12.5, 400)
    ms_bold = inter(12.5, 700)
    # MARKETS: chart icon + bold head + segments, wrapped to 2 lines.
    mk_top = top0 + len(mid) * pitch + 2
    mk_label = "MARKETS: "
    mk_lw = ms_bold.getlength(mk_label)
    mk_segs = [(text, RED if is_red else INK)
               for text, is_red in S.MARKETS_SEGMENTS]
    mk_lines = _wrap_with_head(mk_segs, ms_font,
                               638 - (274 + 20) - mk_lw, 638 - (274 + 20))
    draw_markets_icon(draw, 274, mk_top + 1)
    for li, line in enumerate(mk_lines):
        base = mk_top + li * pitch + 11
        if li == 0:
            draw.text((294, base), mk_label, font=ms_bold, fill=RED,
                      anchor="ls")
            _draw_seg_line(draw, 294 + mk_lw, base, line, ms_font)
        else:
            _draw_seg_line(draw, 294, base, line, ms_font)
    # SPORT: trophy icon + bold head + text, wrapped to 4 lines.
    sp_top = top0 + len(right) * pitch + 2
    sp_label = "SPORT: "
    sp_lw = ms_bold.getlength(sp_label)
    sp_lines = _wrap_with_head([(S.SPORTS_TEXT, INK)], ms_font,
                               1012 - (650 + 20) - sp_lw,
                               1012 - (650 + 20))
    draw_sport_icon(draw, 650, sp_top + 1)
    for li, line in enumerate(sp_lines):
        base = sp_top + li * pitch + 11
        if li == 0:
            draw.text((670, base), sp_label, font=ms_bold, fill=RED,
                      anchor="ls")
            _draw_seg_line(draw, 670 + sp_lw, base, line, ms_font)
        else:
            _draw_seg_line(draw, 670, base, line, ms_font)


def _date_check_segments():
    """Date Check categories parsed from S.DATE_CHECK_LINES, so the
    facts live verbatim in exactly one place (stories.py) and this
    function only re-slices them: (label, pill fill, tint fill,
    [(event, date), ...]). TWO categories only (2026-11-21, user
    order): LEFT OUT 8 items and NOT YET 3 items (expanded
    2026-11-21 — the 5 added items are verified real; see
    stories.py). EDGE is DELETED (it named "Sat 21 Nov" for the
    Peru quake, contradicting the paper's Friday date; the card now
    carries "FRI 19:09 LOCAL" instead). Each item is split on its
    LAST ", " into (event, date) so the renderer can set the event
    in regular INK and the DATE in bold category colour — the date
    is what the reader scans for, so it gets the weight and the
    colour. The split is safe: no event contains a ", " before its
    date. Counts are derived here too (len(items)) so the pill can
    read "LEFT OUT · 8" / "NOT YET · 3" without hard-coding the
    scope."""
    full = " · ".join(S.DATE_CHECK_LINES)
    left = full.split("LEFT OUT: ", 1)[1].split(" · NOT YET: ", 1)[0]
    yet = full.split(" · NOT YET: ", 1)[1]

    def split_items(s):
        return [tuple(it.rsplit(", ", 1)) for it in s.split(" · ")]

    return [
        ("LEFT OUT", RED, (247, 205, 203), split_items(left)),
        ("NOT YET", NAVY, (208, 221, 240), split_items(yet)),
    ]


def _region_counts():
    """Story counts per region, computed from the data (4 leads +
    12 cards + 24 briefs = 40 stories), not hard-coded: Europe 8,
    Middle East 7, North America 6, Latin America 3, Asia 7,
    Africa 4, Global 4, Oceania 1."""
    counts = {}
    for L in S.LEADS:
        counts[L["region"]] = counts.get(L["region"], 0) + 1
    for C in S.CARDS:
        counts[C["region"]] = counts.get(C["region"], 0) + 1
    for (_, region, _, _) in S.BRIEFS:
        counts[region] = counts.get(region, 0) + 1
    return counts


def _region_key_width(show_label=True):
    """Pixel width of the region key at 9px (dot + name + count per
    region, 12px gaps; optional muted "REGIONS" label + 8px gap).
    Used to centre the key before drawing it."""
    lab = inter(9, 800)
    name_f = inter(9, 700)
    num_f = inter(9, 400)
    counts = _region_counts()
    w = lab.getlength("REGIONS") + 8 if show_label else 0
    for region in ("Europe", "Middle East", "North America",
                   "Latin America", "Asia", "Africa", "Global",
                   "Oceania"):
        w += (10 + name_f.getlength(region) + 2
              + num_f.getlength(str(counts[region])) + 12)
    return w - 12


def _region_key(draw, x, base, show_label=True):
    """Region colour key: a coloured dot + region name + story
    count for each of the 8 regions at 9px, with an optional muted
    "REGIONS" label first. The dot (7px) is centred on the text's
    cap height. Drawn on the line at baseline `base`; returns the
    x where the key ends. (2026-11-21: moved OUT of the Date Check
    header to the masthead line — the label is dropped there
    because the masthead already says "8 REGIONS".)"""
    counts = _region_counts()
    lab = inter(9, 800)
    name_f = inter(9, 700)
    num_f = inter(9, 400)
    if show_label:
        draw.text((x, base), "REGIONS", font=lab, fill=DEK, anchor="ls")
        x += lab.getlength("REGIONS") + 8
    for region in ("Europe", "Middle East", "North America",
                   "Latin America", "Asia", "Africa", "Global",
                   "Oceania"):
        draw.ellipse([x, base - 6.5, x + 7, base + 0.5],
                     fill=S.REGION_COLOURS[region])
        x += 10
        draw.text((x, base), region, font=name_f, fill=INK, anchor="ls")
        x += name_f.getlength(region) + 2
        draw.text((x, base), str(counts[region]), font=num_f,
                  fill=INK, anchor="ls")
        x += num_f.getlength(str(counts[region])) + 12
    return x - 12


def draw_date_check_box(draw):
    # DATE CHECK BOX (2026-11-21, reference layout, user order):
    # the full-width strip is gone. The Date Check is now a
    # compact bordered box UNDER THE MAP in the left column
    # (x 12..262, y 840..998), exactly like the reference's box
    # under its map. Same facts/dates, new format: a red header
    # line, then the items as a TWO-COLUMN LIST — event left,
    # date right-aligned — and a "Not yet:" line introducing the
    # 3 NOT YET items. Our graphic style (our red, our fonts,
    # our pale tint fill), the reference's space logic.
    #   * BOX: 12..262 x 840..998, fill (253, 243, 238), red
    #     1.5px outline. Inner text x 18..256 (6px padding).
    #   * HEADER (10.5px bold RED, baseline 852): "DATE CHECK ·
    #     LEFT OUT AS OLDER NEWS" (215.8px, fits the 238px inner
    #     width).
    #   * 7 LEFT OUT rows, 10.5px, 12.5px pitch (baselines
    #     864..939, reflowed 2026-11-21 after the Kenya row was
    #     deleted): event regular INK, date bold RED,
    #     right-aligned at x=256. Longest row 230.7px
    #     (BepiColombo is a NOT YET row) — LEFT OUT max 206.4px.
    #   * "Not yet:" subhead (10.5px bold NAVY, baseline 951.5),
    #     then 3 NOT YET rows (baselines 964/976.5/989):
    #     event regular INK, date bold NAVY, right-aligned.
    #     Longest NOT YET row 230.7px (BepiColombo) — fits the
    #     238px inner width with 7.3px spare. 10.5px (not 11px):
    #     at 11px BepiColombo is 241.7px and would collide with
    #     the right-aligned date.
    #   * Last row descenders ~993, 5px clear of the box bottom
    #     (998); header caps ~844.6, 4.6px clear of the box top.
    draw.rectangle([12, 840, 262, 998], fill=(253, 243, 238),
                   outline=RED, width=1.5)
    dc_font = inter(10.5, 400)
    dc_bold = inter(10.5, 700)
    draw.text((18, 852), "DATE CHECK · LEFT OUT AS OLDER NEWS",
              font=inter(10.5, 800), fill=RED, anchor="ls")
    segs = _date_check_segments()
    left_items = segs[0][3]
    yet_items = segs[1][3]
    # REFLOW (2026-11-21, Kenya deleted — 7 LEFT OUT rows now):
    # the rows are laid out from the item counts at 12.5px pitch,
    # so the box fills evenly: 7 LEFT OUT rows (864..939),
    # "Not yet:" (951.5), 3 NOT YET rows (964..989). Last row
    # descenders ~992, 6px clear of the box bottom (998). Longest
    # row 230.7px (BepiColombo) — fits the 238px inner width with
    # 7.3px spare. 10.5px (not 11px): at 11px BepiColombo is
    # 241.7px and would collide with the right-aligned date.
    pitch = 12.5
    base = 864
    for event, date in left_items:
        draw.text((18, base), event + ", ", font=dc_font, fill=INK,
                  anchor="ls")
        draw.text((256, base), date, font=dc_bold, fill=RED,
                  anchor="rs")
        base += pitch
    # "Not yet:" subhead (navy bold), then the 3 NOT YET rows.
    draw.text((18, base), "Not yet:", font=dc_bold, fill=NAVY,
              anchor="ls")
    base += pitch
    for event, date in yet_items:
        draw.text((18, base), event + ", ", font=dc_font, fill=INK,
                  anchor="ls")
        draw.text((256, base), date, font=dc_bold, fill=NAVY,
                  anchor="rs")
        base += pitch


def draw_bottom_strip(draw):
    # BOTTOM SECTION, REFERENCE LAYOUT (2026-11-21): three
    # columns under the cards. The left column (x 12..262) is the
    # map (drawn by draw_map, tile 726..834) + the Date Check box
    # (840..998, draw_date_check_box above). The middle and right
    # columns are the briefs (draw_briefs, headers at baseline
    # 722). The full-width Date Check strip (911..968) and the
    # Markets/Sport bar (970..998) are DELETED — Markets/Sport
    # now close the briefs columns as wrapped lines. Only the
    # "WHERE IT HAPPENED" header and the footer survive here.
    #   card row 2 ends 705; header caps ~713 (gap 8)
    #   map tile 726..834; Date Check box 840..998 (gap 6)
    #   briefs rows 728..~996; footer rule 1001 (gap ~5)
    #   footer caps ~1007 (gap ~6); footer descenders ~1016,
    #   3px clear of the outer border (1019), 8px off the page edge.
    draw.text((12, 722), "WHERE IT HAPPENED", font=inter(12, 800),
              fill=RED, anchor="ls")
    draw_date_check_box(draw)
    # FOOTER: the legend line is no longer a bare centred line under
    # SPORT. A 2px divider rule in dark warm grey (64, 60, 50) sits
    # 3px below the bottom section, and the 9.5px muted footer sits
    # 4px below the rule — smaller than every content line
    # (11.5/12px), separated on both sides, reading as a footer.
    # The rule is deliberately BOLDER and DARKER than the line below
    # the footer text — the 1px (90, 85, 75) bottom page border,
    # which stays as-is — so the footer is fenced off from the bar
    # above, not from the page edge below.
    # FIT (2026-11-21): adding "Unmarked = confirmed." (+109.4px at
    # 9.5px) to the old 995.0px line would overflow the 1000px content
    # width, so the type is 10 -> 9.5px (the max allowed cut) and the
    # tail is shortened: "and others" dropped from the sources list
    # and the filler "here" dropped from the opening sentence. No
    # legend item, source name, fact or date was dropped. Measured
    # 981.1px at 9.5px, centred span 21.5..1002.5 — 9.5px clear of
    # the 12..1012 content edges on both sides, still one line.
    draw.line([12, 1001, 1012, 1001], fill=(64, 60, 50), width=2)
    draw.text((512, 1013.5), S.FOOTER_TEXT, font=inter(9.5, 400), fill=MUTED,
              anchor="ms")



# ------------------------------------------------------------------- build

def build():
    img = Image.new("RGB", (W * SS, H * SS), PAPER)
    draw = SSDraw(ImageDraw.Draw(img), img)
    draw.rectangle([5, 5, 1019, 1019], outline=(90, 85, 75), width=1)
    draw_masthead(draw)
    draw_timeline(draw)
    # VERTICAL BUDGET, REFERENCE LAYOUT (2026-11-21): masthead
    # descender ~87; timeline band ~91..144 (below-label
    # descenders ~144, 4px clear of the leads); leads 148..381
    # (233px); cards row1 389..543, row2 551..705 (154px each,
    # 8px gaps); bottom headers baseline 722 (caps ~713, 8px
    # clear of the cards); bottom section 726..998 (map tile
    # 726..834, Date Check box 840..998, briefs rows 730..~995);
    # footer rule 1001, footer baseline 1013.5, border 1019.
    for lead, x in zip(S.LEADS, (12, 264, 516, 768)):
        draw_lead(draw, img, lead, x, 148)
    row1 = S.CARDS[0:6]
    row2 = S.CARDS[6:12]
    for card, x in zip(row1, (12, 180, 348, 516, 684, 852)):
        draw_card(img, draw, card, x, 389)
    for card, x in zip(row2, (12, 180, 348, 516, 684, 852)):
        draw_card(img, draw, card, x, 551)
    draw_bottom_strip(draw)
    draw_map(img, draw)
    draw_briefs(draw)
    return img.resize((W, H), Image.BOX)


def main():
    out = HERE / "entry.png"
    build().save(out, format="PNG", optimize=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
