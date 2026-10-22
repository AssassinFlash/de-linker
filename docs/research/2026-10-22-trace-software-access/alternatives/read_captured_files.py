"""Retrieve source PDFs that Apify already captured, then extract read-only text.

No source-host request, browser, installation, account, or agreement acceptance.
Credentials stay in memory; signed Apify retrieval queries are omitted locally.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "read_apify_source_pdf",
    ROOT.parents[1] / "2026-10-22-roof-europe-precedents" / "engineering-study" / "extract_captured_files.py",
)
assert spec and spec.loader
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
reader.ROOT = ROOT
reader.FILES = ROOT / "captured-files"
reader.FILES.mkdir(exist_ok=True)

if __name__ == "__main__":
    reader.main()
