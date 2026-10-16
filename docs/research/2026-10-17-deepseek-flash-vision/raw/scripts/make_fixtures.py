"""Make the probe fixtures: a synthetic nameplate PNG and a one-page text PDF.

Usage: python3 -I make_fixtures.py <outdir>
Everything printed on the label is a test string, not a product fact.
"""

import json
import pathlib
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

FONT_DIR = "/System/Library/Fonts/Supplemental/"
bold = lambda size: ImageFont.truetype(FONT_DIR + "Arial Bold.ttf", size)  # noqa: E731
regular = lambda size: ImageFont.truetype(FONT_DIR + "Arial.ttf", size)  # noqa: E731

# Ground truth: what the label says, line by line.
TRUTH = {
    "brand": "SAJ",
    "product_type": "HYBRID INVERTER",
    "model": "H2-10K-T3",
    "ratings": [
        ["Max. PV input voltage", "1000 V"],
        ["MPPT voltage range", "160-950 V"],
        ["Battery voltage", "180-750 V"],
        ["Rated power", "10000 W"],
        ["Rated AC voltage", "3/N/PE 230/400 V"],
        ["Rated frequency", "50 Hz"],
        ["Max. AC output current", "3 x 16 A"],
        ["Protective class", "I"],
        ["Ingress protection", "IP65"],
    ],
    "serial": "S/N: H2T3K10A2609000123",
}

W, H = 960, 600
label = Image.new("RGB", (W, H), (226, 228, 230))
d = ImageDraw.Draw(label)
d.rectangle([8, 8, W - 9, H - 9], outline=(40, 40, 40), width=4)
# Header band with the brand and the product type.
d.rectangle([12, 12, W - 13, 92], fill=(30, 60, 120))
d.text((36, 22), TRUTH["brand"], font=bold(52), fill=(255, 255, 255))
d.text((560, 38), TRUTH["product_type"], font=bold(30), fill=(255, 255, 255))
d.text((36, 108), "Model: " + TRUTH["model"], font=bold(34), fill=(20, 20, 20))
y = 160
for name, value in TRUTH["ratings"]:
    d.text((36, y), name, font=regular(26), fill=(25, 25, 25))
    d.text((520, y), value, font=bold(26), fill=(25, 25, 25))
    d.line([36, y + 34, W - 36, y + 34], fill=(150, 150, 150), width=1)
    y += 42
d.text((36, H - 52), TRUTH["serial"], font=regular(24), fill=(25, 25, 25))
d.text((700, H - 56), "CE  IEC 62109", font=bold(26), fill=(25, 25, 25))

# A phone-photo look: a slight tilt on a darker background, mild blur and sensor noise.
canvas = Image.new("RGB", (W + 80, H + 80), (88, 92, 96))
tilted = label.rotate(2.5, resample=Image.BICUBIC, expand=True, fillcolor=(88, 92, 96))
canvas.paste(tilted, ((canvas.width - tilted.width) // 2, (canvas.height - tilted.height) // 2))
canvas = canvas.filter(ImageFilter.GaussianBlur(0.8))
random.seed(230)
px = canvas.load()
for _ in range(60000):
    x, yy = random.randrange(canvas.width), random.randrange(canvas.height)
    r, g, b = px[x, yy]
    n = random.randint(-28, 28)
    px[x, yy] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
# A 64-colour palette keeps the fixture small enough for the repository.
canvas.quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(out / "nameplate-probe.png", optimize=True)
(out / "nameplate-probe.truth.json").write_text(json.dumps(TRUTH, indent=2) + "\n")

# A one-page PDF with a real text layer (Helvetica), written by hand so the bytes are known.
lines = [
    "SAJ H2-10K-T3 datasheet excerpt (probe fixture)",
    "Rated power 10000 W",
    "Battery voltage 180-750 V",
]
stream = "BT /F1 14 Tf 72 720 Td 18 TL " + " ".join(f"({t}) Tj T*" for t in lines) + " ET"
objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
]
pdf = b"%PDF-1.4\n"
offsets = []
for i, body in enumerate(objects, start=1):
    offsets.append(len(pdf))
    pdf += f"{i} 0 obj\n{body}\nendobj\n".encode()
xref = len(pdf)
pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
for off in offsets:
    pdf += f"{off:010d} 00000 n \n".encode()
pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
(out / "datasheet-probe.pdf").write_bytes(pdf)
print(canvas.size, (out / "nameplate-probe.png").stat().st_size, len(pdf))
