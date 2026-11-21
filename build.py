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
    # MASTHEAD, LIGHTER + SHORTER (2026-11-21, user order): the title
    # is 68px SemiBold (was 80px Black) — a weight change, not just
    # a size change — and moved down 2px (y=7) so its caps stay clear
    # of the kicker above (at 68px the caps rise ~2px higher than at
    # 80px; the kicker's ink ends ~y=17, the caps start ~y=18).
    # The 'y' descender now ends ~y=91 (was 103): the masthead band
    # (top border to timeline caps) shrinks 105px -> ~90px, ~15%.
    # The ~15px freed goes to the briefs below (draw_briefs rows
    # 13.0 -> 17.5px, round 5) via the whole middle of the page
    # shifting up 15px (see build()).
    draw.text((12, 6), "THE DAY IN WORLD NEWS", font=inter(12, 800),
              fill=RED, anchor="la")
    draw.text((1012, 6), "46 STORIES · 7 REGIONS · ALL FROM THIS FRIDAY",
              font=inter(10.5, 700), fill=DEK, anchor="ra")
    size = 68
    while size >= 68:
        font = title_font(size)
        if font.getlength("Friday 20 November 2026") <= 1000:
            break
        size -= 2
    draw.text((12, 7), "Friday 20 November 2026",
              font=title_font(size), fill=(20, 20, 20), anchor="la")


def draw_timeline(draw):
    # REGION BAR REMOVED (2026-11-21): the coloured segmented bar
    # that sat at y=106..122 is gone entirely — no bar, no labels,
    # no gap left behind. The 18px it freed (16px bar + 2px gap
    # below it) is split: ~10px to this timeline (taller band, bigger
    # type and dots) and ~8px to the lower section (leads/cards shift
    # up 8px; the bottom block spreads the rest — see draw_briefs /
    # draw_bottom_strip). Masthead still says "46 STORIES · 7 REGIONS".
    # REDESIGN (2026-11-21, round 3): modern stem-and-rule connectors,
    # colour-coded by region. Every dot is its event's region colour
    # (was uniform masthead red for all seven); every label's time is
    # the same region colour (was uniform red); and every dot is
    # visibly joined to its label — no floating labels:
    #   above the line: a 2px region-coloured vertical stem rises from
    #     the dot to a 2px region-coloured rule that runs UNDER the
    #     whole label (the rule starts/ends at the dot's x for the
    #     displaced left/right labels, so stem + rule form one
    #     continuous elbow); the stem meets the rule at the label's
    #     centre for centred labels.
    #   below the line: a 2px region-coloured vertical stem drops from
    #     the dot to 1px above the label's cap-top. No rule under
    #     below-labels: a rule there would strike through the hour
    #     labels. The only below-label left is 02:30 (its stem at
    #     x=184 clears the nearest axis label, "00:00", by ~79px).
    #   AXIS LABELS (2026-11-21): numbers only on 00/06/12/18/24.
    #     The 03/09/15/21 labels were removed — they collided with
    #     event labels (02:30 vs "03:00", 11:30 vs "12:00", 20:00 vs
    #     "21:00"). All 25 hourly tick marks stay on the ruler;
    #     only the NUMBER labels were reduced.
    #   EVENTS (2026-11-21): 5, down from 7 — 11:30 UK-EU deals and
    #     20:00 Palisades verdict markers dropped (weakest news
    #     weight; each decluttered the tightest pair). Their stories
    #     stay in the paper; only the markers are gone.
    # Geometry (2026-11-21: whole band shifted up 15px to absorb the
    # masthead's freed space; band caps ~95 .. descenders ~157, 62px
    # vs 61px before; lead row now starts at y=161):
    #   above-event labels, baseline 104 (caps start ~95, ~5px clear
    #     of the title descender at ~91); connector rule y=107..109;
    #     stem y=109..115
    #   ruler line y=121..124 (3px), dots centred on y=122.5,
    #     14px diameter (7px white halo / 6px colour centre)
    #   hour ticks below the line, hour labels (every 6h, 10px)
    #     baseline 141
    #   below-event labels, baseline 153 (descenders to ~157, 4px
    #     clear of the lead row at 161); stem y=130..143
    # Event type is 12px. Times, x positions, anchors and label
    # strings are unchanged — only the band's vertical position.
    draw.text((12, 119), "THE DAY", font=inter(12, 800), fill=RED,
              anchor="ls")
    draw.text((12, 132), "IN UTC", font=inter(12, 800), fill=RED,
              anchor="ls")
    draw.rectangle([88, 121, 1012, 124], fill=INK)
    hour_font = inter(10, 700)
    for hour in range(25):
        x = 88 + hour * 38.5
        if hour % 6 == 0:
            # Axis NUMBER labels only on 00/06/12/18/24 (2026-11-21):
            # the 03/09/15/21 labels collided with event labels.
            # Tick marks stay hourly (long tick every 3h, short else).
            draw.rectangle([x - 1, 125, x + 1, 131], fill=INK)
            label = "%02d:00" % hour
            cx = min(max(x, 88 + hour_font.getlength(label) / 2),
                     1012 - hour_font.getlength(label) / 2)
            draw.text((cx, 141), label, font=hour_font, fill=DEK,
                      anchor="ms")
        else:
            draw.rectangle([x, 125, x, 128], fill=MUTED)
    time_font = inter(12, 800)
    label_font = inter(12, 700)
    space = label_font.getlength(" ")
    for time, x, label, above, anchor, region in S.TIMELINE:
        colour = S.REGION_COLOURS[region]
        draw.ellipse([x - 7, 115.5, x + 7, 129.5],
                     fill=(255, 255, 255))
        draw.ellipse([x - 6, 116.5, x + 6, 128.5], fill=colour)
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
            draw.rectangle([rx0, 107, rx1, 109], fill=colour)
            draw.rectangle([x - 1, 109, x, 115], fill=colour)
            base = 104
        else:
            # Stem drops from the dot to 1px above the label caps.
            draw.rectangle([x - 1, 130, x, 143], fill=colour)
            base = 153
        draw.text((lx, base), time, font=time_font, fill=colour,
                  anchor="ls")
        draw.text((lx + time_font.getlength(time) + space, base), label,
                  font=label_font, fill=INK, anchor="ls")


# ------------------------------------------------------- lead illustrations
# ILLUSTRATION ROUND (2026-11-21): every lead redrawn around ONE
# big focal idea that reads at a glance — bigger map / bigger
# bursts / a second plunging market line / the struck draft as
# the hero — flat graphic shapes in the paper palette only.

