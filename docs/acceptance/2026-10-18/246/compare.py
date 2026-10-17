"""Recompute exact pixel evidence from the paired Chrome PNG captures (Pillow)."""
from pathlib import Path
import json
import math
from PIL import Image, ImageChops

root = Path(__file__).parent
rects = json.loads((root / 'contact-form-geometry.json').read_text())
results = []
for geometry in rects:
    language, width = geometry['language'], geometry['viewport']
    live = Image.open(root / f'live-contact-{language}-{width}.png').convert('RGB')
    local = Image.open(root / f'local-contact-{language}-{width}.png').convert('RGB')
    if live.size != local.size:
        raise ValueError(f'capture size mismatch: {language} {width}')
    diff = ImageChops.difference(live, local)
    body = diff.crop((0, 46 if width == 390 else 32, live.width, live.height))
    rect = geometry['live']
    box = (math.ceil(rect['x']), math.ceil(rect['y']),
           min(live.width, math.floor(rect['x'] + rect['width'])),
           math.floor(rect['y'] + rect['height']))
    form = ImageChops.difference(live.crop(box), local.crop(box))
    results.append(dict(language=language, viewport=width, size=live.size,
                        raw_different_pixels=sum(any(pixel) for pixel in diff.getdata()),
                        below_toolbar_different_pixels=sum(any(pixel) for pixel in body.getdata()),
                        body_bbox=body.getbbox(),
                        contact_form_different_pixels=sum(any(pixel) for pixel in form.getdata()),
                        contact_form_comparison_box=box))
    diff.point(lambda value: 255 if value else 0).save(root / f'contact-diff-{language}-{width}.png')
(root / 'pixel-comparison.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
