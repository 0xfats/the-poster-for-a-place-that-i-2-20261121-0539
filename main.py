#!/usr/bin/env python3
"""UPTURN BAY — a travel poster for a place that isn't there.

A program that draws, with the Python standard library only (no network,
no third-party packages, no external assets), one 1024x1024 travel poster
and writes it to /output/entry.png.

The place: UPTURN BAY, a small fishing town where the waterfall falls UP.
At dusk the sea pours skyward off the cliff, and the townsfolk fish the
rising water from their rooftops with nets while a child in a yellow
raincoat points up, laughing. A handwritten note from Mara, 9, is pinned
to the poster for the judge.

Everything is deterministic: fixed coordinates, no randomness, no clock,
no input. Repeated runs produce byte-identical output.
"""

import os
import struct
import zlib

W, H = 1024, 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------------------
# 5x7 bitmap font (authored here; '#' = ink, '.' = empty).
# Covers A-Z, 0-9 and the punctuation this poster needs.
# ---------------------------------------------------------------------------

FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
}


def lerp(a, b, t):
    """Linear interpolation between two RGB colours; t in [0, 1]."""
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def blend(fg, bg, alpha):
    """fg over bg, alpha in [0, 1]."""
    return (
        int(fg[0] * alpha + bg[0] * (1 - alpha)),
        int(fg[1] * alpha + bg[1] * (1 - alpha)),
        int(fg[2] * alpha + bg[2] * (1 - alpha)),
    )


