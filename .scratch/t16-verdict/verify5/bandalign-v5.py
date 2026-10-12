#!/usr/bin/env python3
"""Reviewer's own band-alignment analysis.

For each pair: cut the live page into 200px bands, search the best integer dy
(over the whole vertical range) that minimises the mean |grey diff| against the
t16 page at that offset, then report the residual differing-pixel count at that
offset — i.e. "which live band corresponds to which t16 band, and what is left
over after alignment". Threshold for the residual count is 0 (any channel
difference counts), same as the pixel gate.

    python3 bandalign-v5.py <pairs-dir> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

pairs = Path(sys.argv[1])
out_path = sys.argv[2]

BAND = 200
XSTEP = 8  # search on every 8th column for speed; residual always measured at full width

report = {}
for live_p in sorted(pairs.glob('*-live.png')):
    base = live_p.name[:-len('-live.png')]
    t16_p = pairs / f'{base}-t16.png'
    if not t16_p.exists():
        continue
    im_live = Image.open(live_p).convert('RGB')
    im_t16 = Image.open(t16_p).convert('RGB')
    w = min(im_live.width, im_t16.width)
    h = min(im_live.height, im_t16.height)
    A = np.asarray(im_live.crop((0, 0, w, h)), dtype=np.int16)
    B = np.asarray(im_t16.crop((0, 0, w, h)), dtype=np.int16)
    Ad = A[:, ::XSTEP].max(axis=2)   # grey proxy: max channel
    Bd = B[:, ::XSTEP].max(axis=2)
    bands = []
    for y0 in range(0, h - 40, BAND):
        y1 = min(y0 + BAND, h)
        band = Ad[y0:y1]
        best = None
        lo = -900
        hi = 900
        for dy in range(lo, hi + 1):
            by0 = y0 + dy
            by1 = y1 + dy
            if by0 < 0 or by1 > h:
                continue
            sub = Bd[by0:by1]
            score = np.abs(band - sub).mean()
            if best is None or score < best[0]:
                best = (score, dy)
        if best is None:
            continue
        _, dy = best
        # residual at full resolution at that offset
        a = A[y0:y1]
        b = B[y0 + dy:y1 + dy]
        d = np.abs(a - b).max(axis=2)
        resid = int((d > 0).sum())
        total = int(d.size)
        # also residual at dy=0 for reference
        d0 = np.abs(A[y0:y1] - B[y0:y1]).max(axis=2)
        resid0 = int((d0 > 0).sum())
        bands.append({
            'y0': y0, 'y1': y1, 'best_dy': int(dy),
            'resid_at_best': resid, 'resid_at_best_pct': round(100.0 * resid / total, 2),
            'resid_at_0': resid0, 'resid_at_0_pct': round(100.0 * resid0 / total, 2),
        })
    # global residual under a piecewise shift model: for each band use its own best dy
    tot_resid = sum(bd['resid_at_best'] for bd in bands)
    tot_px = sum((bd['y1'] - bd['y0']) * w for bd in bands)
    report[base] = {
        'size': f'{w}x{h}',
        'bands': bands,
        'shift_model_resid': tot_resid,
        'shift_model_resid_pct': round(100.0 * tot_resid / tot_px, 3),
    }
    print(f"{base}: bands={len(bands)} shift-model resid {report[base]['shift_model_resid_pct']}% "
          f"| d0 resids: " + ','.join(str(bd['resid_at_0_pct']) for bd in bands[:8]) + ' ...')

Path(out_path).write_text(json.dumps(report, indent=1))
