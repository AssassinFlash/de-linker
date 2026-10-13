"""Build same-viewport evidence. No pixel similarity claim: skin and data differ."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
HERE = Path(__file__).resolve().parent
FONT = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
PORTAL = Image.open(HERE / 'ref-mobile-portal.png').convert('RGB')
# Coordinates selected by inspecting the owner's 736x1104 design sheet.
# Crop the designed screen only (no phone bezel). Scale it to the supplied
# reference viewport; the sheet is a raster, not DOM-derived CSS measurements.
CROPS = {
    'overview': (578, 82, 707, 368),
    'inquiries': (596, 733, 723, 982),
    'inquiry-detail': (303, 420, 430, 690),
    'documents': (303, 420, 430, 690),
    'saved-solutions': (155, 733, 282, 982),
    'company': (19, 420, 144, 690),
    'account-details': (19, 420, 144, 690),
}
DESKTOP = {
    'overview': 'ref-crm-index-1440.png',
    'inquiries': 'ref-inquiries-1440.png',
    'inquiry-detail': 'ref-inquiry-detail-1440.png',
    'documents': 'ref-documents-1440.png',
    'saved-solutions': 'ref-posts-1440.png',
    'company': 'ref-account-profile-1440.png',
    'account-details': 'ref-account-profile-1440.png',
}
def composite(left, right, target, caption):
    canvas = Image.new('RGB', (left.width + right.width, 36 + max(left.height, right.height)), 'white')
    canvas.paste(left, (0, 36)); canvas.paste(right, (left.width, 36))
    draw = ImageDraw.Draw(canvas)
    if left.width < 600:
        draw.text((12, 8), 'REF | owner portal crop', fill='black', font=FONT)
        draw.text((left.width + 12, 8), 'T110 | 390 x 844', fill='black', font=FONT)
    else:
        draw.text((12, 8), 'REFERENCE | ' + caption, fill='black', font=FONT)
        draw.text((left.width + 12, 8), 'T110 | token skin / real account data', fill='black', font=FONT)
    canvas.save(HERE / target)
for name, box in CROPS.items():
    ref = PORTAL.crop(box).resize((390, 844), Image.Resampling.LANCZOS)
    ref.save(HERE / f'ref-portal-{name}-390.png')
    for locale in ['', 'de-']:
        ours = Image.open(HERE / f'ours-{locale}{name}-390.png').convert('RGB')
        composite(ref, ours, f'compare-{locale}{name}-390.png', 'owner-provided mobile portal (raster crop)')
for name, reference in DESKTOP.items():
    left = Image.open(HERE / reference).convert('RGB')
    right = Image.open(HERE / f'ours-{name}-1440.png').convert('RGB')
    assert left.size == right.size == (1440, 900)
    composite(left, right, f'compare-{name}-1440.png', 'Preline Pro 1440 x 900')
# Detail region comparisons, same scale, from the final viewport captures.
for label, source, ours, a, b in [
    ('tiles', 'ref-crm-index-1440.png', 'ours-overview-1440.png', (72,231,1368,377), (300,331,1420,477)),
    ('table', 'ref-inquiries-1440.png', 'ours-inquiries-1440.png', (72,186,1368,346), (300,230,1420,430)),
]:
    left = Image.open(HERE/source).crop(a).convert('RGB')
    right = Image.open(HERE/ours).crop(b).convert('RGB')
    composite(left, right, f'compare-region-{label}-1440.png', 'native-pixel region; no rescaling')
print('Built 7 desktop, 14 mobile and 2 native-scale regional comparisons')
