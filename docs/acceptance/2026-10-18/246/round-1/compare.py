"""Exact RGB comparisons. Run with Python, Pillow and NumPy; no tolerance/masks."""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image

ROOT = Path(__file__).parent
GEOMETRY = {row['label']: row for row in json.loads((ROOT / 'capture-geometry.json').read_text())}


def compare(left, right, language, width):
    a = np.asarray(Image.open(ROOT / left).convert('RGB'), dtype=np.int16)
    b = np.asarray(Image.open(ROOT / right).convert('RGB'), dtype=np.int16)
    if a.shape != b.shape:
        raise ValueError(f'{left} and {right}: different dimensions')
    delta = np.max(np.abs(a - b), axis=2)
    record = GEOMETRY[f'feature-contact-{language}-{width}']
    rect = record['form']
    box = [math.ceil(rect['left']), math.ceil(rect['top']), math.floor(rect['right']), math.floor(rect['bottom'])]
    form = delta[box[1]:box[3], box[0]:box[2]]
    # Report the authenticated WP operator UI explicitly; it is not customer content.
    toolbar = 32 if width == 1440 else 46
    bands = []
    for photo in record['images']:
        r = photo['rect']
        x1, y1 = max(0, math.ceil(r['left'])), max(0, math.ceil(r['top']))
        x2, y2 = min(width, math.floor(r['right'])), min(len(delta), math.floor(r['bottom']))
        area = delta[y1:y2, x1:x2]
        bands.append({'asset': photo['src'].split('/')[-1], 'box': [x1,y1,x2,y2],
                      'different_pixels': int(np.count_nonzero(area)),
                      'max_channel_delta': int(area.max()) if area.size else 0})
    return {'left': left, 'right': right, 'language': language, 'width': width,
            'size': [a.shape[1], a.shape[0]], 'raw_different_pixels': int(np.count_nonzero(delta)),
            'operator_toolbar_different_pixels': int(np.count_nonzero(delta[:toolbar])),
            'customer_page_different_pixels': int(np.count_nonzero(delta[toolbar:])),
            'contact_form_different_pixels': int(np.count_nonzero(form)), 'form_box': box,
            'max_customer_channel_delta': int(delta[toolbar:].max()), 'photos': bands, 'masks': []}


matrix = []
for language in ('en', 'de'):
    for width in (1440, 390):
        for phase in ('main', 'feature'):
            row = compare(f'semantic-live-{phase}-{language}-{width}.png', f'semantic-{phase}-{language}-{width}.png', language, width)
            row['phase'] = phase
            matrix.append(row)
repeat = [compare(f'semantic-live-main-{lang}-{width}.png', f'semantic-live-feature-{lang}-{width}.png', lang, width)
          for lang in ('en', 'de') for width in (1440, 390)]
review_en = compare('diagnostic-live-second-en-1440.png', 'diagnostic-feature-second-en-1440.png', 'en', 1440)
settle = [compare(f'diagnostic-{phase}-first-en-1440.png', f'diagnostic-{phase}-second-en-1440.png', 'en', 1440)
          for phase in ('live','feature')]
result = {'matrix': matrix, 'live_repeat_control': repeat, 'final_review_en_1440': review_en, 'immediate_repeat_control': settle}
(ROOT / 'pixel-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
for row in matrix:
    print(row['phase'], row['language'], row['width'], 'page', row['customer_page_different_pixels'], 'form', row['contact_form_different_pixels'])
print('Final review EN1440: page', review_en['customer_page_different_pixels'], 'form', review_en['contact_form_different_pixels'])
