#!/usr/bin/env python3
"""Cut a Spriters-Resource sheet into frames.

    python3 -I segment.py <sheet.gif> <out_prefix>

Writes <out_prefix>.json (frame boxes grouped into rows) and <out_prefix>.png
(a contact sheet with every frame labelled r<row>.<col>), so frames can be
picked by eye.
"""
import json, sys
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def background(a):
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return Counter(map(tuple, edge)).most_common(1)[0][0]


def frames(path):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    bg = background(a[..., :3])
    fg = np.any(a[..., :3] != bg, axis=-1) & (a[..., 3] > 0)
    # join pieces of one pose (a sword, a fist) that are a pixel or two apart
    joined = ndimage.binary_dilation(fg, iterations=2)
    lab, n = ndimage.label(joined, structure=np.ones((3, 3)))
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        h, w = y1 - y0, x1 - x0
        if h < 14 or w < 8:          # text, sparks
            continue
        if h > 110 or w > 150:       # portraits, banners, huge effects
            continue
        sub = fg[y0:y1, x0:x1] & (lab[y0:y1, x0:x1] == i)
        cols = {tuple(c) for c in a[y0:y1, x0:x1, :3][sub]}
        if len(cols) < 6:            # captions and credits are 1-3 colours
            continue
        boxes.append(dict(x=int(x0), y=int(y0), w=int(w), h=int(h), px=int(sub.sum()), id=i))
    # rows: boxes whose vertical centres lie within the same band
    boxes.sort(key=lambda b: (b['y'] + b['h'] / 2, b['x']))
    rows, cur = [], []
    for b in boxes:
        c = b['y'] + b['h'] / 2
        if cur and abs(c - np.mean([q['y'] + q['h'] / 2 for q in cur])) > 18:
            rows.append(sorted(cur, key=lambda q: q['x'])); cur = []
        cur.append(b)
    if cur:
        rows.append(sorted(cur, key=lambda q: q['x']))
    return im, a, bg, lab, rows


def main():
    src, out = sys.argv[1], sys.argv[2]
    im, a, bg, lab, rows = frames(src)
    json.dump(dict(bg=list(map(int, bg)), rows=[[{k: v for k, v in b.items()} for b in r] for r in rows]),
              open(out + '.json', 'w'))
    # contact sheet: one line per row, frames at x2 with labels
    S = 2
    lines = []
    for ri, r in enumerate(rows):
        cells = []
        for ci, b in enumerate(r):
            crop = im.crop((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
            m = (lab[b['y']:b['y'] + b['h'], b['x']:b['x'] + b['w']] == b['id'])
            ca = np.array(crop); ca[..., 3] = np.where(m & np.any(ca[..., :3] != bg, -1), 255, 0)
            crop = Image.fromarray(ca).resize((b['w'] * S, b['h'] * S), Image.NEAREST)
            cell = Image.new('RGBA', (crop.width + 6, crop.height + 14), (60, 60, 70, 255))
            cell.alpha_composite(crop, (3, 12))
            ImageDraw.Draw(cell).text((2, 0), f'{ri}.{ci}', fill=(255, 255, 0, 255))
            cells.append(cell)
        H = max(c.height for c in cells)
        W = sum(c.width for c in cells)
        line = Image.new('RGBA', (W, H), (40, 40, 48, 255)); x = 0
        for c in cells:
            line.alpha_composite(c, (x, 0)); x += c.width
        lines.append(line)
    W = min(1600, max(l.width for l in lines)); H = sum(l.height for l in lines)
    sheet = Image.new('RGBA', (W, H), (20, 20, 24, 255)); y = 0
    for l in lines:
        sheet.alpha_composite(l.crop((0, 0, min(l.width, W), l.height)), (0, y)); y += l.height
    sheet.convert('RGB').save(out + '.png')
    print(out, sum(len(r) for r in rows), 'frames in', len(rows), 'rows')


if __name__ == '__main__':
    main()
