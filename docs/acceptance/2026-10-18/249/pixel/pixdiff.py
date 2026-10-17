"""python3 pixdiff.py <dir> : pairs *-live.png with *-local.png; prints differing pixels and writes *-diff.png."""
import sys
from pathlib import Path

from PIL import Image, ImageChops

d = Path(sys.argv[1])
for live in sorted(d.glob("*-live.png")):
    local = live.with_name(live.name.replace("-live.png", "-local.png"))
    if not local.exists():
        continue
    a, b = Image.open(live).convert("RGB"), Image.open(local).convert("RGB")
    if a.size != b.size:
        print(f"{live.name[:-9]}: SIZE live {a.size} local {b.size}")
        h = min(a.height, b.height)
        a, b = a.crop((0, 0, a.width, h)), b.crop((0, 0, b.width, h))
    diff = ImageChops.difference(a, b)
    mask = diff.convert("L").point(lambda v: 255 if v else 0)
    n = sum(1 for v in mask.getdata() if v)
    box = mask.getbbox()
    print(f"{live.name[:-9]}: {n} differing pixels, bbox {box}")
    if n:
        red = Image.new("RGB", a.size, (255, 0, 0))
        Image.composite(red, a.point(lambda v: v // 3), mask).save(d / live.name.replace("-live.png", "-diff.png"))
