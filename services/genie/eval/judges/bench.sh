#!/usr/bin/env bash
# Latency and memory of the open judges on this host: the production VPS (1 vCPU,
# 3.9 GB, no GPU) or the Mac. Each judge gets its own llama.cpp server, started at the
# lowest CPU priority as the background worker would run, and is called one request at
# a time by `judges bench` (standard library only, so the VPS needs nothing installed).
#
# usage: bench.sh LLAMA_SERVER MODEL_DIR IDS OUT_DIR JUDGE...
#   MODEL_DIR holds <repo>/<file>.gguf as fetched from Hugging Face (ggml-org).
set -euo pipefail

server=$1 models=$2 ids=$3 out=$4
shift 4
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"

for judge in "$@"; do
    case $judge in
        # One slot and a 4,096-token context, as the worker would run it. Measured
        # prompt tokens (runs/formal-20261010): the largest encoder input is p231 at
        # 3,869 tokens (julia1; laya's largest is p288 at 3,545), leaving ~227 tokens
        # of headroom; the largest chat prompt is p288 at 1,703 (qwen3-1.7b). Encoder
        # models read a whole pass in one physical batch, so their batch sizes match
        # the context.
        julia1) file=Julia-1-GGUF/Julia-1-Q8_0.gguf port=18081 args=(-c 4096 -np 1 -b 4096 -ub 4096) ;;
        laya) file=Laya-GGUF/Laya-Q8_0.gguf port=18082 args=(-c 4096 -np 1 -b 4096 -ub 4096) ;;
        lev) file=lev-GGUF/lev-Q4_K_M.gguf port=18083 args=(-c 4096 -np 1) ;;
        qwen3-1.7b) file=Qwen3-1.7B-GGUF/Qwen3-1.7B-Q4_K_M.gguf port=18084 args=(-c 4096 -np 1 --jinja) ;;
        *) echo "unknown judge $judge" >&2; exit 2 ;;
    esac
    nice -n 19 "$server" -m "$models/$file" --host 127.0.0.1 --port "$port" "${args[@]}" \
        >"$out/$judge.server.log" 2>&1 &
    pid=$!
    for _ in $(seq 1 120); do
        if curl -s -m 2 --noproxy '*' "http://127.0.0.1:$port/health" | grep -q ok; then break; fi
        sleep 2
    done
    PYTHONPATH="$here/src" nice -n 19 python3 -m linker_judges.cli bench \
        --judge "$judge" --pid "$pid" --ids "$ids" --out "$out/$judge.jsonl"
    kill "$pid"
    wait "$pid" 2>/dev/null || true
done
