"""An image as deepseek-flash is shown it: upright, about 1.69 megapixels, a JPEG (#236).

Shared by the photos a customer attaches (attachments.py) and the PDF pages rendered
in the PDF worker (pdfwork.py), so both are drawn the same way.
"""

from __future__ import annotations

import io
import math

from PIL import Image

# deepseek-flash scales every image to about the area of 1300 × 1300 pixels before it
# reads it (docs/research/2026-10-17-deepseek-flash-vision/ §3.3, "roughly that of a
# 1300×1300 image"); sending that size keeps the detail it reads and nothing it throws
# away (research §9, item 2).
TARGET_PIXELS = 1300 * 1300
# JPEG quality of the re-encoded image: libjpeg's 75 is its default; a nameplate's small
# print reads better a step above it, and the measured photos of eval/attachments stay
# a few hundred kilobytes at 85.
JPEG_QUALITY = 85


def encode(image: Image.Image) -> bytes:
    """The image at most TARGET_PIXELS, as a JPEG without metadata."""
    rgb = image.convert("RGB")
    pixels = rgb.width * rgb.height
    if pixels > TARGET_PIXELS:
        scale = math.sqrt(TARGET_PIXELS / pixels)
        rgb = rgb.resize(
            (
                max(1, math.floor(rgb.width * scale)),
                max(1, math.floor(rgb.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )
    out = io.BytesIO()
    # No `exif=`, no `icc_profile=`: what the camera wrote (GPS among it) stays behind.
    rgb.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()