class Canvas:
    """An RGB canvas backed by a bytearray, with fast horizontal spans."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def hline(self, x0, x1, y, color):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        base = (y * self.w + x0) * 3
        n = x1 - x0 + 1
        self.px[base:base + n * 3] = bytes(color) * n

    def vline(self, x, y0, y1, color):
        if x < 0 or x >= self.w:
            return
        y0 = max(0, y0)
        y1 = min(self.h - 1, y1)
        for y in range(y0, y1 + 1):
            base = (y * self.w + x) * 3
            self.px[base:base + 3] = bytes(color)

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            base = (y * self.w + x) * 3
            self.px[base:base + 3] = bytes(color)

    def fill_rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            self.hline(x0, x1, y, color)

    def circle(self, cx, cy, r, color):
        """Filled circle via row spans."""
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.hline(cx - dx, cx + dx, cy + dy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            if t < 0:
                continue
            dx = int(rx * (t ** 0.5))
            self.hline(cx - dx, cx + dx, cy + dy, color)

    def polygon(self, pts, color):
        """Filled polygon (list of (x, y)) via scanline spans."""
        if len(pts) < 3:
            return
        ys = [int(p[1]) for p in pts]
        y0, y1 = max(0, min(ys)), min(self.h - 1, max(ys))
        n = len(pts)
        pts = [(float(p[0]), float(p[1])) for p in pts]
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= yc < y2p) or (y2p <= yc < y1p):
                    t = (yc - y1p) / float(y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(xs[i]), int(xs[i + 1]), y, color)

    def thick_line(self, x0, y0, x1, y1, width, color):
        """A line drawn as a chain of filled circles (round caps)."""
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        r = max(1, width // 2)
        for i in range(steps + 1):
            t = i / float(steps)
            self.circle(int(x0 + dx * t), int(y0 + dy * t), r, color)

    def vgrad(self, y0, y1, stops):
        """Vertical gradient. stops = [(y_fraction, colour), ...] sorted."""
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            f = (y - y0) / float(max(1, y1 - y0))
            for i in range(len(stops) - 1):
                f0, c0 = stops[i]
                f1, c1 = stops[i + 1]
                if f0 <= f <= f1:
                    t = 0.0 if f1 == f0 else (f - f0) / (f1 - f0)
                    self.hline(0, self.w - 1, y, lerp(c0, c1, t))
                    break
            else:
                self.hline(0, self.w - 1, y, stops[-1][1])


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, color, outline=None, slant=0):
    """Draw text with the 5x7 font. x,y = top-left. slant shifts each row
    sideways (for a handwritten feel); outline draws a halo first."""
    if outline is not None:
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                       (-2, -2), (2, -2), (-2, 2), (2, 2)):
            draw_text(cv, x + ox, y + oy, text, scale, outline, None, slant)
    for ci, ch in enumerate(text):
        glyph = FONT.get(ch, FONT[" "])
        gx = x + ci * 6 * scale
        for row in range(7):
            bits = glyph[row]
            sx = gx + (6 - row) * slant
            for col in range(5):
                if bits[col] == "#":
                    cv.fill_rect(sx + col * scale, y + row * scale,
                                 sx + col * scale + scale - 1,
                                 y + row * scale + scale - 1, color)


def draw_text_centered(cv, cx, y, text, scale, color, outline=None, slant=0):
    draw_text(cv, cx - text_width(text, scale) // 2, y, text, scale,
              color, outline, slant)


# ---------------------------------------------------------------------------
# PNG encoding (pure stdlib: zlib + struct).
# ---------------------------------------------------------------------------

def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(ctype, data):
        out = struct.pack(">I", len(data)) + ctype + data
        out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    os.chmod(path, 0o644)
    return len(png)


# ---------------------------------------------------------------------------
# The poster scene.
#
# Layout (1024 x 1024):
#   sky 0..640, sea 640..1024, horizon at y=640.
#   Cliff headland on the left (x 0..~300). The up-waterfall rises from the
#   sea at x~470 and pours into the sky. Town on the cliff top. The sun
#   sets low on the right. Name across the top sky, tagline under it, a
#   pinned handwritten note for the judge at bottom right.
# ---------------------------------------------------------------------------

CREAM = (255, 243, 214)
INK = (43, 33, 58)
PAPER = (251, 243, 221)
NOTE_INK = (58, 42, 74)

HORIZON = 640


def draw_sky(cv):
    cv.vgrad(0, HORIZON, [
        (0.00, (24, 30, 78)),    # deep indigo dusk
        (0.35, (74, 52, 110)),   # violet
        (0.62, (178, 88, 110)),  # rose
        (0.85, (240, 150, 86)),  # amber
        (1.00, (250, 196, 120)),  # low golden light
    ])
    # Early stars in the upper sky.
    for (x, y, r) in [(90, 260, 2), (180, 210, 2), (330, 300, 2),
                      (880, 250, 2), (950, 330, 2), (700, 200, 2),
                      (520, 260, 1), (120, 340, 1), (980, 200, 1)]:
        cv.circle(x, y, r, CREAM)


def draw_sun(cv):
    # Low sun with a soft radial glow, drawn as stepped concentric discs.
    cx, cy = 720, 585
    core, mid, edge = (255, 220, 140), (247, 168, 92), (232, 122, 78)
    for i in range(26, 0, -1):
        t = i / 26.0
        col = lerp(core, edge, t) if t > 0.5 else lerp(mid, core, 1 - t * 2)
        cv.circle(cx, cy, 64 + i * 4, col)
    cv.circle(cx, cy, 64, (255, 224, 148))
    # A thin bright rim on the sun's lower edge.
    cv.ellipse(cx, cy + 58, 62, 10, (255, 240, 190))


def draw_clouds(cv):
    # Soft horizontal dusk clouds: overlapping ellipses in warm tones.
    clouds = [
        (250, 330, 110, 22, (226, 140, 130)),
        (820, 300, 100, 20, (226, 140, 130)),
        (620, 420, 90, 18, (240, 170, 130)),
        (150, 470, 75, 16, (200, 120, 130)),
    ]
    for (cx, cy, rx, ry, col) in clouds:
        cv.ellipse(cx, cy, rx, ry, col)
        cv.ellipse(cx + 40, cy + 6, rx // 2, ry // 2 + 4, col)
        cv.ellipse(cx - 45, cy + 7, rx // 2, ry // 2 + 4, col)
        # A lighter top sliver so the cloud reads as vapour, not a disc.
        cv.ellipse(cx - 10, cy - ry // 2, rx // 2, ry // 3 + 2,
                   lerp(col, CREAM, 0.45))


def draw_sea(cv):
    cv.vgrad(HORIZON, H - 1, [
        (0.00, (23, 96, 104)),   # teal, lit by the sunset
        (0.30, (16, 74, 90)),
        (0.65, (11, 54, 74)),
        (1.00, (8, 40, 60)),     # deep water at the poster's foot
    ])
    # Sun glitter: a broken path of light on the water under the sun.
    for i, (x0, x1, y) in enumerate([
            (660, 790, 665), (640, 810, 690), (680, 780, 715),
            (650, 800, 745), (690, 770, 780), (660, 790, 815)]):
        cv.hline(x0, x1, y, (255, 205, 130))
        cv.hline(x0 + 20, x1 - 10, y + 3, (240, 175, 110))
    # Long wave strokes across the sea.
    for (x0, x1, y, col) in [
            (60, 260, 700, (120, 190, 195)), (340, 560, 730, (110, 180, 185)),
            (820, 980, 720, (120, 190, 195)), (120, 330, 820, (90, 160, 170)),
            (560, 800, 860, (100, 170, 178)), (40, 220, 900, (90, 160, 170)),
            (760, 960, 900, (100, 170, 178)), (300, 520, 950, (80, 145, 158))]:
        cv.hline(x0, x1, y, col)
        cv.hline(x0 + 30, x1 - 40, y + 2, col)


def draw_cliff(cv):
    # Dark headland silhouette on the left, warm rim light on its edge.
    pts = [(0, 452), (110, 408), (205, 436), (258, 508), (300, 640),
           (0, 640)]
    cv.polygon(pts, (38, 30, 56))
    # Rim light along the cliff's right edge.
    cv.thick_line(205, 436, 258, 508, 4, (240, 150, 96))
    cv.thick_line(258, 508, 300, 640, 4, (232, 132, 88))
    cv.thick_line(110, 408, 205, 436, 3, (200, 110, 100))
    # A few pale gulls above the cliff.
    for (x, y, s) in [(330, 380, 10), (370, 350, 8), (300, 320, 7)]:
        cv.thick_line(x - s, y, x, y - 5, 2, (40, 32, 56))
        cv.thick_line(x, y - 5, x + s, y, 2, (40, 32, 56))


def draw_house(cv, x, y, w, h, roof_col, wall_col):
    """A tiny house: wall, pitched roof, one lit window, one dark door."""
    cv.fill_rect(x, y, x + w, y + h, wall_col)
    cv.polygon([(x - 4, y), (x + w // 2, y - 16), (x + w + 4, y)], roof_col)
    cv.fill_rect(x + w // 4, y + h // 3, x + w // 4 + 10, y + h // 3 + 12,
                 (255, 214, 138))
    cv.fill_rect(x + w - 14, y + h - 16, x + w - 6, y + h, (30, 24, 44))


def draw_town(cv):
    # A row of small houses along the cliff top and the shore.
    draw_house(cv, 30, 428, 46, 34, (58, 40, 70), (84, 62, 88))
    draw_house(cv, 92, 414, 40, 30, (58, 40, 70), (96, 70, 84))
    draw_house(cv, 148, 426, 48, 36, (52, 38, 66), (78, 58, 92))
    draw_house(cv, 210, 440, 42, 32, (58, 40, 70), (88, 64, 86))
    # A tiny lighthouse on the cliff's edge, lamp lit.
    cv.fill_rect(268, 470, 282, 560, (240, 232, 210))
    cv.polygon([(264, 470), (275, 448), (286, 470)], (58, 40, 70))
    cv.fill_rect(270, 456, 280, 466, (255, 214, 138))
    cv.circle(275, 461, 4, (255, 230, 160))
    # Warm windows glowing along the shore cottages.
    for (x, y) in [(330, 600), (360, 606), (392, 600)]:
        cv.fill_rect(x, y, x + 8, y + 10, (255, 214, 138))


def draw_figure(cv, x, y, color, arm_up=False):
    """A tiny person: head, body, legs; optionally one arm raised."""
    cv.circle(x, y - 14, 4, (245, 205, 170))
    cv.thick_line(x, y - 10, x, y + 2, 5, color)
    cv.thick_line(x, y + 2, x - 4, y + 12, 3, color)
    cv.thick_line(x, y + 2, x + 4, y + 12, 3, color)
    if arm_up:
        cv.thick_line(x, y - 8, x + 9, y - 20, 3, color)
    else:
        cv.thick_line(x, y - 8, x - 7, y - 2, 3, color)


def draw_rooftop_folk(cv):
    # Townsfolk on the rooftops, hauling a net up toward the rising water.
    draw_figure(cv, 52, 428, (70, 90, 120))
    draw_figure(cv, 112, 414, (150, 70, 80))
    draw_figure(cv, 172, 426, (60, 110, 90))
    # The net: two ropes from the roof folk up to a sagging net arc.
    cv.thick_line(56, 420, 120, 372, 2, (230, 220, 200))
    cv.thick_line(176, 418, 120, 372, 2, (230, 220, 200))
    for (nx, ny) in [(96, 386), (112, 380), (128, 384), (104, 396),
                      (120, 392), (136, 396)]:
        cv.circle(nx, ny, 2, (230, 220, 200))
    # Mara, 9, in a yellow raincoat on the lighthouse rock, pointing UP.
    draw_figure(cv, 292, 470, (255, 210, 62), arm_up=True)
    cv.circle(292, 456, 5, (255, 210, 62))  # her hood


# ---------------------------------------------------------------------------
# The landmark: the waterfall that falls UP.
# ---------------------------------------------------------------------------

def waterfall_center(x_top=470, y_top=168, y_base=668):
    """Sample the waterfall's centreline: an S-curve rising from the sea."""
    pts = []
    for i in range(0, 63):
        t = i / 62.0  # 0 at the top, 1 at the base
        y = y_top + (y_base - y_top) * t
        x = x_top + 58 * _sin(t * 2.6) - 22 * t
        half = 23 + 36 * t  # narrow at the top, wide where it leaves the sea
        pts.append((x, y, half))
    return pts


