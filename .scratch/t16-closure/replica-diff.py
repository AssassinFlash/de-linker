#!/usr/bin/env python3
"""Pixel diff for the paired captures: per-pair differing-pixel counts, a diff
visualization (red = differing pixel, grey = equal) and a JSON summary.

    python3 .scratch/t16-closure/replica-diff.py <pairs-dir> <out-dir>
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
    # visualization: equal pixels in light grey, differing in red
    vis = np.full((h, w, 3), 235, dtype=np.uint8)
    vis[mask] = (255, 0, 0)
    Image.fromarray(vis).save(out / f'{base}-diff.png')
    rows.append({
        'pair': base,
        'live': f'{a.shape[1]}x{a.shape[0]}',
        't16': f'{b.shape[1]}x{b.shape[0]}',
        'overlap': f'{w}x{h}',
        'diff_pixels': int(mask.sum()),
        'diff_percent': round(100.0 * mask.sum() / (h * w), 2),
    })
(out / 'summary.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print(f"{r['pair']}: live {r['live']} t16 {r['t16']} | diff {r['diff_pixels']}/{r['diff_percent']}%")
