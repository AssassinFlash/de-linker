"""Decoded size budget for the installer logo in both PDF entry points."""

from PIL import Image

# A 16-megapixel RGBA logo needs 64 MiB before resampling to the printed mark.
MAX_LOGO_PIXELS = 16 * 1024 * 1024


def logo_dimensions(image: Image.Image) -> tuple[int, int]:
    width, height = image.size
    if width * height > MAX_LOGO_PIXELS:
        raise ValueError("logo exceeds the decoded image budget")
    return width, height
