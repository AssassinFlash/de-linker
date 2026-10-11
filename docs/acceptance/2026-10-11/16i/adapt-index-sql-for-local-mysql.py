"""Adapt #10's MariaDB index SQL to a local instance (Homebrew MySQL 9.6).

    python3 docs/acceptance/2026-10-11/16i/adapt-index-sql-for-local-mysql.py \
        ~/de-linker-data/index/builds/<build>/index-mariadb.sql /tmp/index-mariadb-local.sql
    mysql --defaults-extra-file=~/de-linker-local/linker_local.my.cnf \
        -u linker_local linker_<instance> < /tmp/index-mariadb-local.sql

The local stack runs Homebrew MySQL, the shared host runs MariaDB 11.8.9
(docs/local-stack.md states the difference). Two constructs of the exported SQL
are MariaDB-only; the import fails on the first of them, so both are rewritten
here and nothing else is touched:

1. `VECTOR INDEX (embedding) DISTANCE=cosine` is MariaDB 11.7+ syntax; MySQL
   9.6 rejects it with error 1064. The clause is dropped together with the comma
   that joined it to the FULLTEXT key, so the table keeps its FULLTEXT index.
2. MariaDB's `VEC_FromText('[...]')` becomes MySQL's `STRING_TO_VECTOR('[...]')`.
   Both store float32 little-endian, both parse the same bracketed number list.

The vectors themselves stay: the chunks land with their `VECTOR(3072)` column
populated. They are not searchable on MySQL — it has no vector distance function
(`VEC_DISTANCE_COSINE`, `COSINE_DISTANCE` and `DISTANCE` are all absent, 1305) —
so the ability's dense path falls back to FULLTEXT locally, which is what the
probe beside this file exercises.
"""

import sys
from pathlib import Path

source, target = Path(sys.argv[1]), Path(sys.argv[2])
dropped = replaced = 0
with source.open(encoding="utf-8", errors="surrogateescape") as inp, target.open(
    "w", encoding="utf-8", errors="surrogateescape"
) as out:
    for number, line in enumerate(inp, start=1):
        if "VECTOR INDEX (`embedding`) DISTANCE=cosine" in line:
            dropped += 1
            continue
        if line.startswith("  FULLTEXT KEY `words` (`header`, `text`),"):
            # The vector index was the next line; its comma goes with it.
            line = line.replace("(`header`, `text`),", "(`header`, `text`)")
        if "VEC_FromText(" in line:
            replaced += line.count("VEC_FromText(")
            line = line.replace("VEC_FromText(", "STRING_TO_VECTOR(")
        out.write(line)
        if number % 20000 == 0:
            print(f"{number} lines", file=sys.stderr, flush=True)
print(f"dropped {dropped} vector-index clauses, replaced {replaced} VEC_FromText calls")
