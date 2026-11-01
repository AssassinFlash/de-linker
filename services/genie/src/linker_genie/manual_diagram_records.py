"""Reviewed manufacturer figures, bounded to exact original PDF pixels.

Coordinates are PDF points measured from the top left of the unrotated page.
Each statement describes the drawing in that entire rectangle, including its
figure identifier. The OCR fragments alone are not the source of the facts.
"""

from typing import Any

_ETR = "307b704c87f25f013609375569c9624e3167c13cd0178a16b079c942da6032b6"
_BAT = "627e5444f47bc7db3afd0b1aeeb27099fcbf8eedfbe15fe7302015743a96bcd2"
_ETR_ANCHOR = {
    "kind": "models",
    "series": [],
    "anchor_id": "307b704c87f2-p1-80b6f14f",
    "anchor_sha256": "b05e88c54a0a0c6826e8d02629ae4a3342ad23e8b2b9af611803f4a8a79df2da",
    "anchor_figure": "ETR model list",
    "anchor_bbox": [20, 90, 395, 150],
    "anchor_pixel_size": [750, 120],
    "anchor_pixel_sha256": "ee9a09f6eae1eb73e06af417b483a4db4c3b6825a8c3ea14f916121c4d9467e1",
    "anchor_quote": "( GW50K-ETR-L-G10 | GW75K-ETR-L-G10 | GW75K-ETR-G10 | GW80K-ETR-G10 || GW99.99K-ETR-G10 | GW100K-ETR-G10 | GW110K-ETR-G10 | GW124.99K-ETR-G10 || GW125K-ETR-G10)",
}
_BAT_ANCHOR = {
    "kind": "models",
    "series": [],
    "anchor_id": "627e5444f47b-p1-2580cb9a",
    "anchor_sha256": "dab902eabf50ce3e50aaee856c8f9a9f051ba8868e70ce9a6119dbedbe8c9851",
    "anchor_figure": "BAT-AC model list",
    "anchor_bbox": [20, 90, 395, 160],
    "anchor_pixel_size": [750, 140],
    "anchor_pixel_sha256": "b78bfde3742bfaaece6f78cb7d1b5894657315feb1054adef6605bc2e90d8f60",
    "anchor_quote": "(GW61.4-BAT-AC-G10 | GW92.1-BAT-AC-G10 | GW102.4-BAT-AC-G10 | GW112.6-BAT-AC-G10)",
}

# Pixel hashes cover RGB bytes rendered at two pixels per PDF point, after
# cropping. They are supplemental to the mandatory complete-PDF SHA-256.
DIAGRAMS: list[dict[str, Any]] = [
    {
        **_ETR_ANCHOR,
        "sha256": _ETR,
        "source_id": "307b704c87f2-p1-3fde8e2d",
        "source_sha256": "f4f2d6651371d1fc5d8a0f2e50e6464ef9ff0699cb5987ba52970be4ed892ec5",
        "source_page": 1,
        "source_section": "ZH ż‡",
        "source_picture": "#/pictures/10",
        "figure": "ETR12510DSC0001",
        "display_section": "Installation figure ETR12510DSC0001",
        "bbox": [420, 345, 790, 490],
        "pixel_size": [740, 290],
        "pixel_sha256": "c5fb860303ec2b5947cc5ed3dc35eca1e7e2488f7524618cb018a7f9833b5d05",
        "excerpt": "The ETR installation figure ETR12510DSC0001 shows minimum clearances of 500 mm above and in front of the inverter, 600 mm on each side, and 1000 mm below. The illustrated mounting inclination is at most 15 degrees from vertical.",
    },
    {
        **_ETR_ANCHOR,
        "sha256": _ETR,
        "source_id": "307b704c87f2-p1-d2cef62e",
        "source_sha256": "61f29665fc6f7dbb9f9682822904a07feec39dc4cbc6e309794cfed8ab6e9b73",
        "source_page": 1,
        "source_section": "ZH ż‡",
        "source_picture": "#/pictures/11",
        "figure": "ETR12510INT0002",
        "display_section": "Wall mounting figure ETR12510INT0002",
        "bbox": [420, 500, 790, 645],
        "pixel_size": [740, 290],
        "pixel_sha256": "fbd15f01ae363ae598d14c68517180ca44682c93dde5f412376b589c747cb65b",
        "excerpt": "For wall mounting, figure ETR12510INT0002 shows the bracket oriented with its UP arrow upwards, 10 mm diameter holes drilled 80 mm deep, and M10 fasteners tightened to 14 Nm to 24 Nm.",
    },
    {
        **_BAT_ANCHOR,
        "sha256": _BAT,
        "source_id": "627e5444f47b-p2-4399a628",
        "source_sha256": "287398567741c651577a190867dcb8e63253c46910ed223c8f8a8160c3a4cc40",
        "source_page": 2,
        "source_section": "Procedure",
        "source_picture": "#/pictures/8",
        "figure": "BAT10INT0005",
        "display_section": "Floor mounting figure BAT10INT0005",
        "bbox": [20, 48, 390, 163],
        "pixel_size": [740, 230],
        "pixel_sha256": "c62601a9903c3f4861d14a0f2cc53f3cf3d2b7624bb97fad58f4d994d2e77c21",
        "excerpt": "For the battery cabinet floor mounting, figure BAT10INT0005 shows a 985 mm by 330 mm hole layout, holes of 14 mm diameter and 80 mm depth, and M12 fasteners tightened to 50 Nm.",
    },
]
