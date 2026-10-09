"""Where the build keeps its inputs and outputs: outside the repository.

The PDFs, parse cache and built indexes are data, not source (docs/specs/6-live-pull.md
keeps snapshots out of the repo the same way). `LINKER_DATA` moves the root.
"""

import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("LINKER_DATA", "~/de-linker-data")).expanduser()
PDF_DIR = DATA_ROOT / "pdf"
PARSED_DIR = DATA_ROOT / "parsed"
INDEX_DIR = DATA_ROOT / "index"
INVENTORY_PATH = INDEX_DIR / "inventory.json"
