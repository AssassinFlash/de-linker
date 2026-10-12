#!/usr/bin/env python3
"""Reviewer's own pixel diff (threshold 0) + region analysis for the 12 pairs.

    python3 diff-v5.py <pairs-dir> <out-dir>

Threshold 0 = any RGB max-channel difference counts (the pixel gate's rule).
Emits summary.json with per-pair counts plus the worst 80x80 blocks and a
row-band histogram so each page's residual can be classified.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

pairs = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
rows = []
for live in sorted(pairs.glob('*-live.png')):
    base = live.name[:-len('-live.png')]
    t16 = pairs / f'{base}-t16.png'
    if not t16.exists():
        continue
    a = np.asarray(Image.open(live).convert('RGB'), dtype=np.int16)
    b = np.asarray(Image.open(t16).convert('RGB'), dtype=np.int16)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    d = np.abs(a[:h, :w] - b[:h, :w]).max(axis=2)
    mask = d > 0
    gt8 = int((d > 8).sum())
    # visualization
    vis = np.full((h, w, 3), 235, dtype=np.uint8)
    vis[mask] = (255, 0, 0)
    Image.fromarray(vis).save(out / f'{base}-diff.png')
    # worst 80x80 blocks
    blocks = []
    for y0 in range(0, h, 80):
        for x0 in range(0, w, 80):
            c = int(mask[y0:y0 + 80, x0:x0 + 80].sum())
            if c:
                blocks.append((c, x0, y0))
    blocks.sort(reverse=True)
    # row bands (100px) — where the diff lives vertically
    bands = []
    for y0 in range(0, h, 100):
        c = int(mask[y0:y0 + 100].sum())
        if c:
            bands.append((y0, c))
    rows.append({
        'pair': base,
        'live': f'{a.shape[1]}x{a.shape[0]}',
        't16': f'{b.shape[1]}x{b.shape[0]}',
        'overlap': f'{w}x{h}',
        'diff_pixels': int(mask.sum()),
        'diff_pixels_gt8': gt8,
        'diff_percent': round(100.0 * int(mask.sum()) / (h * w), 2),
        'worst_blocks': [{'c': c, 'x': x, 'y': y} for c, x, y in blocks[:8]],
        'row_bands_top': [{'y': y, 'c': c} for y, c in sorted(bands, key=lambda t: -t[1])[:6]],
    })
(out / 'summary.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print(f"{r['pair']}: live {r['live']} t16 {r['t16']} | diff {r['diff_pixels']} | {r['diff_percent']}% | gt8 {r['diff_pixels_gt8']}")
