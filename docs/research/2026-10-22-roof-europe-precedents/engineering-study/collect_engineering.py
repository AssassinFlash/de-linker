"""Use the existing Apify collector, writing only this deeper study's assets."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("roof_apify_collector", ROOT.parent / "collect_sources.py")
assert spec and spec.loader
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
collector.BASE = ROOT
# Per-run research resource choice under the account's existing shared 16 GiB
# Actor cap. This does not change the account, plan, budget, or global config.
original_api = collector.api


def api_with_run_memory(path, payload=None):
    if path.endswith("/runs") and payload is not None:
        path += "?memory=2048"
    return original_api(path, payload)


collector.api = api_with_run_memory
collector.main()
