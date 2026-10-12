#!/usr/bin/env python3
"""Full-page pixel diff for the DE parity run. Threshold 0, no mask, no shift.

A pair whose heights differ is compared on the overlapping rectangle AND the
pixels that exist on only one side are counted as different. The overlap-only
number is reported beside it, so a short page cannot look cleaner than it is.
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
for live in sorted(pairs.glob("*-live.png")):
    base = live.name[: -len("-live.png")]
    local = pairs / f"{base}-t110.png"
    if not local.exists():
        continue
    a = np.asarray(Image.open(live).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(local).convert("RGB"), dtype=np.int16)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    overlap = np.abs(a[:h, :w] - b[:h, :w]).max(axis=2) > 0
    only = abs(a.shape[0] - b.shape[0]) * w + abs(a.shape[1] - b.shape[1]) * max(a.shape[0], b.shape[0])
    # The corner term above double-counts a width-and-height difference; these
    # captures are the same viewport width, so the width term is zero.
    full = int(overlap.sum()) + int(only)
    total = max(a.shape[0], b.shape[0]) * max(a.shape[1], b.shape[1])
    mag = np.abs(a[:h, :w] - b[:h, :w]).max(axis=2)
    rows.append({
        "pair": base,
        "live": f"{a.shape[1]}x{a.shape[0]}",
        "t110": f"{b.shape[1]}x{b.shape[0]}",
        "diff_pixels_full": full,
        "diff_pixels_overlap": int(overlap.sum()),
        "height_only_pixels": int(only),
        "diff_percent_full": round(100.0 * full / total, 4),
        "height_delta": int(b.shape[0] - a.shape[0]),
        "mag1_share_of_overlap": round(100.0 * int((mag == 1).sum()) / max(int(overlap.sum()), 1), 2),
        "mag_ge_10": int((mag >= 10).sum()),
    })
(out / "summary.json").write_text(json.dumps(rows, indent=1))
for r in rows:
    print(f"{r['pair']}: live {r['live']} t110 {r['t110']} | full {r['diff_pixels_full']} ({r['diff_percent_full']}%) "
          f"| overlap {r['diff_pixels_overlap']} | dh {r['height_delta']} | mag1 {r['mag1_share_of_overlap']}% | mag>=10 {r['mag_ge_10']}")
