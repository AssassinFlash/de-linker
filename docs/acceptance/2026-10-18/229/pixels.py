"""Count every unequal RGB pixel, without tolerance or masks; fail EN drift.

Usage: python3 docs/acceptance/2026-10-18/229/pixels.py <capture-directory>
Requires Pillow (already used by the repository's visual acceptance tools).
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

root = Path(sys.argv[1])
results = []
failed = False
for width in (1280, 1440, 1920, 390):  # #229 acceptance viewports.
    for language, stem in (("en", "home"), ("de", "de")):
        live = Image.open(root / f"{stem}-{width}-live.png").convert("RGB")
        local = Image.open(root / f"{stem}-{width}-local.png").convert("RGB")
        same_size = live.size == local.size
        if not same_size:
            raise SystemExit(f"{language} {width}: size mismatch {live.size} / {local.size}")
        diff = ImageChops.difference(live, local)
        red, green, blue = diff.split()
        # Luminance conversion can round a one-level channel difference to 0.
        # The maximum channel preserves even that single-pixel difference.
        mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        count = sum(mask.histogram()[1:])
        bounds = mask.getbbox()
        # #229 only rules a desktop header change (measured height 89px).
        ruled_change = (
            language == "de"
            and width in (1440, 1920)
            and bounds is not None
            and bounds[3] <= 89
        )
        row = {
            "language": language,
            "viewport_width": width,
            "image_size": live.size,
            "unmasked_different_pixels": count,
            "difference_bounds": bounds,
            "masks": [],
            "ruled_change": ruled_change,
        }
        results.append(row)
        print(json.dumps(row))
        failed |= count > 0 and not row["ruled_change"]
        if count:
            Image.composite(
                Image.new("RGB", live.size, "red"),
                local.point(lambda channel: channel // 3),
                mask.point(lambda channel: 255 if channel else 0),
            ).save(root / f"{stem}-{width}-diff.png")
        # A compact, readable header comparison accompanies full-page proof.
        # The measured anonymous desktop header is 89px; mobile is 81px.
        height = 89 if width >= 1280 else 81
        pair = Image.new("RGB", (live.width, height * 2))
        pair.paste(live.crop((0, 0, live.width, height)), (0, 0))
        pair.paste(local.crop((0, 0, local.width, height)), (0, height))
        pair.save(root / f"{stem}-{width}-headers.png")
(root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
raise SystemExit(1 if failed else 0)
