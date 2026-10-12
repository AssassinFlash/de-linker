#!/usr/bin/env python3
"""Pixel diff for the fresh-diff debt audit (threshold 0, per the t16 method).

    python3 freshdiff.py <captures-dir> <out-dir>

Per pair: differing-pixel count, diff visualization (red = differing pixel,
grey = equal), and 200px-band attribution so differences can be located in
page regions. Also emits worst-band crops for quick eyeballing.
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
    t112 = pairs / f'{base}-t112.png'
    if not t112.exists():
        continue
    a = np.asarray(Image.open(live).convert('RGB'), dtype=np.int16)
    b = np.asarray(Image.open(t112).convert('RGB'), dtype=np.int16)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    d = np.abs(a[:h, :w] - b[:h, :w]).max(axis=2)
    mask = d > 0
    # Visualization: equal pixels light grey, differing red.
    vis = np.full((h, w, 3), 235, dtype=np.uint8)
    vis[mask] = (255, 0, 0)
    Image.fromarray(vis).save(out / f'{base}-diff.png')
    # Band attribution: 200px horizontal bands.
    bands = []
    band_h = 200
    for y0 in range(0, h, band_h):
        n = int(mask[y0:y0 + band_h].sum())
        if n > 0:
            bands.append({'y': y0, 'diff': n})
    rows.append({
        'pair': base,
        'live': f'{a.shape[1]}x{a.shape[0]}',
        't112': f'{b.shape[1]}x{b.shape[0]}',
        'overlap': f'{w}x{h}',
        'diff_pixels': int(mask.sum()),
        'diff_percent': round(100.0 * mask.sum() / (h * w), 2),
        'height_delta': int(b.shape[0] - a.shape[0]),
        'bands_with_diff': len(bands),
        'bands': bands[:60],
    })
(out / 'summary.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print(f"{r['pair']}: live {r['live']} t112 {r['t112']} | diff {r['diff_pixels']}/{r['diff_percent']}% "
          f"| height_delta {r['height_delta']} | bands {r['bands_with_diff']}")
