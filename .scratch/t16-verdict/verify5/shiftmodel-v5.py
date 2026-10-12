#!/usr/bin/env python3
"""Reviewer's landmark shift-model diff.

The exempt changes (P1 #stats, P2 pairings, P3 FAQ, P4 390 spec strip, chips
rows, the rail-help card, the DE intro) move content vertically. This script
builds the vertical shift function from MY OWN DOM landmarks (landmarks-v5.json,
measured live and t16 in the same session) and then measures the threshold-0
residual of each pair at that shift — so what is left is either the exempt
change itself (flagged) or a genuine difference.

    python3 shiftmodel-v5.py <pairs-dir> <landmarks.json> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

pairs = Path(sys.argv[1])
landmarks = json.load(open(sys.argv[2]))
out_path = sys.argv[3]

# selectors used as anchors, in page order; only those present on both sides count
ANCHORS = [
    '.pdp-gallery-main-wrap', '.pdp-project-check', '.pdp-overview', '.pdp-stats-layout',
    '.pdp-info-tabs', '.pdp-faqs', '.pdp-pairings', '.pdp-docs', 'footer',
    '.catalog-mobile-actions', '.wb-acts', '.rail-help', '.linker-contact-invitation',
]
# exempt vertical spans (live y0..y1, label) per page family — the ledger's items
EXEMPT = {
    'shop': [(250, 350, 'chips row (.wb-acts)'), (1840, 2060, 'rail-help card (B)')],
    'archive': [(250, 350, 'chips row (.wb-acts)'), (1590, 2000, 'rail-help card + extra Usable energy section')],
    'pdp': [(1720, 2100, 'P1 #stats single column (ledger)'), (2450, 2820, 'P3 FAQ two columns (ledger)'),
            (2790, 3350, 'P2 pairings auto-fill (ledger)')],
}
EXEMPT_390 = {
    'shop': [(280, 340, 'chips row (.catalog-mobile-actions)')],
    'archive': [(280, 340, 'chips row (.catalog-mobile-actions)')],
    'pdp': [(485, 630, 'P4 390 spec strip two columns (ledger)')],
}

report = {}
for live_p in sorted(pairs.glob('*-live.png')):
    base = live_p.name[:-len('-live.png')]
    key = base.split('-')[0]            # shop | archive | pdp
    width = base.split('-')[2]          # 1440 | 390
    t16_p = pairs / f'{base}-t16.png'
    L = landmarks.get(f'{key}-{base.split("-")[1]}-{width}-live')
    T = landmarks.get(f'{key}-{base.split("-")[1]}-{width}-t16')
    if not t16_p.exists() or not L or not T:
        print(f'{base}: missing pair or landmarks')
        continue
    anchors = []
    for sel in ANCHORS:
        if sel in L and sel in T:
            anchors.append((L[sel][0][1], T[sel][0][1]))
    anchors.sort()
    im_live = Image.open(live_p).convert('RGB')
    im_t16 = Image.open(t16_p).convert('RGB')
    w = min(im_live.width, im_t16.width)
    h = min(im_live.height, im_t16.height)
    A = np.asarray(im_live.crop((0, 0, w, h)), dtype=np.int16)
    B = np.asarray(im_t16.crop((0, 0, w, h)), dtype=np.int16)

    def shift_at(y):
        s = 0
        for ay_live, ay_t16 in anchors:
            if ay_live <= y:
                s = ay_t16 - ay_live
            else:
                break
        return s

    # landmark-shifted copy of B sampled at each live row
    Bs = np.empty_like(B)
    for y in range(h):
        sy = y + shift_at(y)
        if 0 <= sy < h:
            Bs[y] = B[sy]
        else:
            Bs[y] = B[h - 1]
    d = np.abs(A - Bs).max(axis=2)
    mask = d > 0
    ex = EXEMPT_390 if width == '390' else EXEMPT
    spans = ex[key]
    bands = []
    for y0 in range(0, h, 100):
        y1 = min(y0 + 100, h)
        c = int(mask[y0:y1].sum())
        lab = None
        for ey0, ey1, name in spans:
            if y0 < ey1 and y1 > ey0:
                lab = name
                break
        bands.append({'y0': y0, 'resid': c, 'exempt': lab})
    # residual outside exempt spans
    outside = 0
    outside_px = 0
    for bd in bands:
        if bd['exempt'] is None:
            outside += bd['resid']
            outside_px += 100 * w
    inside = sum(bd['resid'] for bd in bands if bd['exempt'])
    report[base] = {
        'size': f'{w}x{h}', 'anchors': anchors,
        'shift_model_resid': int(mask.sum()), 'shift_model_resid_pct': round(100.0 * int(mask.sum()) / (h * w), 2),
        'outside_exempt_resid': outside, 'outside_exempt_pct': round(100.0 * outside / outside_px, 3),
        'inside_exempt_resid': inside,
        'top_outside_bands': sorted([bd for bd in bands if bd['exempt'] is None], key=lambda b: -b['resid'])[:8],
    }
    print(f"{base}: shift-model {report[base]['shift_model_resid_pct']}% | outside-exempt "
          f"{report[base]['outside_exempt_pct']}% ({outside} px) | inside-exempt {inside} px")

Path(out_path).write_text(json.dumps(report, indent=1))