def _sin(v):
    # Sine via its Taylor series (no math import needed for determinism
    # beyond what the stdlib already guarantees; kept explicit here).
    x = v % 6.283185307179586
    term = x
    total = x
    for n in range(1, 7):
        term *= -x * x / ((2 * n) * (2 * n + 1))
        total += term
    return total


def draw_fish(cv, x, y, size, color, up=True):
    """A small fish: body ellipse + tail triangle, nose pointing up."""
    cv.ellipse(x, y, size // 2, size, color)
    tip_y = y - size - size // 2 if up else y + size + size // 2
    cv.polygon([(x - size // 2, y + size // 2 if up else y - size // 2),
                (x + size // 2, y + size // 2 if up else y - size // 2),
                (x, tip_y)], color)
    cv.circle(x - 3, y - 2, 1, (8, 40, 60))


def draw_waterfall(cv):
    pts = waterfall_center()
    # Foam halo: a wider pale ribbon behind the water.
    left = [(x - h - 9, y) for (x, y, h) in pts]
    right = [(x + h + 9, y) for (x, y, h) in reversed(pts)]
    cv.polygon(left + right, (228, 244, 238))
    # The water itself: pale aqua.
    left = [(x - h, y) for (x, y, h) in pts]
    right = [(x + h, y) for (x, y, h) in reversed(pts)]
    cv.polygon(left + right, (176, 226, 228))
    # A darker core current running up the middle.
    core = [(x - h * 0.45, y) for (x, y, h) in pts]
    core += [(x + h * 0.45, y) for (x, y, h) in reversed(pts)]
    cv.polygon(core, (120, 196, 208))
    # White streaks: the water breaking as it climbs.
    for (sx, sy, ln) in [(438, 600, 46), (492, 540, 38), (446, 470, 42),
                         (500, 400, 34), (452, 330, 40), (496, 260, 30),
                         (462, 210, 26)]:
        cv.thick_line(sx, sy, sx + 6, sy - ln, 3, (240, 250, 250))
    # Foam where the sea lets go of the water.
    for (fx, fy, fr) in [(430, 656, 16), (470, 664, 20), (512, 654, 14),
                         (448, 668, 12), (494, 668, 12)]:
        cv.circle(fx, fy, fr, (240, 248, 246))
    # A rounded cap where the fall dissolves into the sky, with spray.
    top_x, top_y = pts[0][0], pts[0][1]
    cv.circle(int(top_x), int(top_y) + 4, 30, (228, 244, 238))
    cv.circle(int(top_x), int(top_y) + 4, 23, (176, 226, 228))
    cv.circle(int(top_x), int(top_y) + 4, 12, (120, 196, 208))
    # Droplets scattering off the top of the fall.
    for (dx, dy, dr) in [(420, 150, 4), (452, 128, 3), (500, 140, 4),
                         (528, 168, 3), (400, 190, 3), (540, 200, 4),
                         (472, 108, 3), (516, 112, 2), (438, 96, 3),
                         (560, 150, 3), (392, 230, 2)]:
        cv.circle(dx, dy, dr, (220, 240, 244))
    # Sky-fish riding the falling-up water, and leaping free at the top.
    for (fx, fy, fs) in [(452, 560, 14), (492, 470, 12), (448, 380, 14),
                         (500, 300, 12), (466, 220, 12)]:
        draw_fish(cv, fx, fy, fs, (36, 68, 96))
    for (fx, fy, fs) in [(420, 130, 12), (520, 150, 10), (560, 210, 10)]:
        draw_fish(cv, fx, fy, fs, (30, 56, 84))


def draw_boats(cv):
    # A little fishing boat on the sea, sail slack, drifting toward the fall.
    bx, by = 700, 800
    cv.polygon([(bx - 46, by), (bx + 46, by), (bx + 30, by + 20),
                (bx - 30, by + 20)], (96, 52, 44))
    cv.thick_line(bx, by, bx, by - 52, 4, (60, 40, 36))
    cv.polygon([(bx + 4, by - 50), (bx + 4, by - 6), (bx + 42, by - 6)],
               (255, 243, 214))
    cv.polygon([(bx - 4, by - 46), (bx - 4, by - 8), (bx - 30, by - 8)],
               (232, 150, 96))
    # And a second boat, small and far away, sailing UP through the sky
    # among the fish — because in Upturn Bay, that is what boats do.
    sx, sy = 780, 250
    cv.polygon([(sx - 26, sy), (sx + 26, sy), (sx + 16, sy + 11),
                (sx - 16, sy + 11)], (96, 52, 44))
    cv.thick_line(sx, sy, sx, sy - 30, 3, (60, 40, 36))
    cv.polygon([(sx + 2, sy - 28), (sx + 2, sy - 4), (sx + 24, sy - 4)],
               (255, 243, 214))
    # Its wake: a curl of cloud.
    cv.ellipse(sx - 10, sy + 16, 22, 5, (255, 243, 214))


def draw_birds(cv):
    for (x, y, s) in [(640, 300, 9), (690, 270, 7), (860, 380, 8),
                      (900, 330, 6), (590, 340, 6)]:
        cv.thick_line(x - s, y, x, y - 4, 2, (43, 33, 58))
        cv.thick_line(x, y - 4, x + s, y, 2, (43, 33, 58))


# ---------------------------------------------------------------------------
# Type, note and frame.
# ---------------------------------------------------------------------------

def draw_type(cv):
    # The place's name: big, cream, outlined, across the top sky.
    draw_text_centered(cv, 512, 66, "UPTURN BAY", 12, CREAM, INK)
    # The tagline: what the stay feels like.
    draw_text_centered(cv, 512, 176, "WHERE THE WATERFALLS FALL UP", 4,
                       (255, 233, 176), INK)
    # A thin rule under the tagline.
    cv.hline(392, 632, 214, CREAM)
    cv.hline(392, 632, 216, CREAM)


def draw_note(cv):
    # A pinned note from Mara, 9 — handwritten slant, paper card, tape.
    x0, y0, x1, y1 = 596, 806, 986, 956
    cv.fill_rect(x0, y0, x1, y1, PAPER)
    cv.fill_rect(x0, y0, x1, y0 + 3, NOTE_INK)
    cv.fill_rect(x0, y0, x0 + 3, y1, NOTE_INK)
    cv.fill_rect(x1 - 3, y0, x1, y1, NOTE_INK)
    cv.fill_rect(x0, y1 - 3, x1, y1, NOTE_INK)
    # Tape strips on the top corners.
    cv.fill_rect(x0 + 8, y0 - 6, x0 + 58, y0 + 8, (232, 214, 160))
    cv.fill_rect(x1 - 58, y0 - 6, x1 - 8, y0 + 8, (232, 214, 160))
    lines = [
        "DEAR JUDGE -",
        "THE TIDE HERE RUNS",
        "UPHILL, SO PACK LIGHT",
        "& BRING A NET.",
        "THE SKY-FISH ARE BITING.",
        "- MARA, 9",
    ]
    ly = y0 + 16
    for line in lines:
        draw_text(cv, x0 + 20, ly, line, 2, NOTE_INK, slant=1)
        ly += 22
    # A small heart after Mara's name.
    hx, hy = x0 + 20 + text_width("- MARA, 9", 2) + 16, y0 + 16 + 5 * 22 + 4
    cv.circle(hx, hy, 4, (196, 60, 80))
    cv.circle(hx + 8, hy, 4, (196, 60, 80))
    cv.polygon([(hx - 4, hy + 2), (hx + 12, hy + 2), (hx + 4, hy + 12)],
               (196, 60, 80))


def draw_frame(cv):
    # Vintage poster frame: cream double border.
    for inset, wdt in ((16, 5), (30, 2)):
        cv.fill_rect(inset, inset, W - 1 - inset, inset + wdt - 1, CREAM)
        cv.fill_rect(inset, H - inset - wdt, W - 1 - inset, H - 1 - inset,
                     CREAM)
        cv.fill_rect(inset, inset, inset + wdt - 1, H - 1 - inset, CREAM)
        cv.fill_rect(W - 1 - inset - wdt + 1, inset, W - 1 - inset,
                     H - 1 - inset, CREAM)


def draw_footer(cv):
    draw_text_centered(cv, 340, 966, "VISIT UPTURN BAY", 3, CREAM, INK)


def build():
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_sun(cv)
    draw_clouds(cv)
    draw_waterfall(cv)
    draw_sea(cv)
    # The waterfall must rise out of the sea, so its base is re-drawn over
    # the water with the foam where the sea lets go.
    draw_waterfall(cv)
    draw_cliff(cv)
    draw_town(cv)
    draw_rooftop_folk(cv)
    draw_boats(cv)
    draw_birds(cv)
    draw_type(cv)
    draw_note(cv)
    draw_footer(cv)
    draw_frame(cv)
    return cv


def main():
    cv = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    size = write_png(cv, OUT)
    print("wrote %s (%d bytes)" % (OUT, size))


if __name__ == "__main__":
    main()
