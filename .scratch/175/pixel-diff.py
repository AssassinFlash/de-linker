#!/usr/bin/env python3
"""Pixel diff of the before/after shot pairs (#175 self-check).

    uv run --with numpy --with pillow python .scratch/175/pixel-diff.py <before-dir> <after-dir> [out-dir]
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

before = Path(sys.argv[1])
after = Path(sys.argv[2])
out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
if out:
    out.mkdir(parents=True, exist_ok=True)

total = 0
for b in sorted(before.glob("*.png")):
    a = after / b.name
    if not a.exists():
        print(f"{b.name}: MISSING after shot")
        continue
    ia = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    ib = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
    h = min(ia.shape[0], ib.shape[0])
    w = min(ia.shape[1], ib.shape[1])
    d = np.abs(ia[:h, :w] - ib[:h, :w]).max(axis=2)
    mask = d > 0
    n = int(mask.sum())
    total += n
    line = f"{b.name}: before {ia.shape[1]}x{ia.shape[0]} after {ib.shape[1]}x{ib.shape[0]} diff={n}"
    if n:
        ys, xs = np.nonzero(mask)
        line += f" bbox y={ys.min()}..{ys.max()} x={xs.min()}..{xs.max()}"
    print(line)
    if out:
        vis = np.full((h, w, 3), 235, dtype=np.uint8)
        vis[mask] = (255, 0, 0)
        Image.fromarray(vis).save(out / f"{b.stem}-diff.png")
print(f"total differing pixels: {total}")
