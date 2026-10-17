"""Exact RGB comparison; no tolerance or masks. Requires Pillow."""
import json
from pathlib import Path
from PIL import Image, ImageChops

root = Path(__file__).resolve().parent
rows = []
for language in ("en", "de"):
    for width in (1440, 390):
        live = Image.open(root / f"parity-live-{language}-{width}.png").convert("RGB")
        local = Image.open(root / f"parity-local-{language}-{width}.png").convert("RGB")
        same_size = live.size == local.size
        count = None
        if same_size:
            diff = ImageChops.difference(live, local)
            count = sum(pixel != (0, 0, 0) for pixel in diff.getdata())
        rows.append({"language": language, "width": width, "live_size": live.size, "local_size": local.size, "unmasked_different_pixels": count, "masks": [], "pass": same_size and count == 0})
report = {"surface": "existing account sign-in page", "method": "same Chromium process and viewport, full-page, fonts and rendered images loaded, animations disabled, exact RGB, no masks", "results": rows}
(root / "pixel-parity.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
