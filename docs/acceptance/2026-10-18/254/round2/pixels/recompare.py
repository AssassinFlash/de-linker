"""Recount archived-approved/current native PNGs with the shared RGB comparator.

No capture, network, site writes, image editing, masks or tolerance. Temporary
copies only supply the shared comparator's established live/local filenames;
both inputs are local captures with their actual source pins in capture.json.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

folder = Path(__file__).resolve().parent
repo = folder.parents[5]
rows = json.loads((folder / 'readback.json').read_text())
assert len(rows) == 18
baseline = folder.parent.parent / 'en-final'
manifest = {
    'baseline_source': 'aa552bdf3ba4423ff34d032e116dadb1af8fd615',
    'current_source': 'bd862bdd5253ed246ab0fa5267f2b5defd6a8c4c',
    'capture_protocol': '../../capture-protocol.js (native CUA/CDP PNG, same tab, original exact viewports, fonts/images decoded, videos paused at loaded first frame)',
    'baseline_directory': '../../en-final',
    'current_directory': '.',
    'note': 'Immutable accepted prior frames compared with fresh current frames. Comparator live/local names are slots, not a claim of production capture. No shared source or database switching.',
    'allowedHeaderChanges': [],
    'cases': [],
}
with tempfile.TemporaryDirectory(prefix='linker-254-pixel-') as work:
    temporary = Path(work)
    for row in rows:
        assert row['baselineSource'] == manifest['baseline_source']
        assert row['currentSource'] == manifest['current_source']
        assert row['y'] == 0 and row['lang'].startswith('en')
        assert all(image['complete'] and image['loaded'] for image in row['images'])
        assert all(video['ready'] >= 2 and video['paused'] and video['time'] <= 0.01 for video in row['videos'])
        stem = row['file'].removesuffix('.png')
        name = stem.rsplit('-', 1)[0]
        shutil.copyfile(baseline / row['file'], temporary / f'{stem}-live.png')
        shutil.copyfile(folder / row['file'], temporary / f'{stem}-local.png')
        manifest['cases'].append({'path': row['path'], 'stem': name, 'width': row['w'], 'language': 'en', 'headerHeight': 0, 'ruledRegions': []})
    (temporary / 'capture.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (folder / 'capture.json').write_text(json.dumps(manifest, indent=2) + '\n')
    result = subprocess.run([sys.executable, str(repo / 'tests/visual/compare.py'), str(temporary)], check=False)
    shutil.copyfile(temporary / 'results.json', folder / 'results.json')
    # Keep any failing raw difference image for diagnosis, never suppress it.
    for difference in temporary.glob('*-diff.png'):
        shutil.copyfile(difference, folder / difference.name)
raise SystemExit(result.returncode)
