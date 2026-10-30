#!/usr/bin/env python3
"""Turns the Naruto: Ninja Council sprite sheets into the firmware's TPK2 sprites.

    python3 tools/pack_sprites.py              # pack everything
    python3 tools/pack_sprites.py --sheet      # also write tools/sprites/check.png

SOURCE ART
  The Game Boy Advance sprite sheets of Naruto: Ninja Council 1 and 2 as
  collected on The Spriters Resource (one sheet per character, ripped by
  Deekman and others). They are (c) Masashi Kishimoto / Shueisha / Bandai --
  see CREDITS.md -- and are NOT in this repository: put them in
  tools/sprites_src/nc1/<name>.gif and tools/sprites_src/nc2/<name>.gif
  (README "Sprites" says where to get them). The packed result ships in
  web/sprites-<village>.pak, so nobody needs the sheets to play.

  The sheets are hand-arranged, not a grid. tools/sprites/segment.py cuts each
  one into frames (connected blobs on the background colour, grouped into
  rows), and tools/sprites/picks.json says which frames are which pose:

      "nc2_naruto": {"idle": ["0.0", "0.1", ...], "walk": [...],
                     "attack": "9.3", "hurt": "...", "down": "...", "happy": "8.3"}

  A frame is "row.col" in that sheet's segmentation. "row.col/k" takes the
  k-th of several figures that were drawn so close together that they came out
  as one blob (split at their empty columns). A key the picks leave out is
  guessed from the sheet's layout (row 0 stance, row 1 walk, the widest
  standing frame as the attack, the flattest frame as "down"); "walk": null
  means "walks in its stance".

  A roster entry whose sprite key is not a sheet name ("tobirama",
  "hashirama") is an ALIAS in picks.json: {"sheet": "nc2_1st_2nd_hokage", ...}.

WHAT IT WRITES
  tools/sdcard/mons/pNNN.bin    normal colours
  tools/sdcard/mons/psNNN.bin   the rare colour variant (hue-shifted)
  noart.h                       ninja with no art: never hatched or met

LOOK
  The sheets' own pixels, mirrored to face LEFT like every sprite the engine
  draws, with a 1-px pale rim so dark outfits still read on the night sky.
  All frames of one ninja share one canvas, aligned on the feet.
"""
import colorsys
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'sprites'))
import game_data as D
import segment

SRC = os.path.join(HERE, 'sprites_src')
OUT = os.path.join(HERE, 'sdcard', 'mons')
PICKS = os.path.join(HERE, 'sprites', 'picks.json')
RIM = (0xf4, 0xf6, 0xee)
VARIANT_HUE = 0.42
MAXF = 4                     # frames kept per looping action


