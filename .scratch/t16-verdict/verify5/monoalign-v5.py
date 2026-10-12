#!/usr/bin/env python3
"""Monotone alignment diff (reviewer's instrument for the pixel gate).

Model: t16 is live with some content removed (the ledger's exempt changes only
remove/move content vertically), so there is a monotone shift path s(y) that is
non-increasing (rows can only be deleted from live, never inserted) and changes
by at most 1px per row. DP finds the path minimising the row distance; the
leftover is `|A[y] - B[y+s(y)]| > 0` counted at threshold 0, exactly the gate's
rule. The rows where s decreases (deletions) mark where content was removed —
they must fall inside the ledger's exempt spans.

    python3 monoalign-v5.py <pairs-dir> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

pairs = Path(sys.argv[1])
landmarks = json.load(open(sys.argv[2]))
# live-side dynamic spans (verified: two captures of the SAME side differ there)
DYNAMIC = {
    'pdp-en-1440': [(248, 294, 'live lazy thumbnail (dynamic, live side)')],
    'pdp-de-390': [(3545, 3622, 'live lazy thumbnail (dynamic, live side)')],
}
out_path = sys.argv[3]
out_dir = Path(out_path).parent / 'aligned'
out_dir.mkdir(parents=True, exist_ok=True)

# exempt spans in LIVE coordinates (from my own landmarks + the ledger's items)
EXEMPT_LIVE = {
    'shop-1440': [(250, 340, 'chips row'), (1840, 2065, 'rail-help card (B)')],
    'shop-390': [(280, 395, 'chips row')],
    'archive-1440': [(250, 340, 'chips row'), (1590, 2000, 'rail-help (B) + extra Usable-energy section')],
    'archive-390': [(280, 395, 'chips row')],
    'pdp-1440': [(1720, 2095, 'P1 stats'), (2455, 2705, 'P3 FAQ'), (2790, 3520, 'P2 pairings')],
    'pdp-390': [(485, 620, 'P4 spec strip')],
}
def spans_from_landmarks(base):
    kind, lang, width = base.split('-')[0], base.split('-')[1], base.split('-')[2]
    L = landmarks.get(f'{kind}-{lang}-{width}-live')
    if not L:
        return []
    sp = []
    def add(sel, name, pad=6, src=L):
        v = src.get(sel)
        if v:
            x, y, w_, h_ = v[0]
            sp.append((y - pad, y + h_ + pad, name))
    # the Genie dock (fixed bubble, ledger 'Genie 坞') renders at the first
    # viewport's bottom right in the t16 capture at 1440
    T = landmarks.get(f'{kind}-{lang}-{width}-t16')
    if T and '[class*="genie"]' in T and width == '1440':
        for rect in T['[class*="genie"]']:
            if rect[2] == 50 and rect[3] == 50:
                sp.append((rect[1] - 8, rect[1] + rect[3] + 8, 'Genie dock (ledger)'))
    if kind == 'pdp':
        add('.pdp-stats-layout', 'P1 stats (ledger)')
        add('.pdp-faqs', 'P3 FAQ (ledger)')
        add('.pdp-pairings', 'P2 pairings (ledger)')
        add('.pdp-spec-list', 'P4 390 spec strip (ledger)')
        if lang == 'de':
            add('.pdp-overview', 'DE intro rewrite (ledger)')
    else:
        add('.wb-acts' if width == '1440' else '.catalog-mobile-actions', 'chips row (ledger)')
        # the rail-help card: union of both sides' rects (the ruling copy makes
        # the t16 card taller), so the B exemption covers its whole footprint
        add('.rail-help', 'rail-help card (B, ledger)')
        if T and '.rail-help' in T:
            x, y, w_, h_ = T['.rail-help'][0]
            sp.append((y - 6, y + h_ + 6, 'rail-help card t16 rect (B, ledger)'))
    return sp
EXEMPT_LIVE = {}

# per-family shift window (live row y maps to t16 row y+s), loose but bounded
WINDOW = {
    'shop-1440': (-60, 20), 'shop-390': (-120, 20),
    'archive-1440': (-260, 20), 'archive-390': (-120, 20),
    'pdp-1440': (-260, 40), 'pdp-390': (-60, 60),
}
XSTEP = 4

report = {}
for live_p in sorted(pairs.glob('*-live.png')):
    base = live_p.name[:-len('-live.png')]
    fam = f"{base.split('-')[0]}-{base.split('-')[2]}"
    t16_p = pairs / f'{base}-t16.png'
    if not t16_p.exists():
        continue
    im_live = Image.open(live_p).convert('RGB')
    im_t16 = Image.open(t16_p).convert('RGB')
    w = min(im_live.width, im_t16.width)
    h = min(im_live.height, im_t16.height)
    A = np.asarray(im_live.crop((0, 0, w, h)), dtype=np.int16)
    B = np.asarray(im_t16.crop((0, 0, w, h)), dtype=np.int16)
    As = A[:, ::XSTEP].max(axis=2).astype(np.int32)
    Bs = B[:, ::XSTEP].max(axis=2).astype(np.int32)
    smin, smax = WINDOW[fam]
    shifts = list(range(smin, smax + 1))   # ascending; index k = smin + k
    nS = len(shifts)
    # row cost: mean abs diff of live row y against t16 row y+s
    rows = h
    cost = np.full((rows, nS), 1e9, dtype=np.float32)
    for k, s in enumerate(shifts):
        if s >= 0:
            y0, y1 = 0, rows - s
            cost[y0:y1, k] = np.abs(As[y0:y1] - Bs[y0 + s:y1 + s]).mean(axis=1)
        else:
            y0, y1 = -s, rows
            cost[y0:y1, k] = np.abs(As[y0:y1] - Bs[y0 + s:y1 + s]).mean(axis=1)
    # DP with non-increasing s (s(y) <= s(y-1), s(y) >= s(y-1)-1)
    INF = np.float32(1e12)
    dp = np.full((rows, nS), INF, dtype=np.float32)
    back = np.full((rows, nS), -1, dtype=np.int16)
    # start: any shift allowed
    dp[0] = cost[0]
    for y in range(1, rows):
        prev = dp[y - 1]
        same = prev
        dec = np.concatenate([prev[1:], np.array([INF], dtype=np.float32)])   # came from k+1 (s bigger)
        inc = np.concatenate([np.array([INF], dtype=np.float32), prev[:-1]])  # came from k-1 (s smaller)
        best = same
        backv = np.zeros(nS, dtype=np.int16)
        m = dec < best; best = np.where(m, dec, best); backv = np.where(m, 1, backv)
        m = inc < best; best = np.where(m, inc, best); backv = np.where(m, -1, backv)
        back[y] = backv
        dp[y] = best + cost[y]
    # backtrack from the end, choosing the best final shift
    k = int(np.argmin(dp[rows - 1]))
    path = np.empty(rows, dtype=np.int32)
    deletions = []
    insertions = []
    for y in range(rows - 1, -1, -1):
        path[y] = shifts[k]
        if y > 0 and back[y, k] == 1:
            deletions.append(y)  # live row y has no counterpart (t16 skipped it)
            k = k + 1
        elif y > 0 and back[y, k] == -1:
            insertions.append(y)  # t16 row inserted before live row y
            k = k - 1
    # residual at threshold 0 along the path
    resid = 0
    for y in range(rows):
        s = int(path[y])
        sy = y + s
        if 0 <= sy < h:
            d = np.abs(A[y] - B[sy]).max(axis=1)
            resid += int((d > 0).sum())
    total = rows * w
    # aligned diff visualization (red = differing along the alignment path)
    vis = np.full((rows, w, 3), 235, dtype=np.uint8)
    for y in range(rows):
        sy = y + int(path[y])
        if 0 <= sy < h:
            dd = np.abs(A[y] - B[sy]).max(axis=1) > 0
            vis[y][dd] = (255, 0, 0)
    Image.fromarray(vis).save(out_dir / f'{base}-aligned-diff.png')

    # residual along the path, per 100px live band, flagged by exempt spans
    ex = spans_from_landmarks(base) + DYNAMIC.get(base, [])
    bands = []
    out_resid = out_px = in_resid = 0
    out_gt10 = 0
    for y0 in range(0, rows, 50):
        y1 = min(y0 + 50, rows)
        c = 0; g10 = 0
        for y in range(y0, y1):
            s_ = int(path[y]); sy = y + s_
            if 0 <= sy < h:
                dd = np.abs(A[y] - B[sy]).max(axis=1)
                c += int((dd > 0).sum())
                g10 += int((dd > 10).sum())
        lab = None
        for ey0, ey1, name in ex:
            if y0 < ey1 and y1 > ey0:
                lab = name
                break
        bands.append({'y0': y0, 'resid': c, 'gt10': g10, 'exempt': lab})
        if lab is None:
            out_resid += c; out_px += (y1 - y0) * w; out_gt10 += g10
        else:
            in_resid += c
    # group deletions/insertions into runs
    runs = []
    for y in sorted(deletions) + sorted(insertions):
        if runs and y - runs[-1][1] <= 5:
            runs[-1][1] = y
        else:
            runs.append([y, y])
    report[base] = {
        'size': f'{w}x{h}', 'resid': resid, 'resid_pct': round(100.0 * resid / total, 3),
        'total': total,
        'shift_start': int(path[0]), 'shift_end': int(path[-1]),
        'n_deletions': len(deletions), 'n_insertions': len(insertions),
        'deletion_runs': [[a, b, b - a + 1] for a, b in runs],
        'outside_exempt_resid': out_resid,
        'outside_exempt_pct': round(100.0 * out_resid / max(1, out_px), 3),
        'outside_exempt_gt10': out_gt10,
        'outside_exempt_gt10_pct': round(100.0 * out_gt10 / max(1, out_px), 4),
        'inside_exempt_resid': in_resid,
        'top_outside_bands': sorted([b for b in bands if b['exempt'] is None], key=lambda b: -b['resid'])[:10],
        'top_outside_gt10_bands': sorted([b for b in bands if b['exempt'] is None], key=lambda b: -b['gt10'])[:10],
    }
    delr = ', '.join(f'{a}-{b}({n})' for a, b, n in report[base]['deletion_runs'][:12])
    print(f"{base}: resid {report[base]['resid_pct']}% | outside-exempt {report[base]['outside_exempt_pct']}% "
          f"({out_resid} px, of which >10: {out_gt10} = {report[base]['outside_exempt_gt10_pct']}%) | inside {in_resid} px | shift {path[0]} -> {path[-1]}")
    print('   top outside >10 bands:', [(b['y0'], b['gt10'], b['resid']) for b in report[base]['top_outside_gt10_bands'][:6]])
    print('   exempt spans:', [(int(a), int(b), n) for a, b, n in ex])

Path(out_path).write_text(json.dumps(report, indent=1))
