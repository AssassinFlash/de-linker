"""Apify-only collection of actual official tool access and sample paths."""
import importlib.util
from pathlib import Path
import time
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent
helper = ROOT.parents[1] / "2026-10-22-roof-europe-precedents" / "collect_sources.py"
spec = importlib.util.spec_from_file_location("access_collector", helper)
assert spec and spec.loader
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
collector.BASE = ROOT
original_api = collector.api


def bounded_api(path, payload=None):
    if path.endswith("/runs") and payload is not None:
        path += "?memory=2048"
    # Retry read-only API access after a transient local proxy failure. Never
    # retry actor creation: a lost POST response could otherwise start it twice.
    for attempt in range(3):
        try:
            return original_api(path, payload)
        except (URLError, TimeoutError):
            if payload is not None or attempt == 2:
                raise
            time.sleep(attempt + 1)


collector.api = bounded_api
if __name__ == "__main__":
    collector.main()