# ---------------------------------------------------------------------------
class Sheet:
    def __init__(self, key):
        game, name = key.split('_', 1)
        path = os.path.join(SRC, game, name + '.gif')
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.im, self.a, self.bg, self.lab, self.rows = segment.frames(path)

    def blob(self, ref):
        """RGBA array of one frame, background cleared."""
        part = None
        if '/' in ref:
            ref, part = ref.split('/')
            part = int(part)
        r, c = map(int, ref.split('.'))
        b = self.rows[r][c]
        x0, y0, x1, y1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
        sub = self.a[y0:y1, x0:x1].copy()
        m = ((self.lab[y0:y1, x0:x1] == b['id']) & np.any(sub[..., :3] != self.bg, -1)
             & (sub[..., 3] > 0))
        sub[..., 3] = np.where(m, 255, 0)
        if part is not None:
            cols = m.any(0)
            runs, start = [], None
            for x, on in enumerate(list(cols) + [False]):
                if on and start is None:
                    start = x
                elif not on and start is not None:
                    runs.append((start, x))
                    start = None
            runs = [rr for rr in runs if rr[1] - rr[0] >= 6]
            a0, a1 = runs[min(part, len(runs) - 1)]
            sub = sub[:, a0:a1]
        ys, xs = np.nonzero(sub[..., 3])
        return sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def guess(rows):
    """The layout most Ninja Council sheets share."""
    def row_ok(r):
        hs = [b['h'] for b in r]
        return len(r) >= 2 and max(hs) - min(hs) <= 8
    idle_r = next((ri for ri, r in enumerate(rows) if row_ok(r)), 0)
    H = int(np.median([b['h'] for b in rows[idle_r]]))
    W = int(np.median([b['w'] for b in rows[idle_r]]))
    idle = [f'{idle_r}.{ci}' for ci in range(len(rows[idle_r]))]
    walk_r = next((ri for ri in range(idle_r + 1, len(rows)) if row_ok(rows[ri])), idle_r)
    walk = [f'{walk_r}.{ci}' for ci in range(len(rows[walk_r]))]
    flat = [(ri, ci, b) for ri, r in enumerate(rows) for ci, b in enumerate(r)]
    cand = [(b['w'], ri, ci) for ri, ci, b in flat
            if walk_r < ri < max(walk_r + 8, len(rows) // 2) and abs(b['h'] - H) <= H * 0.3]
    atk = '%d.%d' % max(cand)[1:] if cand else idle[0]
    cand = [(b['w'] / b['h'], ri, ci) for ri, ci, b in flat if b['h'] < H * 0.6 and b['w'] > W * 1.2]
    down = '%d.%d' % max(cand)[1:] if cand else idle[0]
    dr = int(down.split('.')[0])
    hurt = f'{dr}.0' if rows[dr][0]['h'] > H * 0.6 else idle[0]
    return dict(idle=idle, walk=walk, attack=atk, hurt=hurt, down=down, happy=idle[0])


def poses(key, picks, cache):
    p = dict(picks.get(key, {}))
    sheet_key = p.pop('sheet', key)
    if sheet_key not in cache:
        cache[sheet_key] = Sheet(sheet_key)
    sh = cache[sheet_key]
    g = guess(sh.rows)
    for k, v in p.items():
        if v is not None:
            g[k] = v
    if 'walk' in p and p['walk'] is None:
        g['walk'] = g['idle']
    lst = lambda v: v if isinstance(v, list) else [v]
    take = lambda refs: [sh.blob(r) for r in lst(refs)[:MAXF]]
    return {k: take(g[k]) for k in ('idle', 'walk', 'attack', 'hurt', 'down', 'happy')}


# ---------------------------------------------------------------------------
def feet_x(a):
    """Horizontal anchor: the middle of the lowest third of the figure, which
    is the feet -- a sword or a jutsu sticking out sideways must not shift it."""
    al = a[..., 3] > 0
    h = al.shape[0]
    xs = np.nonzero(al[h * 2 // 3:].any(0))[0]
    if not len(xs):
        xs = np.nonzero(al.any(0))[0]
    return (xs.min() + xs.max()) / 2


def canvas(all_frames, pad=2):
    """One canvas for all frames: bottoms aligned, feet on the centre line."""
    left = max(feet_x(f) for f in all_frames)
    right = max(f.shape[1] - feet_x(f) for f in all_frames)
    # symmetric about the feet: the firmware centres the canvas on the spot
    # the ninja stands on, so an attack reaching out to one side must not push
    # the body off that spot
    half = int(np.ceil(max(left, right)))
    H = max(f.shape[0] for f in all_frames) + 2 * pad
    W = 2 * half + 2 * pad
    ax = half + pad
    return W, H, ax, pad


def add_rim(a):
    al = a[..., 3] > 0
    grow = al.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            grow |= np.roll(np.roll(al, dy, 0), dx, 1)
    rim = grow & ~al
    a = a.copy()
    a[rim] = (*RIM, 255)
    return a


def place(f, W, H, ax, pad):
    out = np.zeros((H, W, 4), np.uint8)
    x = int(round(ax - feet_x(f)))
    y = H - pad - f.shape[0]
    x = max(0, min(W - f.shape[1], x))
    out[y:y + f.shape[0], x:x + f.shape[1]] = f
    return add_rim(out[:, ::-1])          # the sheets face right, the engine left


def to_grid(a):
    h, w = a.shape[:2]
    return [[tuple(int(v) for v in a[y, x, :3]) if a[y, x, 3] else None for x in range(w)]
            for y in range(h)]


def shift(g, dx, dy):
    h, w = len(g), len(g[0])
    return [[g[y - dy][x - dx] if 0 <= x - dx < w and 0 <= y - dy < h else None
             for x in range(w)] for y in range(h)]


def mirror(g):
    return [list(reversed(r)) for r in g]


def actions(P):
    idle, walk = P['idle'], P['walk']
    i1, i2 = idle[0], idle[min(1, len(idle) - 1)]
    happy, atk, hurt, down = P['happy'][0], P['attack'][0], P['hurt'][0], P['down'][0]
    w = walk if len(walk) >= 2 else [i1, i2]
    ms = lambda n, t: [t] * n
    return [
        (0, idle, ms(len(idle), 260)),                                      # Idle
        (1, w, ms(len(w), 160)),                                            # WalkL
        (2, [mirror(f) for f in w], ms(len(w), 160)),                       # WalkR
        (3, [down, down], [900, 900]),                                      # Sleep
        (4, [i1, happy, i1, happy], [200, 200, 200, 200]),                  # Eat
        (5, [shift(hurt, -2, 0), shift(hurt, 2, 0), hurt], [90, 90, 220]),  # Hurt
        (6, [i1, shift(atk, -4, 0), atk, i1], [120, 140, 220, 160]),        # Attack
        (7, [happy, i1, happy, i1], [300, 300, 300, 300]),                  # Pose
        (9, [happy, i1], [300, 400]),                                       # Nod
        (10, [i1, happy, i2, i1], [300, 300, 400, 300]),                    # DeepBreath
    ]


def hue_shift(c):
    r, g, b = (v / 255 for v in c)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.15 or l < 0.08 or l > 0.92:
        return c
    r, g, b = colorsys.hls_to_rgb((h + VARIANT_HUE) % 1.0, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def rgb565(c):
    r, g, b = c
    return (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3)


def write_tpk2(path, acts, recolour=None):
    pal, idx = [], {}
    def key(c):
        c = recolour(c) if recolour and c != RIM else c
        k = rgb565(c)
        if k not in idx:
            idx[k] = len(pal)
            pal.append(k)
        return idx[k]
    blocks = []
    for aid, frames, ms in acts:
        h, w = len(frames[0]), len(frames[0][0])
        data = bytearray()
        for fr in frames:
            for row in fr:
                for c in row:
                    data.append(0xFF if c is None else key(c))
        blocks.append((aid, w, h, frames, ms, bytes(data)))
    if len(pal) > 255:
        raise SystemExit('%s: %d colours' % (path, len(pal)))
    with open(path, 'wb') as fh:
        fh.write(b'TPK2')
        fh.write(struct.pack('<BH', len(blocks), len(pal)))
        for c in pal:
            fh.write(struct.pack('<H', c))
        for aid, w, h, frames, ms, data in blocks:
            fh.write(struct.pack('<4B', aid, w, h, len(frames)))
            fh.write(struct.pack('<%dH' % len(frames), *ms))
            fh.write(data)


def write_noart(noart):
    with open(os.path.join(HERE, '..', 'noart.h'), 'w') as f:
        f.write('// GENERATED by tools/pack_sprites.py. Do not edit.\n//\n'
                '// Ninja with no sprite yet. They keep their dex numbers but never\n'
                '// hatch and never turn up in a mission: a fighter that can only\n'
                '// draw as a number is a defect.\n'
                '#pragma once\n#include <stdint.h>\n\n')
        f.write('#define NO_ART_COUNT %d\n' % len(noart))
        f.write('static const int16_t NO_ART[NO_ART_COUNT ? NO_ART_COUNT : 1] = {\n  %s\n};\n\n'
                % (', '.join(map(str, noart)) or '0'))
        f.write('static inline bool speciesHasArt(int16_t d) {\n'
                '  for (int i = 0; i < NO_ART_COUNT; i++)\n'
                '    if (NO_ART[i] == d) return false;\n'
                '  return true;\n}\n')


def main():
    os.makedirs(OUT, exist_ok=True)
    picks = json.load(open(PICKS))
    cache, noart, tiles = {}, [], []
    for num, ver, key, disp, *_ in D.ROSTER:
        try:
            P = poses(key, picks, cache)
        except FileNotFoundError as e:
            noart.append(num)
            print(f'  {num:3d} {disp:15s} -- no sheet ({e})')
            continue
        flat = [f for v in P.values() for f in v]
        W, H, ax, pad = canvas(flat)
        if W > 255 or H > 255:
            raise SystemExit(f'{disp}: canvas {W}x{H} is over the 255 the format allows')
        G = {k: [to_grid(place(f, W, H, ax, pad)) for f in v] for k, v in P.items()}
        acts = actions(G)
        write_tpk2(os.path.join(OUT, f'p{num:03d}.bin'), acts)
        write_tpk2(os.path.join(OUT, f'ps{num:03d}.bin'), acts, hue_shift)
        print(f'  {num:3d} {disp:15s} {W}x{H}')
        if '--sheet' in sys.argv:
            row = [place(P[k][0], W, H, ax, pad) for k in ('idle', 'walk', 'attack', 'hurt', 'down', 'happy')]
            t = Image.new('RGBA', (W * 6 + 10, H + 12), (40, 40, 50, 255))
            for i, a in enumerate(row):
                t.alpha_composite(Image.fromarray(a), (i * (W + 2), 12))
            ImageDraw.Draw(t).text((2, 0), f'{num} {disp}', fill=(255, 255, 0, 255))
            tiles.append(t)
    write_noart(noart)
    if tiles:
        cw = max(t.width for t in tiles)
        ch = max(t.height for t in tiles)
        cols = 3
        S = Image.new('RGB', (cw * cols, ch * ((len(tiles) + cols - 1) // cols)), (20, 20, 24))
        for i, t in enumerate(tiles):
            S.paste(t, ((i % cols) * cw, (i // cols) * ch), t)
        S.save(os.path.join(HERE, 'sprites', 'check.png'))
    print(f'{len(D.ROSTER) - len(noart)} packed, {len(noart)} without art: {noart}')


if __name__ == '__main__':
    main()
