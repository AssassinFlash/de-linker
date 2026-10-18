"""Compare the same browser's loaded full-page EN captures without masks."""
import hashlib
import json
import pathlib
from PIL import Image, ImageChops

HERE = pathlib.Path(__file__).resolve().parent
rows = []
for before in sorted((HERE/'en-before').glob('*.png')):
    after = HERE/'en-final'/before.name
    raw_left, raw_right = Image.open(before), Image.open(after)
    assert raw_left.format == raw_right.format == 'PNG', 'Strict pixel evidence must use native lossless PNG'
    left, right = raw_left.convert('RGBA'), raw_right.convert('RGBA')
    approved_changes = {'inquiry':'inquiry design','product':'owner-approved product presentation','blog':'owner-referenced journal discovery','blog-category':'owner-referenced topic discovery','service':'owner-approved service introduction'}
    approved = approved_changes.get(before.stem.rsplit('-',1)[0])
    if left.size == right.size:
        # Count pixels with a difference in any RGBA channel, not file metadata.
        changed = sum(a != b for a, b in zip(left.getdata(), right.getdata()))
        box = ImageChops.difference(left.convert('RGB'), right.convert('RGB')).getbbox()
    else:
        changed, box = None, None
    rows.append({'file':before.name,'before_size':left.size,'after_size':right.size,'changed_pixels':changed,'bbox':box,'approved_change':approved,'pass':approved or (left.size == right.size and changed == 0),'before_sha256':hashlib.sha256(before.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(after.read_bytes()).hexdigest()})
assert sum(not r['approved_change'] for r in rows) == 18, 'Nine unaffected page types retain the strict pixel gate'
assert len(rows) == 28, 'Fourteen EN page types at two viewport sizes are required'
(HERE/'pixel-results.json').write_text(json.dumps({'masks':[], 'captures':rows, 'pass':all(r['pass'] for r in rows)},indent=2)+'\n')
for r in rows:
    print(r['file'],r['changed_pixels'],r['pass'])
raise SystemExit(not all(r['pass'] for r in rows))
