#!/usr/bin/env python3
"""Cluster the differing pixels of a before/after pair into boxes.

    uv run --with numpy --with pillow python .scratch/175/diff-regions.py <before.png> <after.png> [min-pixels] [cell]

A coarse grid of `cell` pixels is marked where any pixel differs, the marked
cells are clustered, and each cluster prints its box, its size and a sample of
the colours on both sides — enough to name the element the box is.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

before = np.asarray(Image.open(Path(sys.argv[1])).convert("RGB"), dtype=np.int16)
after = np.asarray(Image.open(Path(sys.argv[2])).convert("RGB"), dtype=np.int16)
min_pixels = int(sys.argv[3]) if len(sys.argv) > 3 else 400
cell = int(sys.argv[4]) if len(sys.argv) > 4 else 16

h = min(before.shape[0], after.shape[0])
w = min(before.shape[1], after.shape[1])
d = np.abs(before[:h, :w] - after[:h, :w]).max(axis=2)
mask = d > 0

rows = h // cell
cols = w // cell
grid = np.zeros((rows, cols), dtype=bool)
counts = np.zeros((rows, cols), dtype=np.int64)
for r in range(rows):
    for c in range(cols):
        block = mask[r * cell : (r + 1) * cell, c * cell : (c + 1) * cell]
        counts[r, c] = block.sum()
        grid[r, c] = block.any()

seen = np.zeros_like(grid)
clusters = []
for r in range(rows):
    for c in range(cols):
        if not grid[r, c] or seen[r, c]:
            continue
        stack = [(r, c)]
        seen[r, c] = True
        cells = []
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < rows and 0 <= nx < cols and grid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        total = int(sum(counts[y, x] for y, x in cells))
        ys = [y for y, _ in cells]
        xs = [x for _, x in cells]
        clusters.append(
            {
                "total": total,
                "y0": min(ys) * cell,
                "y1": (max(ys) + 1) * cell,
                "x0": min(xs) * cell,
                "x1": (max(xs) + 1) * cell,
            }
        )

clusters.sort(key=lambda box: -box["total"])
print(f"{len(clusters)} clusters (min {min_pixels} pixels)")
for box in clusters:
    if box["total"] < min_pixels:
        continue
    y = (box["y0"] + box["y1"]) // 2
    samples = []
    for x in range(box["x0"] + 4, box["x1"], max(8, (box["x1"] - box["x0"]) // 6)):
        samples.append((x, tuple(before[y, x]), tuple(after[y, x])))
    print(
        f"  {box['total']:8d} px  y {box['y0']}-{box['y1']}  x {box['x0']}-{box['x1']}"
    )
    for x, b, a in samples[:4]:
        print(f"        x={x}: before {b} after {a}")
