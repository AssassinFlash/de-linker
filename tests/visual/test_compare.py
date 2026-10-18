"""Guard the exact-pixel contract through the shared command's public CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class ExactPixelComparison(unittest.TestCase):
    def test_only_declared_region_may_differ(self):
        for point, expected_exit in (((0, 0), 0), ((1, 1), 1)):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "capture.json").write_text(json.dumps({
                    "cases": [{"path": "/", "stem": "home", "width": 2,
                               "language": "en", "headerHeight": 1,
                               "ruledRegions": [{"name": "new registration entry",
                                                 "bounds": [0, 0, 1, 1]}]}],
                    "allowedHeaderChanges": [],
                }))
                image = Image.new("RGB", (2, 2))
                image.save(root / "home-2-live.png")
                image.putpixel(point, (0, 1, 0))
                image.save(root / "home-2-local.png")
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("compare.py")), directory], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                row = json.loads((root / "results.json").read_text())[0]
                self.assertEqual(row["unmasked_different_pixels"], 1)
                self.assertEqual(row["outside_ruled_different_pixels"], expected_exit)

    def test_exact_rgb_and_dimensions(self):
        # A one-level green change rounds to zero with luminance conversion.
        # It must still fail the exact RGB contract, just like a size change.
        for scenario, expected_exit, expected_pixels in (
            ("equal", 0, 0),
            ("one_green_level", 1, 1),
            ("different_size", 1, None),
        ):
            with (
                self.subTest(scenario=scenario),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                (root / "capture.json").write_text(
                    json.dumps(
                        {
                            "cases": [
                                {
                                    "path": "/",
                                    "stem": "home",
                                    "width": 2,
                                    "language": "en",
                                    "headerHeight": 1,
                                }
                            ],
                            "allowedHeaderChanges": [],
                        }
                    )
                )
                image = Image.new("RGB", (2, 2))
                image.save(root / "home-2-live.png")
                if scenario == "one_green_level":
                    image.putpixel((1, 0), (0, 1, 0))
                elif scenario == "different_size":
                    image = Image.new("RGB", (2, 3))
                image.save(root / "home-2-local.png")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("compare.py")),
                        directory,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                if expected_pixels is None:
                    self.assertIn("size mismatch", result.stderr)
                else:
                    row = json.loads((root / "results.json").read_text())[0]
                    self.assertEqual(row["unmasked_different_pixels"], expected_pixels)


if __name__ == "__main__":
    unittest.main()
