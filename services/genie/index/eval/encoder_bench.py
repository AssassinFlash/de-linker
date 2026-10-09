"""Query-encoder benchmark of the embedding bake-off: latency and memory on this host.

Measures one model variant per run, in its own process, so its memory is its own:
- latency of each of the questions encoded one at a time (tokenize, infer, pool,
  normalize), after one warm-up query whose time is reported apart;
- the process RSS after loading and its peak (VmRSS, VmHWM);
- the host's MemAvailable before loading, after loading and its lowest point.
The bake-off ran it on the VPS (docs/research/2026-10-09/embedding-bakeoff.md) in a
throwaway uv environment under /tmp/bench-<date>/, with:
    --onnx <file> --tokenizer <tokenizer.json> --pooling cls|mean|sentence_embedding --prefix "query: "
or  --sentence-transformer <hub id>     (PyTorch fp32 through sentence-transformers)
It prints one JSON object. Needs numpy plus onnxruntime and tokenizers, or
sentence-transformers, and this package on the path for its token cap.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from linker_genie.embedding import MAX_TOKENS


def proc_mb(path: str, field: str) -> float | None:
    """A kB figure from a /proc file, in MB; None where /proc does not exist."""
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith(field + ":"):
                return int(line.split()[1]) / 1024
    except OSError:
        return None
    return None


def mem_available() -> float | None:
    return proc_mb("/proc/meminfo", "MemAvailable")


def onnx_encoder(
    onnx: Path, tokenizer_file: Path, pooling: str, prefix: str
) -> Callable[[str], Any]:
    import numpy as np
    import onnxruntime
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    tokenizer.enable_truncation(MAX_TOKENS)
    options = onnxruntime.SessionOptions()
    # The VPS runtime rule (owner, 2026-10-09): one thread, and no spinning while idle,
    # so the encoder never holds the single core the engine also needs.
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    options.add_session_config_entry("session.inter_op.allow_spinning", "0")
    session = onnxruntime.InferenceSession(
        str(onnx), options, providers=["CPUExecutionProvider"]
    )
    inputs = {item.name for item in session.get_inputs()}
    outputs = [item.name for item in session.get_outputs()]

    def encode(text: str) -> Any:
        encoding = tokenizer.encode(prefix + text)
        ids = np.array([encoding.ids], dtype=np.int64)
        mask = np.array([encoding.attention_mask], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in inputs:
            feed["token_type_ids"] = np.zeros_like(ids)
        result = dict(zip(outputs, session.run(None, feed), strict=True))
        if pooling == "sentence_embedding":
            vector = result["sentence_embedding"][0]
        elif pooling == "cls":
            vector = result[outputs[0]][0][0]
        else:
            hidden = result[outputs[0]][0]
            vector = (hidden * mask[0][:, None]).sum(axis=0) / mask[0].sum()
        return vector / np.linalg.norm(vector)

    return encode


def torch_encoder(model: str, prefix: str) -> Callable[[str], Any]:
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(1)
    transformer = SentenceTransformer(model, device="cpu")
    return lambda text: transformer.encode([prefix + text], normalize_embeddings=True)[
        0
    ]


def run(
    encode_factory: Callable[[], Callable[[str], Any]], questions: Sequence[str]
) -> dict[str, Any]:
    before = mem_available()
    started = time.perf_counter()
    encode = encode_factory()
    loaded = time.perf_counter()
    after_load = mem_available()
    rss_loaded = proc_mb("/proc/self/status", "VmRSS")
    first_started = time.perf_counter()
    encode(questions[0])
    first = time.perf_counter() - first_started
    lowest = mem_available()
    latencies = []
    for question in questions:
        tick = time.perf_counter()
        encode(question)
        latencies.append(time.perf_counter() - tick)
        now = mem_available()
        if now is not None and (lowest is None or now < lowest):
            lowest = now
    ordered = sorted(latencies)
    return {
        "questions": len(questions),
        "load_seconds": round(loaded - started, 2),
        "first_query_ms": round(first * 1000, 1),
        "p50_ms": round(statistics.median(ordered) * 1000, 1),
        "p95_ms": round(ordered[max(0, round(0.95 * len(ordered)) - 1)] * 1000, 1),
        "max_ms": round(ordered[-1] * 1000, 1),
        "rss_loaded_mb": rss_loaded and round(rss_loaded),
        "rss_peak_mb": (peak := proc_mb("/proc/self/status", "VmHWM")) and round(peak),
        "mem_available_before_mb": before and round(before),
        "mem_available_loaded_mb": after_load and round(after_load),
        "mem_available_lowest_mb": lowest and round(lowest),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark one query encoder on this host."
    )
    parser.add_argument("--variant", required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--onnx", type=Path)
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument(
        "--pooling", choices=["cls", "mean", "sentence_embedding"], default="mean"
    )
    parser.add_argument("--sentence-transformer")
    parser.add_argument("--prefix", default="")
    args = parser.parse_args(argv)
    try:
        # This process, not the engine or anything else on the host, is what the
        # kernel's OOM killer should pick if a variant does not fit.
        Path(f"/proc/{os.getpid()}/oom_score_adj").write_text("1000")
    except OSError:
        pass
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if args.sentence_transformer:
        result = run(
            lambda: torch_encoder(args.sentence_transformer, args.prefix), questions
        )
    else:
        result = run(
            lambda: onnx_encoder(args.onnx, args.tokenizer, args.pooling, args.prefix),
            questions,
        )
    print(json.dumps({"variant": args.variant, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
