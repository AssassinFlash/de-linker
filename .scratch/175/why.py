#!/usr/bin/env python3
"""Why a before/after pair differs: the first differing pixels with their
colours, and how the differing rows/columns are distributed.

    uv run --with numpy --with pillow python .scratch/175/why.py <before.png> <after.png> [samples]
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

before = np.asarray(Image.open(Path(sys.argv[1])).convert("RGB"), dtype=np.int16)
after = np.asarray(Image.open(Path(sys.argv[2])).convert("RGB"), dtype=np.int16)
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 20

d = np.abs(before - after).max(axis=2)
ys, xs = np.nonzero(d > 0)
print(f"differing pixels: {len(ys)}")
step = max(1, len(ys) // samples)
for i in range(0, len(ys), step):
    y, x = int(ys[i]), int(xs[i])
    print(f"  y={y:5d} x={x:5d} before={tuple(int(v) for v in before[y, x])} after={tuple(int(v) for v in after[y, x])}")

delta = np.abs(before.astype(np.int32) - after.astype(np.int32))
print("max channel delta:", int(delta.max()), "mean over differing:", round(float(delta[d > 0].mean()), 2))
# Row runs: which rows differ and how strongly
rows = (d > 0).sum(axis=1)
rows_nz = np.nonzero(rows)[0]
if len(rows_nz):
    print(f"rows {rows_nz.min()}..{rows_nz.max()}, rows with diffs: {len(rows_nz)}")
    for y in rows_nz[:40]:
        print(f"   row {y}: {int(rows[y])} px")
