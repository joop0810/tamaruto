#!/usr/bin/env python3
"""The village backdrops: one scene per village plus the Chunin-exam arena,
drawn from code as flat pixel art, so they are this project's own.

    python3 tools/draw_villages.py            # -> tools/villages/*.png (+ preview.png)
    python3 tools/gen_backs.py                # -> backs.h

Each scene is two layers, drawn at x2 on the 466 px panel:

  skyline  233 x 116, TRANSPARENT where the sky shows. The firmware keeps drawing
           its own sky (dawn, day, dusk, night, sun, moon, clouds) behind it.
  street   233 x 117, the ground the ninja stands on, from the horizon down.

Day and night are drawn separately here but share ONE index image in backs.h:
every pixel becomes a (day colour, night colour) pair, so night costs a second
palette rather than a second bitmap. A lit window is simply a pixel whose day
colour is the wall's window colour and whose night colour is warm yellow.

The main screen draws both layers whole. A fight draws the lower part of the
skyline (rows 40..115) over a band of sky, then the top of the street.

The village list is NOT restated: it comes from VERSIONS in game_data.py, and
a village without a scene here stops the build.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import game_data as D

OUT = os.path.join(HERE, 'villages')
W, SKY_H, GROUND_H = 233, 116, 117
ARENA = 'ARENA'


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def night_c(c):
    r, g, b = c
    return (int(r * 0.32), int(g * 0.36), int(b * 0.55 + 22))


# Colours that keep their brightness at night (they are light sources).
GLOWS = {'glow', 'win_lit', 'torch', 'fire'}


class Pal:
    """Named colours for one scene; win_lit is a window by day, yellow by night."""

    def __init__(self, base, night):
        self.night = night
        self.c = {}
        for k, v in base.items():
            c = rgb(v)
            if night and k not in GLOWS:
                c = night_c(c)
            self.c[k] = c
        self.c['win_lit'] = rgb('#ffd27a') if night else self.c['win']

    def __getitem__(self, k):
        return self.c[k]


COMMON = dict(
    win='#5a6f86', glow='#ffd27a', lantern='#d9473a', wood='#7a4a2c', fence='#9a6a44',
    tree='#4f8a3c', tree_d='#386a2c', tree_l='#73ad55', sakura='#f2a7c0', sakura_d='#d77a9c',
    sakura_l='#fcd3e0', grass='#6aa84f', grass_d='#4f8a3c', torch='#ff9a3a', fire='#ffd27a',
)


def scheme(**kw):
    d = dict(COMMON)
    d.update(kw)
    return d


# ---------------------------------------------------------------------------
# building blocks

def lit(P, rnd, p=0.5):
    return P['win_lit'] if rnd.random() < p else P['win']


def roofed_house(d, P, rnd, x, base, w, h, floors=1):
    d.rectangle([x, base - h, x + w, base], fill=P['wall'])
    d.line([(x + w, base - h), (x + w, base)], fill=P['wall_d'])
    for f in range(floors):
        wy = base - h + 5 + f * 10
        for wx in range(x + 3, x + w - 3, 7):
            d.rectangle([wx, wy, wx + 3, wy + 3], fill=lit(P, rnd, 0.55))
    d.polygon([(x - 4, base - h), (x + w + 4, base - h), (x + w - 2, base - h - 6), (x + 2, base - h - 6)],
              fill=P['roof'])
    d.line([(x - 4, base - h), (x + w + 4, base - h)], fill=P['roof_d'])
    d.line([(x + 2, base - h - 6), (x + w - 2, base - h - 6)], fill=P['roof_l'])
    d.point((x - 5, base - h - 1), fill=P['roof'])
    d.point((x + w + 5, base - h - 1), fill=P['roof'])


def pagoda(d, P, rnd, x, base, w, tiers):
    y = base
    for t in range(tiers):
        tw, tx, th = w - t * 6, x + t * 3, 9
        d.rectangle([tx + 2, y - th, tx + tw - 2, y], fill=P['wall'])
        for wx in range(tx + 4, tx + tw - 4, 6):
            d.rectangle([wx, y - th + 3, wx + 2, y - th + 5], fill=lit(P, rnd))
        y -= th
        d.polygon([(tx - 4, y), (tx + tw + 4, y), (tx + tw - 1, y - 5), (tx + 1, y - 5)], fill=P['roof'])
        d.line([(tx - 4, y), (tx + tw + 4, y)], fill=P['roof_d'])
        d.point((tx - 5, y - 1), fill=P['roof'])
        d.point((tx + tw + 5, y - 1), fill=P['roof'])
        y -= 5
    d.line([(x + w // 2, y), (x + w // 2, y - 5)], fill=P['roof_d'])


def tank_tower(d, P, rnd, x, base, w, h):
    d.rectangle([x, base - h, x + w, base], fill=P['wall'])
    d.rectangle([x + w - 3, base - h, x + w, base], fill=P['wall_d'])
    for y in range(base - h + 4, base - 3, 8):
        for wx in range(x + 2, x + w - 3, 5):
            d.rectangle([wx, y, wx + 2, y + 2], fill=lit(P, rnd, 0.45))
    d.rectangle([x - 1, base - h - 2, x + w + 1, base - h], fill=P['roof'])
    tx = x + w // 2 - 4
    d.rectangle([tx, base - h - 10, tx + 8, base - h - 2], fill=P['tank'])
    d.rectangle([tx + 6, base - h - 10, tx + 8, base - h - 2], fill=P['tank_d'])
    d.line([(tx - 1, base - h - 10), (tx + 9, base - h - 10)], fill=P['tank_d'])


def round_tree(d, P, x, base, r, sakura=False):
    d.rectangle([x - 1, base - r - 2, x + 1, base], fill=P['wood'])
    c, cd, cl = ((P['sakura'], P['sakura_d'], P['sakura_l']) if sakura
                 else (P['tree'], P['tree_d'], P['tree_l']))
    d.ellipse([x - r, base - 2 * r - 4, x + r, base - 4], fill=c)
    d.ellipse([x - r + 2, base - 2 * r - 1, x + r - 1, base - 6], fill=cd)
    d.ellipse([x - r + 1, base - 2 * r - 5, x + r - 3, base - r - 3], fill=c)
    d.ellipse([x - r // 2, base - 2 * r - 4, x + r // 3, base - r - 4], fill=cl)


def pine(d, P, x, base, h, col, col_d):
    d.rectangle([x - 1, base - 5, x + 1, base], fill=P['wood'])
    for i in range(3):
        top = base - h + i * (h // 4)
        half = 4 + i * 3
        d.polygon([(x, top), (x - half, top + h // 3 + 2), (x + half, top + h // 3 + 2)], fill=col)
        d.line([(x, top + 1), (x + half - 1, top + h // 3 + 1)], fill=col_d)


def string_lanterns(d, P, x0, x1, y0, night):
    for x in range(x0, x1, 2):
        y = y0 + int(3 * math.sin((x - x0) / (x1 - x0) * math.pi))
        d.point((x, y), fill=P['wood'])
    for x in range(x0 + 6, x1 - 4, 12):
        y = y0 + int(3 * math.sin((x - x0) / (x1 - x0) * math.pi))
        d.rectangle([x, y + 1, x + 2, y + 4], fill=P['glow'] if night else P['lantern'])


def far_band(d, P, rnd, base, height, amp, key='far', step=6):
    pts = [(0, base)]
    for x in range(0, W + step, step):
        pts.append((x, base - height - int(amp * math.sin(x / 9.0)) - rnd.randrange(3)))
    pts.append((W, base))
    d.polygon(pts, fill=P[key])


# ---------------------------------------------------------------------------
# KONOHA -- the hidden leaf: red roofs, the carved cliff, water-tank towers

KONOHA = scheme(
    rock='#b59a7a', rock_d='#8f7658', rock_l='#d2bb98',
    wall='#efe2c4', wall_d='#cdb994', roof='#c0503a', roof_d='#8e3428', roof_l='#de7a58',
    tank='#9aa6a8', tank_d='#6f7a7c', far='#8fb9a0',
    street='#d8c29a', street_d='#bfa67c', street_l='#e9d8b4',
)


def konoha_sky(d, P, rnd):
    base = SKY_H
    far_band(d, P, rnd, base, 24, 4)
    # the cliff: four rounded heads, not portraits
    x0, cb, w, h = 20, base - 18, 120, 44
    d.polygon([(x0, cb), (x0 + 6, cb - h + 10), (x0 + 18, cb - h), (x0 + w - 18, cb - h),
               (x0 + w - 6, cb - h + 8), (x0 + w, cb)], fill=P['rock'])
    for i in range(3):
        y = cb - 6 - i * 7
        d.line([(x0 + 4 + i * 3, y), (x0 + w - 4 - i * 3, y)], fill=P['rock_d'])
    hw = (w - 24) // 4
    for i in range(4):
        cx, top = x0 + 12 + hw * i + hw // 2, cb - h - 1
        d.ellipse([cx - hw // 2 + 2, top + 1, cx + hw // 2 - 2, top + 22], fill=P['rock_l'])
        d.rectangle([cx - hw // 2 + 4, top + 12, cx + hw // 2 - 4, top + 24], fill=P['rock_l'])
        d.line([(cx - 4, top + 9), (cx - 1, top + 9)], fill=P['rock_d'])
        d.line([(cx + 1, top + 9), (cx + 4, top + 9)], fill=P['rock_d'])
        d.line([(cx - 1, top + 15), (cx + 1, top + 15)], fill=P['rock_d'])
        d.line([(cx - hw // 2 + 2, top + 24), (cx + hw // 2 - 2, top + 24)], fill=P['rock_d'])
    tank_tower(d, P, rnd, 4, base - 6, 16, 42)
    pagoda(d, P, rnd, 148, base - 8, 36, 3)
    tank_tower(d, P, rnd, 200, base - 4, 14, 36)
    roofed_house(d, P, rnd, 186, base - 4, 16, 18)
    for x, w, h in [(0, 22, 20), (26, 30, 26), (62, 20, 18), (152, 24, 22), (182, 26, 26), (214, 22, 20)]:
        roofed_house(d, P, rnd, x, base, w, h, 2 if h > 21 else 1)
    string_lanterns(d, P, 2, 84, base - 21, P.night)
    string_lanterns(d, P, 150, 232, base - 21, P.night)
    round_tree(d, P, 98, base, 10, sakura=True)
    round_tree(d, P, 136, base - 2, 8)


def konoha_ground(d, P, rnd):
    d.rectangle([0, 0, W, 5], fill=P['grass'])
    for x in range(0, W, 3):
        d.point((x, 5 + (x % 2)), fill=P['grass_d'])
    lane(d, P, 30, 0.9)
    specks(d, P, rnd, 70, 'street_d')
    for _ in range(26):
        d.point((rnd.randrange(W), rnd.randrange(8, GROUND_H)), fill=P['sakura'])
    side_fences(d, P)


# ---------------------------------------------------------------------------
# SUNA -- the hidden sand: domed adobe, the round tower, the canyon walls

SUNA = scheme(
    wall='#d9b47e', wall_d='#b48d58', roof='#c79a62', roof_d='#9a7444', roof_l='#e8c690',
    cliff='#b98a56', cliff_d='#94683c', cliff_l='#d2a672', far='#e3c48f', far_d='#cfa972',
    pipe='#8a6a48', win='#5a4630', banner='#4f86b8',
    street='#e6cf9c', street_d='#cdb07a', street_l='#f2e0b6',
)


def dome_house(d, P, rnd, x, base, w, h):
    d.rectangle([x, base - h, x + w, base], fill=P['wall'])
    d.rectangle([x + w - 3, base - h, x + w, base], fill=P['wall_d'])
    d.pieslice([x - 1, base - h - w // 2, x + w + 1, base - h + w // 2], 180, 360, fill=P['roof'])
    d.arc([x - 1, base - h - w // 2, x + w + 1, base - h + w // 2], 200, 260, fill=P['roof_l'])
    for wx in range(x + 3, x + w - 3, 6):
        d.ellipse([wx, base - h + 4, wx + 3, base - h + 7], fill=lit(P, rnd, 0.5))
    if h > 14:
        d.rectangle([x + w // 2 - 2, base - 7, x + w // 2 + 2, base], fill=P['win'])


def suna_sky(d, P, rnd):
    base = SKY_H
    # dunes far away
    pts = [(0, base)]
    for x in range(0, W + 8, 8):
        pts.append((x, base - 16 - int(6 * math.sin(x / 21.0))))
    pts.append((W, base))
    d.polygon(pts, fill=P['far'])
    # canyon walls that frame the village
    for side in (0, 1):
        xs = [0, 34] if side == 0 else [W - 34, W]
        d.polygon([(xs[0], base), (xs[0], base - 70), (xs[1] - 10, base - 62), (xs[1], base)]
                  if side == 0 else
                  [(xs[0], base), (xs[0] + 10, base - 62), (xs[1], base - 70), (xs[1], base)],
                  fill=P['cliff'])
        for i in range(4):
            y = base - 14 - i * 13
            d.line([(xs[0] + 2, y), (xs[1] - 2, y + 2)], fill=P['cliff_d'])
        d.line([(xs[1] - 10 if side == 0 else xs[0] + 10, base - 62), (xs[1] if side == 0 else xs[0], base)],
               fill=P['cliff_l'])
    # the big round tower in the middle
    tx, tw, th = 92, 48, 46
    d.rectangle([tx, base - th, tx + tw, base], fill=P['wall'])
    d.rectangle([tx + tw - 6, base - th, tx + tw, base], fill=P['wall_d'])
    d.pieslice([tx - 2, base - th - 18, tx + tw + 2, base - th + 18], 180, 360, fill=P['roof'])
    d.arc([tx - 2, base - th - 18, tx + tw + 2, base - th + 18], 200, 250, fill=P['roof_l'])
    d.ellipse([tx + tw // 2 - 7, base - th + 4, tx + tw // 2 + 7, base - th + 18], fill=P['banner'])
    d.ellipse([tx + tw // 2 - 4, base - th + 7, tx + tw // 2 + 4, base - th + 15], fill=P['wall'])
    for y in range(base - th + 22, base - 4, 8):
        for wx in range(tx + 4, tx + tw - 4, 7):
            d.ellipse([wx, y, wx + 3, y + 3], fill=lit(P, rnd, 0.45))
    # pipes between the houses
    d.line([(40, base - 26), (92, base - 30)], fill=P['pipe'])
    d.line([(140, base - 30), (192, base - 24)], fill=P['pipe'])
    for x, w, h in [(30, 22, 18), (56, 18, 24), (146, 20, 22), (170, 24, 16), (198, 18, 20)]:
        dome_house(d, P, rnd, x, base - 2, w, h)
    for x, w, h in [(10, 20, 12), (74, 16, 10), (204, 22, 12)]:
        dome_house(d, P, rnd, x, base, w, h)


def suna_ground(d, P, rnd):
    lane(d, P, 34, 0.9)
    # ripples in the sand
    for y in range(6, GROUND_H, 7):
        off = (y * 11) % 17
        for x in range(off, W, 17):
            d.arc([x, y, x + 10, y + 4], 200, 340, fill=P['street_d'])
    specks(d, P, rnd, 30, 'street_d')


# ---------------------------------------------------------------------------
# KIRI -- the hidden mist: stilt houses over water, mountains in fog

KIRI = scheme(
    wall='#b9c4c8', wall_d='#93a0a6', roof='#4f7a8f', roof_d='#3a5c6c', roof_l='#6f9ab0',
    far='#9db4bf', far_d='#88a2ae', mist='#d6e2e6', water='#5f8ea6', water_d='#4b7790',
    water_l='#8fb6c8', plank='#8a6a4c', plank_d='#6c5038', post='#5a4232', win='#3f5866',
    street='#8a6a4c', street_d='#6c5038', street_l='#9e7c5a',
)


def stilt_house(d, P, rnd, x, base, w, h):
    d.rectangle([x + 2, base - 6, x + 3, base], fill=P['post'])
    d.rectangle([x + w - 3, base - 6, x + w - 2, base], fill=P['post'])
    top = base - 6
    d.rectangle([x, top - h, x + w, top], fill=P['wall'])
    d.line([(x + w, top - h), (x + w, top)], fill=P['wall_d'])
    for wx in range(x + 3, x + w - 3, 6):
        d.rectangle([wx, top - h + 4, wx + 2, top - h + 7], fill=lit(P, rnd, 0.5))
    d.polygon([(x - 3, top - h), (x + w + 3, top - h), (x + w // 2, top - h - 8)], fill=P['roof'])
    d.line([(x - 3, top - h), (x + w // 2, top - h - 8)], fill=P['roof_l'])


def kiri_sky(d, P, rnd):
    base = SKY_H
    # mountains in fog, two layers
    for layer, (hgt, key) in enumerate(((52, 'far'), (34, 'far_d'))):
        pts = [(0, base)]
        for x in range(0, W + 10, 10):
            pts.append((x, base - hgt + int(12 * abs(math.sin(x / (27.0 - layer * 6)))) - rnd.randrange(3)))
        pts.append((W, base))
        d.polygon(pts, fill=P[key])
    for y in (base - 40, base - 30, base - 22):
        for x in range((y * 7) % 20, W, 26):
            d.line([(x, y), (x + 15, y)], fill=P['mist'])
    # the water the village stands in
    d.rectangle([0, base - 12, W, base], fill=P['water'])
    for y in range(base - 10, base, 4):
        for x in range((y * 5) % 9, W, 14):
            d.line([(x, y), (x + 5, y)], fill=P['water_l'])
    # the round tower with the blue roof
    tx, tw, th = 120, 30, 40
    d.rectangle([tx + 3, base - 6, tx + 5, base], fill=P['post'])
    d.rectangle([tx + tw - 5, base - 6, tx + tw - 3, base], fill=P['post'])
    d.rectangle([tx, base - 6 - th, tx + tw, base - 6], fill=P['wall'])
    d.rectangle([tx + tw - 5, base - 6 - th, tx + tw, base - 6], fill=P['wall_d'])
    for y in range(base - th, base - 10, 8):
        for wx in range(tx + 4, tx + tw - 5, 6):
            d.rectangle([wx, y, wx + 2, y + 3], fill=lit(P, rnd, 0.5))
    d.pieslice([tx - 4, base - 6 - th - 14, tx + tw + 4, base - 6 - th + 14], 180, 360, fill=P['roof'])
    d.arc([tx - 4, base - 6 - th - 14, tx + tw + 4, base - 6 - th + 14], 200, 250, fill=P['roof_l'])
    for x, w, h in [(4, 22, 16), (32, 18, 22), (58, 24, 14), (90, 20, 18), (160, 22, 20), (188, 18, 14), (210, 22, 18)]:
        stilt_house(d, P, rnd, x, base, w, h)
    # mist drifting in front
    for x in range(6, W, 30):
        d.line([(x, base - 9), (x + 18, base - 9)], fill=P['mist'])


def kiri_ground(d, P, rnd):
    # a boardwalk over the water: water at the sides, planks in the middle
    d.rectangle([0, 0, W, GROUND_H], fill=P['water'])
    for y in range(2, GROUND_H, 5):
        for x in range((y * 7) % 11, W, 16):
            d.line([(x, y), (x + 6, y)], fill=P['water_l'])
    for y in range(0, GROUND_H):
        half = 40 + int(y * 0.85)
        d.line([(W // 2 - half, y), (W // 2 + half, y)], fill=P['plank'])
    for y in range(4, GROUND_H, 6):
        half = 40 + int(y * 0.85)
        d.line([(W // 2 - half, y), (W // 2 + half, y)], fill=P['plank_d'])
    for y in range(0, GROUND_H, 12):
        half = 40 + int(y * 0.85)
        for x in (W // 2 - half, W // 2 + half):
            d.rectangle([x - 1, y, x + 1, y + 6], fill=P['post'])


# ---------------------------------------------------------------------------
# OTO -- the hidden sound: dark forest, a rock hideout, torches

OTO = scheme(
    rock='#6a5a78', rock_d='#4e4060', rock_l='#857496',
    far='#3f4a5e', far_d='#323b4d', pine='#2f4a3e', pine_d='#25392f', cave='#1c1824',
    fog='#7d6f96', win='#2a2434', wall='#6a5a78', wall_d='#4e4060',
    street='#5c5266', street_d='#4a4154', street_l='#6e6378',
)


def oto_sky(d, P, rnd):
    base = SKY_H
    far_band(d, P, rnd, base, 40, 6)
    for x in range(0, W, 9):
        pine(d, P, x + rnd.randrange(4), base - 14, 30 + rnd.randrange(10), P['far_d'], P['far'])
    # the hideout: a rock mound with a cave mouth in the middle
    d.ellipse([60, base - 62, 172, base + 30], fill=P['rock'])
    d.ellipse([66, base - 58, 120, base - 20], fill=P['rock_l'])
    for i in range(5):
        y = base - 50 + i * 9
        d.line([(70 + i * 2, y), (162 - i * 2, y + 3)], fill=P['rock_d'])
    d.pieslice([98, base - 30, 134, base + 6], 180, 360, fill=P['cave'])
    d.rectangle([98, base - 12, 134, base], fill=P['cave'])
    # torches either side of the cave
    for tx in (90, 140):
        d.rectangle([tx, base - 18, tx + 1, base], fill=P['wood'])
        d.rectangle([tx - 1, base - 22, tx + 2, base - 18], fill=P['torch'])
        d.point((tx, base - 23), fill=P['fire'])
    # near forest at the sides
    for x in list(range(2, 58, 11)) + list(range(176, W, 11)):
        pine(d, P, x, base, 40 + rnd.randrange(12), P['pine'], P['pine_d'])
    for x in range(0, W, 24):
        d.line([(x, base - 6), (x + 14, base - 6)], fill=P['fog'])


def oto_ground(d, P, rnd):
    lane(d, P, 26, 0.8)
    specks(d, P, rnd, 90, 'street_d')
    for _ in range(14):
        x, y = rnd.randrange(W), rnd.randrange(8, GROUND_H - 4)
        d.ellipse([x, y, x + 5, y + 3], fill=P['rock_d'])


# ---------------------------------------------------------------------------
# ARENA -- the Chunin exam finals: a walled stadium, the crowd on the stands

ARENA_S = scheme(
    wall='#cdb98f', wall_d='#a8946c', roof='#c0503a', roof_d='#8e3428', roof_l='#de7a58',
    stand='#9a8a70', stand_d='#7d6e56', far='#5f8f4a',
    street='#c9b07e', street_d='#ad9462', street_l='#dcc69a', ring='#e8dcbc',
)
CROWD = ['#d9473a', '#4f86b8', '#f4e27a', '#6aa84f', '#efe2c4', '#8a5aa8', '#e89a4a']


def arena_sky(d, P, rnd):
    base = SKY_H
    for x in range(0, W, 12):
        round_tree(d, P, x + 6, base - 40, 9 + rnd.randrange(3))
    # the stands: tiers of crowd behind a wall
    for tier in range(5):
        y = base - 60 + tier * 8
        d.rectangle([0, y, W, y + 7], fill=P['stand'] if tier % 2 else P['stand_d'])
        for x in range(1 + tier % 2, W, 3):
            c = CROWD[(x * 7 + tier * 3) % len(CROWD)]
            col = rgb(c) if not P.night else night_c(rgb(c))
            d.rectangle([x, y + 2, x + 1, y + 4], fill=col)
    # roofed boxes for the Kage at the top centre
    d.rectangle([92, base - 72, 140, base - 60], fill=P['wall'])
    d.polygon([(88, base - 72), (144, base - 72), (138, base - 78), (94, base - 78)], fill=P['roof'])
    d.line([(88, base - 72), (144, base - 72)], fill=P['roof_d'])
    # the arena wall
    d.rectangle([0, base - 20, W, base], fill=P['wall'])
    d.line([(0, base - 20), (W, base - 20)], fill=P['wall_d'])
    for x in range(0, W, 18):
        d.line([(x, base - 19), (x, base)], fill=P['wall_d'])
    # a gate in the middle
    d.rectangle([104, base - 16, 128, base], fill=P['wall_d'])
    d.pieslice([104, base - 22, 128, base - 10], 180, 360, fill=P['wall_d'])


def arena_ground(d, P, rnd):
    specks(d, P, rnd, 80, 'street_d')
    # the marked ring of the arena
    d.ellipse([20, 18, W - 20, GROUND_H + 70], outline=P['ring'])
    d.ellipse([21, 19, W - 21, GROUND_H + 69], outline=P['ring'])


# ---------------------------------------------------------------------------
# shared ground pieces

def lane(d, P, top_half, grow):
    for y in range(8, GROUND_H):
        half = top_half + int((y - 8) * grow)
        d.line([(W // 2 - half, y), (W // 2 + half, y)], fill=P['street_l'])


def specks(d, P, rnd, n, key):
    for _ in range(n):
        x, y = rnd.randrange(W), rnd.randrange(10, GROUND_H)
        d.line([(x, y), (x + rnd.randrange(2, 5), y)], fill=P[key])


def side_fences(d, P):
    for side in (0, 1):
        for i in range(8):
            x = 4 + i * 6 if side == 0 else W - 8 - i * 6
            d.rectangle([x, 8, x + 1, 15], fill=P['fence'])
        d.line([(2 if side == 0 else W - 50, 10), (50 if side == 0 else W - 2, 10)], fill=P['fence'])


SCENES = {
    'KONOHA': (KONOHA, konoha_sky, konoha_ground),
    'SUNA':   (SUNA, suna_sky, suna_ground),
    'KIRI':   (KIRI, kiri_sky, kiri_ground),
    'OTO':    (OTO, oto_sky, oto_ground),
    ARENA:    (ARENA_S, arena_sky, arena_ground),
}


def village_names():
    """Every village in game_data.VERSIONS, in order, then the arena."""
    names = [v[0] for v in D.VERSIONS]
    missing = [n for n in names if n not in SCENES]
    if missing:
        raise SystemExit('no village scene for %s -- draw one in tools/draw_villages.py' % missing)
    return names + [ARENA]


def draw(name, night):
    base, sky_fn, ground_fn = SCENES[name]
    P = Pal(base, night)
    sky = Image.new('RGBA', (W, SKY_H), (0, 0, 0, 0))
    sky_fn(ImageDraw.Draw(sky), P, random.Random(name + 'sky'))
    ground = Image.new('RGB', (W, GROUND_H), P['street'])
    ground_fn(ImageDraw.Draw(ground), P, random.Random(name + 'ground'))
    return sky, ground


def preview(path):
    """Every scene, day and night, on a round panel with a simple sky."""
    names = village_names()
    S = Image.new('RGB', (len(names) * 240, 2 * 240), (24, 24, 30))
    for i, n in enumerate(names):
        for j, night in enumerate((False, True)):
            sky, ground = draw(n, night)
            p = Image.new('RGB', (466, 466))
            dd = ImageDraw.Draw(p)
            top, bot = (rgb('#0c1224'), rgb('#1e2646')) if night else (rgb('#8fc8ea'), rgb('#dceee6'))
            for y in range(0, 232, 8):
                dd.rectangle([0, y, 466, y + 8], fill=tuple(int(a + (b - a) * y / 232) for a, b in zip(top, bot)))
            s2 = sky.resize((466, 232), Image.NEAREST)
            p.paste(s2, (0, 0), s2)
            p.paste(ground.resize((466, 234), Image.NEAREST), (0, 232))
            m = Image.new('L', (466, 466), 0)
            ImageDraw.Draw(m).ellipse([0, 0, 465, 465], fill=255)
            out = Image.new('RGB', (466, 466), (24, 24, 30))
            out.paste(p, (0, 0), m)
            S.paste(out.resize((233, 233), Image.NEAREST), (i * 240 + 3, j * 240 + 3))
    S.save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.png'):
            os.remove(os.path.join(OUT, f))
    names = village_names()
    for n in names:
        for night in (False, True):
            sky, ground = draw(n, night)
            tag = n.lower() + ('_night' if night else '_day')
            sky.save(os.path.join(OUT, tag + '_sky.png'))
            ground.save(os.path.join(OUT, tag + '_ground.png'))
    if '--preview' in sys.argv:
        preview(os.path.join(OUT, 'preview.png'))
    print('drew %d scenes (%s) into %s' % (len(names), ', '.join(names), OUT))


if __name__ == '__main__':
    main()