def lead_art_1(draw, x, y0):
    """Poland — BEFORE: pale washed-out map, two thin dashed red
    trails, two small bursts. AFTER: a stronger blue field, a big
    cream Poland map with a thick red EASTERN BORDER, two THICK
    solid red missile trails (not dashed) streaking in from the
    east, each ending in a LARGE layered impact burst, and a bold
    red "2" badge — two missiles, two hits, at first glance."""
    draw.rectangle([x, y0, x + 244, y0 + 80], fill=(205, 220, 238))
    land = [(x + 10, y0 + 26), (x + 55, y0 + 12), (x + 115, y0 + 10),
            (x + 175, y0 + 16), (x + 225, y0 + 24), (x + 234, y0 + 46),
            (x + 208, y0 + 66), (x + 150, y0 + 74), (x + 90, y0 + 76),
            (x + 38, y0 + 68), (x + 12, y0 + 48)]
    draw.polygon(land, fill=(240, 232, 205), outline=(90, 85, 75))
    # Eastern border: a thick red line along the map's east edge.
    draw.line([(x + 214, y0 + 20), (x + 226, y0 + 26),
               (x + 232, y0 + 46), (x + 218, y0 + 60)],
              fill=RED, width=3, joint="curve")
    # Two thick solid missile trails from the east edge.
    for (x1, y1, x2, y2) in [(244, 16, 188, 36), (244, 46, 200, 58)]:
        draw.line([(x + x1, y0 + y1), (x + x2, y0 + y2)], fill=RED,
                  width=4)
        draw.line([(x + x1, y0 + y1), (x + x2, y0 + y2)],
                  fill=(255, 120, 90), width=2)
    # Large layered impact bursts with radiating ticks.
    for bx, by, r in [(188, 36, 18), (200, 58, 15)]:
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            draw.line([x + bx + (r + 2) * math.cos(a),
                       y0 + by + (r + 2) * math.sin(a),
                       x + bx + (r + 7) * math.cos(a),
                       y0 + by + (r + 7) * math.sin(a)],
                      fill=(255, 150, 40), width=2)
        star(draw, x + bx, y0 + by, r, r // 3 + 1, (255, 190, 40))
        star(draw, x + bx, y0 + by, r * 2 // 3, 3, (255, 120, 40))
        star(draw, x + bx, y0 + by, r // 2, 2, RED)
    # Bold "2" badge: two missiles.
    draw.ellipse([x + 4, y0 + 4, x + 26, y0 + 26], fill=RED,
                 outline=(255, 255, 255), width=2)
    draw.text((x + 15, y0 + 15), "2", font=inter(14, 800),
              fill=(255, 255, 255), anchor="mm")
    draw.text((x + 32, y0 + 15), "POLAND", font=inter(10, 800),
              fill=INK, anchor="lm")
    draw.text((x + 240, y0 + 6), "EASTERN BORDER", font=inter(8, 700),
              fill=DEK, anchor="ra")


def lead_art_2(draw, x, y0):
    """Kyiv — BEFORE: thin dark bridge, two small bursts, a sparse
    drone swarm. AFTER: the bridge deck is BROKEN at the impact
    point — a visible gap with a huge fireball, smoke and river
    reflections — so the hit reads instantly; a denser drone
    swarm overhead. First glance: a bridge broken and burning
    at night."""
    draw.rectangle([x, y0, x + 244, y0 + 80], fill=(24, 32, 58))
    draw.rectangle([x, y0 + 56, x + 244, y0 + 80], fill=(36, 52, 92))
    # Bridge deck, broken at the impact point (x+108..x+136).
    draw.rectangle([x + 8, y0 + 44, x + 108, y0 + 52], fill=(16, 20, 38))
    draw.rectangle([x + 136, y0 + 44, x + 236, y0 + 52],
                   fill=(16, 20, 38))
    # Arch supports under each deck segment.
    draw.arc([x + 30, y0 + 44, x + 96, y0 + 80], 180, 360,
             fill=(16, 20, 38), width=3)
    draw.arc([x + 148, y0 + 44, x + 214, y0 + 80], 180, 360,
             fill=(16, 20, 38), width=3)
    # Smoke plume rising from the gap.
    for sx, sy, sr in [(122, 30, 6), (118, 22, 5), (126, 14, 4)]:
        draw.ellipse([x + sx - sr, y0 + sy - sr, x + sx + sr,
                      y0 + sy + sr], fill=(110, 110, 125))
    # Huge fireball at the gap, with radiating ticks.
    bx, by = 122, 48
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        draw.line([x + bx + 19 * math.cos(a), y0 + by + 19 * math.sin(a),
                   x + bx + 25 * math.cos(a), y0 + by + 25 * math.sin(a)],
                  fill=(255, 150, 40), width=2)
    star(draw, x + bx, y0 + by, 18, 5, (255, 150, 40))
    star(draw, x + bx, y0 + by, 12, 4, (255, 210, 80))
    star(draw, x + bx, y0 + by, 6, 2, RED)
    # Smaller burst on the left deck.
    star(draw, x + 58, y0 + 40, 10, 3, (255, 150, 40))
    star(draw, x + 58, y0 + 40, 6, 2, (255, 210, 80))
    # River reflections under the fireball.
    for rx in (114, 122, 130):
        draw.line([x + rx, y0 + 58, x + rx, y0 + 74],
                  fill=(255, 150, 40), width=2)
    # Denser drone swarm (8), clear of the "KYIV 00:30" label.
    for dx, dy in [(95, 14), (110, 26), (130, 8), (148, 22),
                   (165, 16), (180, 26), (195, 9), (222, 18)]:
        draw.line([x + dx - 13, y0 + dy + 2, x + dx - 3, y0 + dy],
                  fill=(176, 32, 32), width=1)
        draw.ellipse([x + dx - 2, y0 + dy - 2, x + dx + 2, y0 + dy + 2],
                     fill=(255, 255, 255))
    draw.text((x + 10, y0 + 8), "KYIV 00:30", font=inter(10, 800),
              fill=(255, 255, 255), anchor="la")


def lead_art_4(draw, x, y0):
    """COP31 — BEFORE: small globe, thin thermometer, a small doc
    whose "FOSSIL FUELS" has only a thin strike line. AFTER: a
    bigger globe and a thermometer filled HIGH, and a LARGE
    document whose "FOSSIL FUELS" is crossed by a THICK red X
    (not a thin line) with a red "DROPPED" stamp — the draft
    dropping fossil fuels, at first glance."""
    draw.rectangle([x, y0, x + 244, y0 + 80], fill=(242, 236, 220))
    # Bigger globe.
    draw.ellipse([x + 6, y0 + 10, x + 70, y0 + 70], fill=(70, 130, 180))
    draw.ellipse([x + 16, y0 + 20, x + 36, y0 + 38], fill=(90, 170, 90))
    draw.ellipse([x + 40, y0 + 44, x + 58, y0 + 60], fill=(90, 170, 90))
    # Thermometer, mercury filled high (overheating).
    draw.rounded_rectangle([x + 76, y0 + 10, x + 88, y0 + 52],
                           radius=5, fill=(255, 255, 255),
                           outline=RED, width=1)
    draw.rectangle([x + 78, y0 + 22, x + 86, y0 + 50], fill=RED)
    draw.ellipse([x + 73, y0 + 50, x + 91, y0 + 68], fill=RED)
    # Large document.
    draw.rectangle([x + 98, y0 + 6, x + 240, y0 + 72], fill=PANEL,
                   outline=(180, 175, 165))
    draw.text((x + 169, y0 + 14), "DRAFT DEAL", font=inter(8, 800),
              fill=MUTED, anchor="ma")
    draw.text((x + 169, y0 + 34), "FOSSIL FUELS", font=inter(13, 800),
              fill=INK, anchor="mm")
    # Thick red X over FOSSIL FUELS (text spans ~x+119..x+219).
    draw.line([x + 117, y0 + 26, x + 221, y0 + 42], fill=RED, width=3)
    draw.line([x + 221, y0 + 26, x + 117, y0 + 42], fill=RED, width=3)
    draw.text((x + 169, y0 + 52), "$120bn", font=inter(11, 800),
              fill=INK, anchor="mm")
    draw.line([x + 146, y0 + 52, x + 192, y0 + 52], fill=RED, width=2)
    # DROPPED stamp inside the document.
    draw.rectangle([x + 138, y0 + 58, x + 200, y0 + 70], outline=RED,
                   width=2)
    draw.text((x + 169, y0 + 64), "DROPPED", font=inter(8, 800),
              fill=RED, anchor="mm")
    draw.text((x + 240, y0 + 78), "OVERTIME", font=inter(9, 800),
              fill=RED, anchor="ra")


LEAD_ART = {1: lead_art_1, 2: lead_art_2, 4: lead_art_4}


def draw_lead(draw, img, lead, x, y0):
    """One lead card; lead 3 is the dark-navy anchor."""
    w = 244
    region = S.REGION_COLOURS[lead["region"]]
    if lead["id"] == 3:
        # DESIGN (user order): navy is LIMITED to the top illustration
        # band (y0..y0+80) — the rest of the card is the standard white
        # panel, so the headline, dek, badge and source sit on white
        # like the other leads. The band ALSO carries the same thin
        # region-coloured top rule as the other leads (N. America
        # green, 3px at the very top, over the navy) — the navy band
        # is the card's identifier, the green rule is its region
        # marker, matching cards 1, 2 and 4. "-3.7%" stays 44px white
        # on navy — still the boldest element on the page.
        draw.rectangle([x, y0, x + w, y0 + 240], fill=PANEL,
                       outline=PANEL_BORDER)
        draw.rectangle([x, y0, x + w, y0 + 80], fill=NAVY2)
        draw.rectangle([x, y0, x + w, y0 + 3], fill=region)
        draw.text((x + 10, y0 + 48), "-3.7%", font=merr(44, 900),
                  fill=(255, 255, 255), anchor="ls")
        draw.text((x + 10, y0 + 70), "S&P 500 · 6,910",
                  font=inter(13, 700), fill=ANCHOR_YELLOW, anchor="ls")
        # CHART (illustration rebuild 2026-11-21): faint gridlines,
        # a bold red falling line with the area beneath it filled
        # dark red, a steeper orange Nasdaq line (-5.3% in the dek),
        # a red arrowhead at the S&P line's end — the fall, not just
        # the number, is the art.
        for gy in (20, 40, 60):
            draw.line([(x + 148, y0 + gy), (x + 240, y0 + gy)],
                      fill=(55, 70, 115), width=1)
        sp = [(x + 150, y0 + 12), (x + 176, y0 + 26),
              (x + 204, y0 + 46), (x + 228, y0 + 64)]
        draw.polygon(sp + [(x + 228, y0 + 74), (x + 150, y0 + 74)],
                     fill=(140, 40, 60))
        draw.line([(x + 150, y0 + 16), (x + 178, y0 + 30),
                   (x + 206, y0 + 42), (x + 234, y0 + 64)],
                  fill=(255, 150, 40), width=2, joint="curve")
        draw.line(sp, fill=ANCHOR_RED, width=3, joint="curve")
        draw.polygon([(x + 232, y0 + 68), (x + 220, y0 + 61),
                      (x + 223, y0 + 70)], fill=ANCHOR_RED)
        for px, py in sp[1:]:
            draw.ellipse([px - 3, py - 3, px + 3, py + 3],
                         fill=(255, 255, 255))
        tag = "CORRECTION"
        tag_font = inter(9, 800)
        tag_w = tag_font.getlength(tag) + 10
        draw.rectangle([x + w - tag_w - 6, y0 + 6,
                        x + w - 6, y0 + 20], fill=(200, 40, 30))
        draw.text((x + w - 6 - tag_w / 2, y0 + 13), tag, font=tag_font,
                  fill=(255, 255, 255), anchor="mm")
        kick_fill, kick_num = region, (255, 255, 255)
        kick_colour, head_colour, dek_colour = region, INK, DEK
        src_colour = MUTED
    else:
        draw.rectangle([x, y0, x + w, y0 + 240], fill=PANEL,
                       outline=PANEL_BORDER)
        LEAD_ART[lead["id"]](draw, x, y0)
        draw.rectangle([x, y0, x + w, y0 + 3], fill=region)
        kick_fill, kick_num = region, (255, 255, 255)
        kick_colour, head_colour, dek_colour = region, INK, DEK
        src_colour = MUTED
    cy = y0 + 90
    number_circle(draw, x + 8 + 6.5, cy, 13, kick_fill, lead["id"], 9,
                  text_fill=kick_num)
    draw.text((x + 26, y0 + 97), lead["kicker"], font=inter(10.5, 800),
              fill=kick_colour, anchor="ls")
    font, lines, leading = fit_headline(
        lead["headline"], [(28, 31), (26, 29), (24, 27)], 228)
    ty = y0 + 101
    for line in lines:
        draw.text((x + 8, ty), line, font=font, fill=head_colour, anchor="la")
        ty += leading
    dek_font, dek_lines = fit_dek(lead["dek"], 228, base=11)
    ty = y0 + 197
    for line in dek_lines:
        draw.text((x + 8, ty), line, font=dek_font, fill=dek_colour,
                  anchor="la")
        ty += dek_font.size + 2.5
    badge(draw, x + 8, y0 + 227, lead["status"], 12, 9)
    draw.text((x + w - 8, y0 + 238), lead["source"].upper(),
              font=inter(9.5, 700), fill=src_colour, anchor="rs")


# ------------------------------------------------------ medium illustrations
# ILLUSTRATION ROUND (2026-11-21): every card redrawn around ONE
# big focal idea that reads at a glance — a hero number, a hero
# stamp, a giant spike, a broken line — flat graphic shapes in
# the paper palette only. Card 11's in-art label changes
# "1 IN 12" -> "61 PATIENTS": the trial size straight from the
# dek; "1 IN 12" appears in no source for this story.

def card_art_5(draw, x, y0):
    """UK-EU — BEFORE: small flags, a thin teal link, a modest "3"
    in a circle. AFTER: BIGGER flags (32x20), a THICK teal bridge
    (4px) joining them, and a LARGE red "3" seal (r=13, 18px) that
    overlaps the bridge like a wax seal, "DEALS" beneath. First
    glance: UK + EU + 3 deals."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(226, 232, 240))
    draw.line([x + 6, y0 + 6, x + 6, y0 + 40], fill=(90, 85, 75), width=2)
    draw.line([x + 154, y0 + 6, x + 154, y0 + 40], fill=(90, 85, 75),
              width=2)
    draw.paste(_flag_image("GB", 32, 20), (x + 8, y0 + 8))
    _flag_outline(draw, x + 8, y0 + 8, "GB", 32, 20)
    draw.rectangle([x + 122, y0 + 8, x + 152, y0 + 28],
                   fill=(0, 51, 153))
    for i in range(12):
        a = 2 * math.pi * i / 12
        draw.ellipse([x + 137 + 10 * math.cos(a) - 1,
                      y0 + 18 + 7 * math.sin(a) - 1,
                      x + 137 + 10 * math.cos(a) + 1,
                      y0 + 18 + 7 * math.sin(a) + 1],
                     fill=(255, 204, 0))
    draw.line([x + 42, y0 + 20, x + 120, y0 + 20], fill=(14, 124, 123),
              width=4)
    draw.ellipse([x + 67, y0 + 7, x + 93, y0 + 33], fill=RED,
                 outline=(255, 255, 255), width=2)
    draw.text((x + 80, y0 + 20), "3", font=inter(18, 800), fill=(255, 255, 255),
              anchor="mm")
    draw.text((x + 80, y0 + 41), "DEALS", font=inter(7, 800), fill=INK,
              anchor="ma")


def card_art_6(draw, x, y0):
    """UN chief race — BEFORE: a thin assembly arc, a small ballot
    box with a small X, a "9TH VOTE" chip. AFTER: NINE ballot
    slips in a row along the bottom — the first eight plain, the
    NINTH one crossed out with a big red X — the ninth vote was
    vetoed. The arc stays as a backdrop, the "9TH VOTE" chip
    stays top-right. First glance: nine votes, the ninth vetoed."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(238, 236, 228))
    draw.arc([x + 20, y0 + 2, x + 92, y0 + 24], 180, 360,
             fill=(150, 110, 70), width=4)
    for i in range(9):
        a = math.pi + math.pi * i / 8
        sx, sy = x + 56 + 36 * math.cos(a), y0 + 13 + 11 * math.sin(a)
        draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(60, 50, 40))
    draw.rectangle([x + 100, y0 + 4, x + 156, y0 + 18], fill=RED)
    draw.text((x + 128, y0 + 11), "9TH VOTE", font=inter(9, 800),
              fill=(255, 255, 255), anchor="mm")
    for i in range(9):
        sx = x + 6 + i * 17
        draw.rectangle([sx, y0 + 24, sx + 15, y0 + 42],
                       fill=(255, 255, 255), outline=(120, 115, 105))
        draw.line([sx + 3, y0 + 30, sx + 12, y0 + 30],
                  fill=(150, 145, 135), width=1)
        draw.line([sx + 3, y0 + 35, sx + 12, y0 + 35],
                  fill=(150, 145, 135), width=1)
    # The ninth slip (rightmost) is crossed out in red.
    sx = x + 6 + 8 * 17
    draw.line([sx + 2, y0 + 26, sx + 13, y0 + 40], fill=RED, width=3)
    draw.line([sx + 13, y0 + 26, sx + 2, y0 + 40], fill=RED, width=3)


def card_art_7(draw, x, y0):
    """Iran war — BEFORE: a small calendar with a 22px "9", a small
    tanker, plain red "UNTIL 2027" text. AFTER: a LARGE calendar
    page (60x38) with a HUGE "9" (30px), a bigger tanker on a
    wider sea band, and "UNTIL 2027" as a bold red chip with
    white text. First glance: month 9, no decision until 2027."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(210, 226, 238))
    draw.rectangle([x + 4, y0 + 4, x + 64, y0 + 42], fill=(255, 255, 255),
                   outline=(90, 85, 75))
    draw.rectangle([x + 4, y0 + 4, x + 64, y0 + 14], fill=RED)
    draw.text((x + 34, y0 + 9), "MONTH", font=inter(8, 800),
              fill=(255, 255, 255), anchor="mm")
    draw.text((x + 34, y0 + 30), "9", font=inter(30, 800), fill=NAVY,
              anchor="mm")
    draw.rectangle([x + 68, y0 + 28, x + 160, y0 + 46], fill=(36, 70, 110))
    draw.polygon([(x + 86, y0 + 30), (x + 140, y0 + 30), (x + 134, y0 + 38),
                  (x + 86, y0 + 38)], fill=(30, 30, 35))
    draw.rectangle([x + 100, y0 + 24, x + 116, y0 + 30], fill=(30, 30, 35))
    star(draw, x + 94, y0 + 20, 7, 3, (255, 150, 40))
    draw.rectangle([x + 104, y0 + 6, x + 156, y0 + 18], fill=RED)
    draw.text((x + 130, y0 + 12), "UNTIL 2027", font=inter(8, 800),
              fill=(255, 255, 255), anchor="mm")


def card_art_8(draw, x, y0):
    """Hodeidah — BEFORE: a small burst, thin cranes, three red x
    marks (the dek says FIVE drones were intercepted). AFTER: a
    dusk sky, a HUGE layered burst (r=18) as the hero, thicker
    crane silhouettes, a bigger ship, and FIVE red x marks — one
    per intercepted drone. First glance: an explosion at a port."""
    draw.rectangle([x, y0, x + 160, y0 + 30], fill=(235, 190, 130))
    draw.rectangle([x, y0 + 30, x + 160, y0 + 46], fill=(40, 70, 110))
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        draw.line([x + 52 + 20 * math.cos(a), y0 + 20 + 20 * math.sin(a),
                   x + 52 + 26 * math.cos(a), y0 + 20 + 26 * math.sin(a)],
                  fill=(255, 150, 40), width=2)
    star(draw, x + 52, y0 + 20, 18, 5, (255, 190, 40))
    star(draw, x + 52, y0 + 20, 12, 4, (255, 120, 40))
    star(draw, x + 52, y0 + 20, 7, 2, RED)
    for cx in (96, 140):
        draw.line([x + cx, y0 + 4, x + cx, y0 + 30], fill=(40, 35, 30),
                  width=3)
        draw.line([x + cx - 6, y0 + 8, x + cx + 16, y0 + 8],
                  fill=(40, 35, 30), width=2)
        draw.line([x + cx, y0 + 4, x + cx + 16, y0 + 8],
                  fill=(40, 35, 30), width=1)
        draw.line([x + cx + 12, y0 + 8, x + cx + 12, y0 + 20],
                  fill=(40, 35, 30), width=1)
        draw.rectangle([x + cx + 10, y0 + 20, x + cx + 14, y0 + 23],
                       fill=(40, 35, 30))
    draw.polygon([(x + 92, y0 + 32), (x + 146, y0 + 32), (x + 140, y0 + 42),
                  (x + 92, y0 + 42)], fill=(20, 25, 35))
    draw.rectangle([x + 102, y0 + 26, x + 116, y0 + 32], fill=(20, 25, 35))
    draw.rectangle([x + 122, y0 + 27, x + 134, y0 + 32], fill=RED)
    # Five intercepted drones: five red x marks.
    for dx, dy in [(18, 8), (78, 6), (118, 8), (130, 6), (152, 18)]:
        draw.text((x + dx, y0 + dy), "×", font=inter(9, 800), fill=RED,
                  anchor="mm")


def card_art_9(draw, x, y0):
    """Peru quake — BEFORE: a thin red seismograph trace, a 20px
    "6.7", flat Andes. AFTER: a THICK red trace (width 4) with a
    HUGE central spike that nearly touches the top of the band,
    bolder Andes, and "6.7" at 24px — the spike IS the story.
    The dark "SAT 00:09 UTC" chip is kept exactly (user order)."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(240, 236, 224))
    for bx, bw, bh in [(4, 56, 14), (56, 54, 18), (106, 50, 12)]:
        draw.polygon([(x + bx, y0 + 46), (x + bx + bw / 2, y0 + 46 - bh),
                      (x + bx + bw, y0 + 46)], fill=(150, 110, 70))
    # The trace starts right of the 6.7, so it never crosses the
    # number; the peak (x+76, y0+4) stays left of the SAT chip
    # (x+87..x+154, y0+6..y0+18) and the descent clears its bottom.
    pts = [(x + 54, y0 + 30), (x + 66, y0 + 24),
           (x + 76, y0 + 4), (x + 88, y0 + 28),
           (x + 102, y0 + 20), (x + 124, y0 + 24), (x + 154, y0 + 24)]
    draw.line(pts, fill=RED, width=4, joint="curve")
    draw.text((x + 8, y0 + 4), "6.7", font=merr(24, 900), fill=RED,
              anchor="la")
    # UTC-DATE TAG (2026-11-21, option (b) MARKING): the quake was
    # 19:09 local Fri 20 Nov = 00:09 UTC Sat 21 Nov, but this paper
    # is Friday 20 Nov and the timeline is "THE DAY IN UTC" — so the
    # Saturday-UTC timing is marked visibly and deliberately on the
    # card itself (the Date Check EDGE item explains it too).
    draw.rectangle([x + 87, y0 + 6, x + 154, y0 + 18], fill=INK)
    draw.text((x + 120.5, y0 + 12), "SAT 00:09 UTC", font=inter(7.5, 800),
              fill=(255, 255, 255), anchor="mm")


def card_art_10(img, draw, x, y0):
    """Palisades Fire — BEFORE: a modest gradient, small flames, a
    small 9px GUILTY stamp. AFTER: a darker smoky sky, TALLER
    flames (up to 30px) licking from a bigger house, and a LARGE
    white-backed GUILTY stamp (12px) as the verdict, front and
    centre. First glance: a fire, and a guilty verdict."""
    for row in range(46 * SS):
        t = row / (46 * SS - 1)
        r = int(160 + (235 - 160) * t)
        g = int(50 + (150 - 50) * t)
        b = int(30 + (50 - 30) * t)
        draw.line([x, y0 + row / SS, x + 160, y0 + row / SS],
                  fill=(r, g, b))
    draw.polygon([(x, y0 + 46), (x, y0 + 30), (x + 60, y0 + 22),
                  (x + 120, y0 + 32), (x + 160, y0 + 26), (x + 160, y0 + 46)],
                 fill=(40, 25, 20))
    draw.rectangle([x + 98, y0 + 28, x + 120, y0 + 38], fill=(30, 20, 15))
    draw.polygon([(x + 96, y0 + 28), (x + 122, y0 + 28), (x + 109, y0 + 16)],
                 fill=(30, 20, 15))
    for fx, fh in [(102, 30), (116, 26), (130, 22), (146, 16), (88, 18)]:
        draw.polygon([(x + fx - 7, y0 + 36), (x + fx, y0 + 36 - fh),
                      (x + fx + 7, y0 + 36)], fill=(255, 170, 40))
        draw.polygon([(x + fx - 3, y0 + 36), (x + fx, y0 + 36 - fh + 10),
                      (x + fx + 3, y0 + 36)], fill=(255, 220, 80))
    draw.rectangle([x + 8, y0 + 30, x + 22, y0 + 36], fill=(90, 60, 40))
    draw.line([x + 15, y0 + 30, x + 15, y0 + 22], fill=(90, 60, 40), width=3)
    stamp(img, x + 48, y0 + 20, "GUILTY", inter(12, 800), RED, -10,
          fill=(255, 255, 255))


def card_art_11(img, draw, x, y0):
    """Pill vs pancreatic cancer — BEFORE: a 56x20 capsule, small
    tumours, a thin check. AFTER: a BIGGER capsule (70x24) as the
    hero, and a clearer shrinking sequence — a big red tumour,
    a medium orange one, a tiny pale one, small chevrons between
    them, then a BIG thick green check. First glance: a pill that
    shrinks tumours; 61 PATIENTS from the dek."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(238, 244, 240))
    draw.text((x + 6, y0 + 6), "61 PATIENTS", font=inter(9, 800),
              fill=(14, 124, 123), anchor="la")
    # Tumours shrink left to right along the bottom, with chevrons
    # between them, then a big thick green check.
    for cx, r, col in [(26, 10, (200, 60, 50)),
                       (58, 7, (230, 130, 40)),
                       (86, 4, (240, 210, 180))]:
        draw.ellipse([x + cx - r, y0 + 38 - r, x + cx + r, y0 + 38 + r],
                     fill=col)
    for ax in (42, 72):
        draw.line([x + ax, y0 + 35, x + ax + 4, y0 + 38], fill=(14, 124, 123),
                  width=2)
        draw.line([x + ax + 4, y0 + 38, x + ax, y0 + 41], fill=(14, 124, 123),
                  width=2)
    draw.line([x + 96, y0 + 37, x + 100, y0 + 41], fill=(14, 124, 123),
              width=3)
    draw.line([x + 100, y0 + 41, x + 108, y0 + 31], fill=(14, 124, 123),
              width=3)
    cap = Image.new("RGBA", (70 * SS, 24 * SS), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cap)
    cd.rounded_rectangle([0, 0, 70 * SS, 24 * SS], radius=12 * SS,
                         fill=(255, 255, 255), outline=(180, 175, 165),
                         width=SS)
    cd.rounded_rectangle([35 * SS, 0, 70 * SS, 24 * SS], radius=12 * SS,
                         fill=(14, 124, 123))
    cap = cap.rotate(-25, expand=True, resample=Image.BICUBIC)
    img.paste(cap, ((x + 76) * SS, (y0 + 2) * SS), cap)


def card_art_12(img, draw, x, y0):
    """AI centres abroad — BEFORE: a small "$" bubble, a modest
    server rack, an 11px TAX stamp. AFTER: a BIGGER "$" bubble
    (20px $), a LARGER dark server rack with glowing gold LEDs
    that dominates the right side, and a LARGE TAX stamp (13px)
    across it. First glance: a tax on AI servers."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(236, 232, 226))
    draw.rectangle([x + 6, y0 + 12, x + 54, y0 + 40], fill=(255, 255, 255),
                   outline=(120, 120, 120))
    draw.polygon([(x + 20, y0 + 12), (x + 44, y0 + 12), (x + 32, y0 + 4)],
                 fill=(255, 255, 255), outline=(120, 120, 120))
    draw.text((x + 30, y0 + 26), "$", font=inter(20, 800), fill=RED,
              anchor="mm")
    draw.rectangle([x + 96, y0 + 6, x + 152, y0 + 44], fill=(30, 30, 40))
    for px in (102, 112, 122, 132, 142, 150):
        draw.line([x + px, y0 + 6, x + px, y0 + 10], fill=(212, 175, 55),
                  width=2)
        draw.line([x + px, y0 + 40, x + px, y0 + 44], fill=(212, 175, 55),
                  width=2)
    stamp(img, x + 124, y0 + 25, "TAX", inter(13, 800), RED, -10,
          fill=(255, 255, 255))


def card_art_13(draw, x, y0):
    """Nvidia — BEFORE: a flat green chip, a thin red down-arrow,
    a small "-14%" chip. AFTER: a BIGGER green chip and a HUGE
    thick red down-arrow (8px shaft, large head) that pierces
    it top to bottom — the arrow IS the story — with "-14%" in
    a larger white chip. First glance: Nvidia plunging."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(238, 240, 236))
    draw.rectangle([x + 36, y0 + 6, x + 120, y0 + 40], fill=(118, 185, 0))
    for px in (44, 56, 68, 80, 92, 104, 116):
        draw.line([x + px, y0 + 2, x + px, y0 + 6], fill=(60, 90, 0),
                  width=2)
        draw.line([x + px, y0 + 40, x + px, y0 + 44], fill=(60, 90, 0),
                  width=2)
    draw.line([x + 78, y0 + 4, x + 78, y0 + 34], fill=RED, width=8)
    draw.polygon([(x + 78, y0 + 44), (x + 66, y0 + 30), (x + 90, y0 + 30)],
                 fill=RED)
    draw.rectangle([x + 124, y0 + 4, x + 158, y0 + 22], fill=(255, 255, 255),
                   outline=(90, 85, 75))
    draw.text((x + 141, y0 + 13), "-14%", font=inter(13, 800), fill=RED,
              anchor="mm")


def card_art_14(draw, x, y0):
    """Marcos / APEC — BEFORE: a small PH flag, a thin dashed arc,
    a small plane, a modest "P41.1bn" chip. AFTER: a THICKER
    dashed flight arc (3px), a bigger plane, and a LARGE navy
    "P41.1bn" chip (72x16, 13px) — the pledges are the story —
    with "7,000+ JOBS" beneath. First glance: P41.1bn flies home."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(226, 234, 242))
    draw.paste(_flag_image("PH", 26, 13), (x + 6, y0 + 6))
    _flag_outline(draw, x + 6, y0 + 6, "PH", 26, 13)
    pts = quad((x + 34, y0 + 30), (x + 80, y0 + 8), (x + 126, y0 + 24))
    dashed_curve(draw, pts, (90, 85, 75), 3)
    draw.polygon([(x + 118, y0 + 20), (x + 148, y0 + 24), (x + 118, y0 + 28),
                  (x + 124, y0 + 24)], fill=(255, 255, 255),
                 outline=(90, 85, 75))
    draw.polygon([(x + 126, y0 + 22), (x + 142, y0 + 18), (x + 142, y0 + 22)],
                 fill=(255, 255, 255), outline=(90, 85, 75))
    draw.rectangle([x + 86, y0 + 28, x + 158, y0 + 44], fill=NAVY)
    draw.text((x + 122, y0 + 36), "P41.1bn", font=inter(13, 800),
              fill=(255, 255, 255), anchor="mm")
    draw.text((x + 8, y0 + 44), "7,000+ JOBS", font=inter(8, 800),
              fill=(26, 110, 74), anchor="ls")


def card_art_15(draw, x, y0):
    """Gaza — BEFORE: a thin Yellow Line (6px) with a small black
    X break, tents. AFTER: a THICK Yellow Line (8px) with a WIDE
    jagged break (24px gap) and a BOLD black X, plus a red marker
    flag planted at the break — the truce frays, and the break
    is the whole picture. CLAIMED, so tension, not damage: no
    explosion, just the break and the flag."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(238, 232, 214))
    draw.rectangle([x, y0, x + 18, y0 + 46], fill=(210, 226, 238))
    # The Yellow Line at one height, broken in the middle: a wide
    # gap with a bold black X marking the break.
    draw.line([x + 18, y0 + 18, x + 76, y0 + 18], fill=(230, 200, 40),
              width=8)
    draw.line([x + 100, y0 + 18, x + 160, y0 + 18], fill=(230, 200, 40),
              width=8)
    draw.line([x + 78, y0 + 11, x + 98, y0 + 25], fill=INK, width=3)
    draw.line([x + 78, y0 + 25, x + 98, y0 + 11], fill=INK, width=3)
    # Red marker flag planted at the break.
    draw.line([x + 88, y0 + 25, x + 88, y0 + 40], fill=(90, 85, 75),
              width=2)
    draw.polygon([(x + 88, y0 + 25), (x + 100, y0 + 28), (x + 88, y0 + 31)],
                 fill=RED)
    for tx in (118, 136, 152):
        draw.polygon([(x + tx - 8, y0 + 42), (x + tx, y0 + 28),
                      (x + tx + 8, y0 + 42)], fill=(200, 190, 160),
                     outline=(120, 110, 90))


def card_art_16(draw, x, y0):
    """Gen Z protests — BEFORE: 10 small figures, a modest central
    placard with a 15px "25". AFTER: a DENSER crowd (12 figures,
    raised arms, varied shirt colours) holding up a LARGE central
    placard with a HUGE red "25" (20px) — the count is the story
    — flanked by two smaller placards. First glance: a crowd
    marching, 25 countries."""
    draw.rectangle([x, y0, x + 160, y0 + 46], fill=(238, 236, 230))
    shirts = [(200, 80, 60), (43, 92, 168), (26, 110, 74), (198, 110, 28),
              (123, 75, 166), (14, 124, 123)]
    for i in range(12):
        px = x + 4 + i * 13
        draw.ellipse([px + 4, y0 + 22, px + 12, y0 + 30], fill=(40, 35, 30))
        draw.rectangle([px + 2, y0 + 30, px + 14, y0 + 44],
                       fill=shirts[i % len(shirts)])
        draw.line([px + 12, y0 + 32, px + 16, y0 + 18],
                  fill=shirts[i % len(shirts)], width=2)
    draw.rectangle([x + 8, y0 + 6, x + 30, y0 + 18], fill=PANEL,
                   outline=(90, 85, 75))
    draw.rectangle([x + 130, y0 + 6, x + 152, y0 + 18], fill=PANEL,
                   outline=(90, 85, 75))
    draw.rectangle([x + 48, y0 + 2, x + 112, y0 + 20], fill=PANEL,
                   outline=(90, 85, 75))
    draw.text((x + 80, y0 + 11), "25", font=inter(20, 800), fill=RED,
              anchor="mm")


CARD_ART = {
    5: card_art_5, 6: card_art_6, 7: card_art_7, 8: card_art_8,
    9: card_art_9, 13: card_art_13, 14: card_art_14,
    15: card_art_15, 16: card_art_16,
}


def draw_card(img, draw, card, x, y0):
    w = 160
    region = S.REGION_COLOURS[card["region"]]
    draw.rectangle([x, y0, x + w, y0 + 157], fill=PANEL,
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
    cy = y0 + 54
    number_circle(draw, x + 6 + 6, cy, 12, region, card["id"], 8.5)
    draw.text((x + 21, y0 + 59), card["kicker"], font=inter(9.5, 800),
              fill=region, anchor="ls")
    font, lines, leading = fit_headline(
        card["headline"], [(18, 19), (16, 18)], 148)
    ty = y0 + 61
    for line in lines:
        draw.text((x + 6, ty), line, font=font, fill=INK, anchor="la")
        ty += leading
    dek_font, dek_lines = fit_dek(card["dek"], 148)
    ty = y0 + 120
    for line in dek_lines:
        draw.text((x + 6, ty), line, font=dek_font, fill=DEK,
                  anchor="la")
        ty += dek_font.size + 1.5
    # BADGE RULE (2026-11-21, user-confirmed): medium cards show NO
    # CONFIRMED badge — an unmarked medium card reads as confirmed
    # (see the footer legend). REPORTED / CLAIMED badges stay exactly
    # as they are. Leads (draw_lead) keep their CONFIRMED badges.
    if card["status"] != "CONFIRMED":
        badge(draw, x + 6, y0 + 146, card["status"], 10, 8.5)
    draw.text((x + w - 6, y0 + 155), card["source"].upper(),
              font=inter(9, 700), fill=MUTED, anchor="rs")


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
# cropped atlas map), lat 70..-46. X scale 0.676 px/deg, Y scale
# 0.95 px/deg — a 1.4x vertical stretch, the usual newspaper-inset
# compromise: coastlines stay true in shape (Africa 46x67px,
# Australia 27x27px) while the map fills the squarish panel. The
# 110px-tall map is centred vertically in the panel's 160px drawable
# band (caption below it), leaving equal sea margins top/bottom.
# (Round 5, 2026-11-21: panel grew 154 -> 172px tall so the block
# reaches down toward the Date Check; the map stays centred, sea
# margins 24.9px top/bottom, dots shift down ~9px with it.)
MAP_LON0, MAP_LON1 = -135.0, 155.0
MAP_LAT_TOP, MAP_LAT_BOT = 70.0, -46.0
MAP_XSCALE = 196 / (MAP_LON1 - MAP_LON0)
MAP_YSCALE = 0.95
MAP_TOP = 740 + (160 - (MAP_LAT_TOP - MAP_LAT_BOT) * MAP_YSCALE) / 2
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
    panel (7px inset; y capped at 900, clear of the caption whose
    baseline is now 908 — in practice the southernmost dots sit
    near y~868, so the cap never binds)."""
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
            pos[i][0] = min(201, max(19, x + fx))
            pos[i][1] = min(900, max(762, y + fy))
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
            q[0] = min(201, max(19, q[0]))
            q[1] = min(900, max(762, q[1]))
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
        if not (19 <= x <= 201 and 762 <= y <= 900):
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
                if not (19 <= x <= 201 and 762 <= y <= 900):
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
                if not (19 <= x <= 201 and 762 <= y <= 900):
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
    ox, oy = 12, 740
    # Draw the map on its own tile so coastline polygons that run
    # past the panel (high latitudes, the lon crop) are clipped by
    # the tile edge instead of painting over the briefs/bottom strip.
    # Tile height 169 (oy..909, round 5 + 3px reclaimed for the bar):
    # the tile must end above the Date Check strip (913) or it would
    # paint over the strip, which is drawn before the map is pasted
    # — 909 leaves a 4px gap. The map itself is unchanged (still
    # centred in its 160px drawable); only the sea below the caption
    # is 3px shorter.
    tile = Image.new("RGB", (196 * SS, 169 * SS), (222, 232, 240))
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
    # Typography: caption is the smallest text on the page (9px);
    # MUTED on the pale sea was ~3.2:1. DEK takes it to ~5.3:1.
    # Width 166.1px, still fits the 190px panel.
    # Caption at oy+165 (baseline 905, descenders ~907): it rides
    # the panel bottom now (tile ends 909), 2px above the tile edge
    # and ~6px above the Date Check strip (913).
    draw.text((ox + 6, oy + 165), "Dots 1–16: leads & cards · Small dots: briefs",
              font=inter(9, 400), fill=DEK, anchor="ls")


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


def draw_briefs(draw):
    # LAYOUT, ROUND 5 (2026-11-21, user order): brief text 12 -> 12.5px
    # and the block grows taller so its bottom sits flush with the map
    # panel (912) and only ~4px above the Date Check strip (916).
    # TEXT SIZE: 13px was tried first and does NOT fit — even after
    # every column is widened into the dead gaps (below), 6 rows still
    # truncate at 13px (44 +5.4, 47 +5.1, 21 +4.9, 49 +2.6, 34 +3.4,
    # 50 +0.9); 12.75px still loses 4 rows. 12.5px is the largest
    # size that fits all 30 rows whole: tightest spares are brief 44
    # (2.9px), 47 (3.4px), 21 (4.4px), 34 (4.9px); no truncation, no
    # wrap, no wording trim. Baseline top+11.5 (was top+11 at 12px),
    # so cap tops sit ~top+2.5 against the 12px flag.
    # COLUMNS: starts 216/492/754, limits 234/220/218. Col 1's row end
    # (490) stops 2px short of col 2's flags (492); col 2's row end
    # (752) stops 2px short of col 3's flags (754); col 3 starts 8px
    # left of its old 762 and its row end (1012) sits flush with the
    # content edge, like the Markets/Sport bar. The widening (col 1
    # +10, col 2 +6, col 3 +10 vs the old 224/214/208) is what buys
    # the 12.5px fit — at the old limits 12.5px truncated 6 rows.
    # ROWS 17.15px (was 17.5): the 10-row block now spans 740..~909 —
    # last row top 894.35, descenders ~908.5, flush with the map panel
    # bottom (909). The 0.35px x 9 pitch cut frees ~3px, which moves
    # the Date Check strip up 3px (913..960) so the Markets/Sport bar
    # below gains 3px of height (964..998) — the briefs/map bottom
    # alignment itself does not move relative to the strip (gap ~4px,
    # as before). The pitch, not the text, does the stretching: the
    # block top stays 740 and the footer stays at 1001/1013.5.
    # SEPARATORS: a 0.75px muted hairline (214, 210, 201) between
    # every two brief rows. It sits at next_top+0.75 — ~3.9px below
    # the previous row's descender bottoms (~prev_top+14.3) and
    # ~1.8px above the next row's cap tops (~next_top+2.5) — and is
    # drawn in a FIRST pass, before any row text, so a descender or
    # flag that crosses it paints over it instead of being struck
    # through by it. 9 per column (between rows only, never after
    # the last row, so the Date Check gap stays clean). The +0.75
    # offset keeps y on the 0.25px grid Pillow's line needs at 4x
    # supersampling (17.5px pitch: 740 + i*17.5 + 0.75).
    # SOURCE LABELS (2026-11-21, user order): the numbered circles
    # are gone — each brief carries its source as a compact 7px
    # Inter-800 small-caps label (S.BRIEF_SOURCE_LABEL, from
    # stories.json; Reuters -> RTRS, Bloomberg Law -> BLOOM — the
    # full names would truncate briefs 22/47/51 and 34). The label
    # sits at the END of the row, right-aligned at the row end
    # (col_x+40+limit), baseline top+9.5 so its caps stay centred
    # on the flag. The flag now sits at the column edge (col_x) —
    # the label slot it used to hug is gone — and the brief text
    # follows the flag with a 2px gap, stopping 3px short of the
    # label. So the text limit is row_end - 3 - label_w - tx, and
    # the freed label slot almost exactly pays for the label at
    # the end: at 12.5px the tightest fit is brief 44 (FOOTY,
    # 2.9px spare) and brief 47 (RTRS, 3.4px spare); no brief
    # truncates. The
    # map's numbered dots 1-16 are NOT affected — only the brief
    # list lost its numbers. The label is 7px caps in muted DEK
    # grey against 12px black text, right-aligned at a fixed row
    # end, so it reads as a credit rather than part of the text —
    # no middot separator: on the tightest rows there is no room
    # for one between text end and label without truncating.
    # FITS at 12.5px (measured with the same getlength the renderer
    # uses, per row: text width vs row_end - 3 - label_w - tx):
    # tightest spares 44: 2.9px, 47: 3.4px, 21: 4.4px, 34: 4.9px —
    # all 30 rows fit whole, no truncation, no wrap.
    columns = [(216, S.BRIEFS[0:10], 234), (492, S.BRIEFS[10:20], 220),
               (754, S.BRIEFS[20:30], 218)]
    bold = inter(12.5, 700)
    regular = inter(12.5, 400)
    label_font = inter(7, 800)
    for col_x, items, limit in columns:
        for i in range(1, len(items)):
            y = 740 + i * 17.15 + 0.75
            draw.line([col_x, y, col_x + 40 + limit, y],
                      fill=(214, 210, 201), width=0.75)
    # VERTICAL DIVIDERS (user order, 2026-11-21): 1px hairlines in
    # the gutters between the three brief columns — x=491 (col 1
    # row end 490 / col 2 flag start 492) and x=753 (col 2 row
    # end 752 / col 3 flag start 754). Same (214, 210, 201)
    # hairline as the row separators. Span 740..909: the full
    # briefs block, top of the first row to the bottom of the
    # last row (flush with the map panel bottom). Drawn in this
    # first pass, before any row text, so nothing is struck
    # through; the gutters hold no text or flags.
    for div_x in (491, 753):
        draw.line([(div_x, 740), (div_x, 909)],
                  fill=(214, 210, 201), width=1)
    for col_x, items, limit in columns:
        row_end = col_x + 40 + limit
        for i, (sid, region, flag, text) in enumerate(items):
            top = 740 + i * 17.15
            label = S.BRIEF_SOURCE_LABEL[sid]
            label_w = label_font.getlength(label)
            # flag at the column edge; text follows with a 2px gap.
            draw_flag(draw, col_x, top + 1, flag)
            tx = col_x + 20
            # text stops 3px short of the source label, which is
            # right-aligned at the row end (see comment above).
            row_limit = row_end - 3 - label_w - tx
            draw.text((row_end, top + 9.5), label, font=label_font,
                      fill=DEK, anchor="rs")
            if ": " in text:
                head, _, tail = text.partition(": ")
                head += ": "
            else:
                head, tail = text.split(" ", 1)[0] + " ", text.split(" ", 1)[1]
            shown = head + tail
            while (bold.getlength(head) + regular.getlength(tail) > row_limit
                   and len(tail) > 1):
                tail = tail[:-1]
                shown = head + tail + "…"
            draw.text((tx, top + 11.5), head, font=bold, fill=INK, anchor="ls")
            draw.text((tx + bold.getlength(head), top + 11.5), tail,
                      font=regular, fill=INK, anchor="ls")
            if shown.endswith("…"):
                draw.text((tx + bold.getlength(head)
                           + regular.getlength(tail), top + 11.5), "…",
                          font=regular, fill=INK, anchor="ls")


def _date_check_segments():
    """Date Check categories parsed from S.DATE_CHECK_LINES, so the
    facts live verbatim in exactly one place (stories.py) and this
    function only re-slices them: (label, pill fill, tint fill,
    [items]). LEFT OUT 4 items, EDGE 1, NOT YET 2. The " · "
    separators between items survive inside each segment; the one
    between two categories is replaced by the gap between their
    tinted blocks (see draw_bottom_strip)."""
    full = " · ".join(S.DATE_CHECK_LINES)
    left = full.split("LEFT OUT: ", 1)[1].split(" · EDGE: ", 1)[0]
    edge = full.split(" · EDGE: ", 1)[1].split(" · NOT YET: ", 1)[0]
    yet = full.split(" · NOT YET: ", 1)[1]
    return [
        ("LEFT OUT", RED, (247, 205, 203), left.split(" · ")),
        ("EDGE", (176, 86, 0), (249, 226, 186), edge.split(" · ")),
        ("NOT YET", NAVY, (208, 221, 240), yet.split(" · ")),
    ]


def draw_bottom_strip(draw):
    draw.text((12, 736), "WHERE IT HAPPENED", font=inter(12, 800),
              fill=RED, anchor="ls")
    draw.text((216, 736), "ALSO ON FRIDAY 20 NOVEMBER",
              font=inter(12, 800), fill=RED, anchor="ls")
    # LAYOUT (2026-11-21, masthead freed ~15px): the whole bottom
    # block moves up 15px with the middle of the page (headers
    # baseline 751 -> 736, briefs/map top 755 -> 740, brief rows
    # 13.0 -> 17.15px — see draw_briefs). The footer rule and
    # footer stay exactly where they were (rule 1001, baseline
    # 1013.5); the Date Check strip moved up 3px (913..960, was
    # 916..963) on the 3px the briefs pitch gave back, so the
    # Markets/Sport bar gains 3px (964..998).
    # Gaps below are measured ink-to-ink (caps/descenders, strict
    # threshold), all >= 2px:
    #   card row 2 ends 721; headers caps ~727 (gap ~6)
    #   last brief descenders ~908 = map panel bottom 909;
    #   Date Check top 913 (gap ~4-5)
    #   strip 913..960; bar top 964 (gap 4)
    #   bar 964..998; footer rule 1001 (gap 3)
    #   footer caps ~1007 (gap ~6); footer descenders ~1016,
    #   3px clear of the outer border (1019), 8px off the page edge.
    # DATE CHECK, STRUCTURED (2026-11-21): the three run-on lines
    # are now three labelled category blocks. Each category gets a
    # filled pill tag (LEFT OUT red, EDGE amber, NOT YET navy) and
    # a pale tinted block in its own colour behind its items, so
    # the categories read as separate blocks at a glance; items in
    # one category stay joined by " · ", and a 12px gap (no " · ")
    # separates one category's block from the next. LEFT OUT spans
    # two lines — its second line (Kenya item) carries the same red
    # tint, so the continuation is visibly the same block. The
    # DATE CHECK badge stays where it was, vertically centred on
    # the strip. Type is 12px (was 11.5), leading 13.5px
    # (baselines 926/939.5/953); pills are 10.5px (was 9.5) and
    # 15px tall (was 14); tints deepened a step (see
    # _date_check_segments). The strip is 47px (913..960) — same
    # height as before, moved up 3px on space freed by tightening
    # the briefs pitch 17.5 -> 17.15 (see draw_briefs), so the bar
    # below gains 3px of height instead.
    # WHY NOT ONE ROW PER CATEGORY: a clean row per category needs
    # a 4th line — LEFT OUT alone measures 1104.4px at 11.5px
    # against 888px of text width, so it always wraps to two lines
    # (EDGE 1 line, NOT YET 1 line). Four lines at 13.5px leading
    # need a ~59px strip (3 x 13.5 + caps/descenders + padding),
    # ~15px taller than the old 44px strip; only ~6px could be
    # freed (strip top 917 -> 916, bottom 961 -> 963) without
    # crowding the briefs above (3.1px gap at 916) or Markets
    # below (5.5px gap at 963). So the compact 3-line structured
    # layout below is the fit, now at 12px type (2026-11-21
    # enrichment — measured ends 787/702, inside the 1004 limit).
    # Flow is measured, not hard-coded: pills and items are laid
    # out left to right with getlength, wrapping an item to the
    # next line when it would pass x=1004. Measured ends at 12px
    # type / 10.5px pills: line 1 (LEFT OUT pill + 3 items) 828.9;
    # line 2 (Kenya + EDGE pill + 1 item) 786.6; line 3 (NOT YET
    # pill + 2 items) 701.9 — all inside the 1004 limit.
    draw.rectangle([12, 913, 1012, 960], fill=(253, 243, 238),
                   outline=RED, width=1.5)
    dc_font = inter(12, 400)
    pill_font = inter(10.5, 800)
    sep_w = dc_font.getlength(" · ")
    x0, x1 = 116, 1004
    baselines = [926, 939.5, 953]
    ops = [[] for _ in baselines]      # ("pill", label, x, w, fill)
                                       # ("text", s, x)
    blocks = [[] for _ in baselines]  # (x_start, x_end, tint)
    line, x = 0, x0
    for label, pill_fill, tint, items in _date_check_segments():
        pw = pill_font.getlength(label) + 12
        # The pill travels with its first item: if pill + first item
        # do not fit on this line, the pill wraps with them instead
        # of stranding alone at the end of the line (that bug put a
        # lone NOT YET pill at the end of line 2, with its items on
        # line 3 and no pill there).
        first_w = dc_font.getlength(items[0]) if items else 0
        if x > x0 and x + pw + 4 + first_w > x1:
            line += 1
            x = x0
        block_start = x
        ops[line].append(("pill", label, x, pw, pill_fill))
        x += pw + 4
        first = True
        for item in items:
            w = dc_font.getlength(item)
            if x + w > x1:
                blocks[line].append((block_start, x, tint))
                line += 1
                block_start, x, first = x0, x0, True
            if not first:
                ops[line].append(("text", " · ", x))
                x += sep_w
            ops[line].append(("text", item, x))
            x += w
            first = False
        blocks[line].append((block_start, x, tint))
        x += 12
    for i, base in enumerate(baselines):
        for bx0, bx1, tint in blocks[i]:
            draw.rounded_rectangle(
                [bx0 - 4, base - 10.5, bx1 + 4, base + 3.5], radius=4,
                fill=tint)
        for op in ops[i]:
            if op[0] == "pill":
                _, label, px, pw, fill = op
                draw.rounded_rectangle(
                    [px, base - 11, px + pw, base + 4], radius=7.5,
                    fill=fill)
                draw.text((px + pw / 2, base - 3.5), label,
                          font=pill_font, fill=(255, 255, 255),
                          anchor="mm")
            else:
                draw.text((op[2], base), op[1], font=dc_font, fill=INK,
                          anchor="ls")
    draw.rectangle([18, 927.5, 110, 945.5], fill=RED)
    draw.text((64, 936.5), "DATE CHECK", font=inter(10.5, 800),
              fill=(255, 255, 255), anchor="mm")
    # MARKETS + SPORT, ONE BAR (2026-11-21, user order): the two
    # lines are no longer separate — they sit in a single white bar
    # (964..998, hairline outline) with a 1px hairline separator
    # between the MARKETS half (top) and the SPORT half (bottom).
    # Side-by-side halves do NOT fit: SPORT alone measures 933px
    # at 11.5px, so the bar stacks the two lines full-width, each
    # on its own row inside the one band. ENRICHED (2026-11-21):
    # the bar is 34px tall (was 31 — 3px freed by the briefs pitch
    # 17.5 -> 17.15, strip moved up 3px with it); MARKETS label and
    # values are 12.5px (was 11.5; values end x=692, huge slack);
    # SPORT label is 12.5px too (42.8px, clear of the text at x=72)
    # but SPORT VALUES STAY 11.5px: at 11.5 they already end x=1005
    # (7px from the edge), and even weight 500 overflows (1012.6) —
    # no size or weight bump fits there. Outline and separator are
    # a step darker and the separator sits at the bar midpoint
    # (y=981). Baselines unchanged (977/993): at 12.5px the MARKETS
    # caps start ~968.2, 4.2px below the bar top.
    draw.rectangle([12, 964, 1012, 998], fill=PANEL,
                   outline=(170, 165, 155), width=1.5)
    draw.text((12, 977), "MARKETS", font=inter(12.5, 800), fill=RED,
              anchor="ls")
    mx = 92
    for text, is_red in S.MARKETS_SEGMENTS:
        font = inter(12.5, 400)
        draw.text((mx, 977), text, font=font,
                  fill=RED if is_red else INK, anchor="ls")
        mx += font.getlength(text)
    draw.line([13, 981, 1011, 981], fill=(150, 145, 135), width=1)
    draw.text((12, 993), "SPORT", font=inter(12.5, 800), fill=RED,
              anchor="ls")
    draw.text((72, 993), S.SPORTS_TEXT, font=inter(11.5, 400), fill=INK,
              anchor="ls")
    # FOOTER: the legend line is no longer a bare centred line under
    # SPORT. A 2px divider rule in dark warm grey (64, 60, 50) sits
    # 3px below the Markets/Sport bar, and the 9.5px muted footer sits
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
    for lead, x in zip(S.LEADS, (12, 264, 516, 768)):
        draw_lead(draw, img, lead, x, 161)
    row1 = S.CARDS[0:6]
    row2 = S.CARDS[6:12]
    for card, x in zip(row1, (12, 180, 348, 516, 684, 852)):
        draw_card(img, draw, card, x, 404)
    for card, x in zip(row2, (12, 180, 348, 516, 684, 852)):
        draw_card(img, draw, card, x, 564)
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
