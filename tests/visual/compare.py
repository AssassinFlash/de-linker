"""Exact RGB comparator for pixel-parity.mjs; no tolerance, masks or cropping.

Can also re-read an existing capture: python3 tests/visual/compare.py <outdir>.
Requires Pillow, already used by the site's visual acceptance tools.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

root = Path(sys.argv[1])
manifest = json.loads((root / "capture.json").read_text())
results = []
failed = False
for case in manifest["cases"]:
    stem = f"{case['stem']}-{case['width']}"
    live = Image.open(root / f"{stem}-live.png").convert("RGB")
    local = Image.open(root / f"{stem}-local.png").convert("RGB")
    if live.size != local.size:
        print(f"{stem}: size mismatch {live.size} / {local.size}", file=sys.stderr)
        results.append({"case": stem, "dimension_match": False,
                        "live_size": live.size, "local_size": local.size,
                        "ruled_change": False})
        failed = True
        continue
    diff = ImageChops.difference(live, local)
    red, green, blue = diff.split()
    # Luminance can round a one-level channel difference to 0. The maximum
    # channel preserves even that single-pixel difference.
    mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    count = sum(mask.histogram()[1:])
    bounds = mask.getbbox()
    # Regions are explicit ruled changes, never dynamic masks. Keep the raw
    # difference above and count every pixel outside the declared rectangles.
    outside = mask.copy()
    regions = list(case.get("ruledRegions", []))
    regions.extend({"name": "declared header change", "bounds": [0, 0, live.width, rule["height"]]}
                   for rule in manifest["allowedHeaderChanges"]
                   if case["path"] == rule["path"] and case["width"] in rule["widths"])
    for region in regions:
        left, top, right, bottom = region["bounds"]
        if not (0 <= left < right <= live.width and 0 <= top < bottom <= live.height):
            raise SystemExit(f"{stem}: invalid ruled region {region}")
        outside.paste(0, (left, top, right, bottom))
    outside_count = sum(outside.histogram()[1:])
    ruled_change = count > 0 and outside_count == 0
    row = {
        "language": case["language"],
        "viewport_width": case["width"],
        "image_size": live.size,
        "unmasked_different_pixels": count,
        "difference_bounds": bounds,
        "masks": [],
        "ruled_change": ruled_change,
        "ruled_regions": regions,
        "outside_ruled_different_pixels": 0 if ruled_change else outside_count,
    }
    results.append(row)
    print(json.dumps(row))
    failed |= count > 0 and not ruled_change
    if count:
        Image.composite(
            Image.new("RGB", live.size, "red"),
            local.point(lambda channel: channel // 3),
            mask.point(lambda channel: 255 if channel else 0),
        ).save(root / f"{stem}-diff.png")
    # Measured header crop is a companion, never the full-page proof.
    height = case["headerHeight"]
    if not height:
        continue
    pair = Image.new("RGB", (live.width, height * 2))
    pair.paste(live.crop((0, 0, live.width, height)), (0, 0))
    pair.paste(local.crop((0, 0, local.width, height)), (0, height))
    pair.save(root / f"{stem}-headers.png")
(root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
raise SystemExit(1 if failed else 0)
