"""Offline build of the document index (`just index`), run on the Mac, never on the VPS.

inventory -> parse -> chunk -> embed -> store; the result is one SQLite file plus
its manifest, published by `ops/publish_index.py`. Spec: docs/specs/10-knowledge-index.md.
"""
