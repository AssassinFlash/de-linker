"""MariaDB export of a corpus: tables, keys, escaping and vectors."""

from pathlib import Path

from index import corpus, mariadb
from index.chunking import Chunk
from index.corpus import DocumentRow
from linker_genie.embedding import pack

SHA = "ab" * 32


def write_corpus(directory: Path, vectors: bool) -> None:
    meta = corpus.Meta(
        "v1", "toy" if vectors else None, 3 if vectors else None, "docling x", 512
    )
    documents = [
        DocumentRow(
            SHA,
            ("https://de-linker.com/a.pdf",),
            "Ben's \\ manual",
            "",
            ("GoodWe",),
            ("GW10K-ET",),
            "manual",
            "en",
            3,
            "indexed",
        )
    ]
    chunks = [
        Chunk(f"c{i}", SHA, 1, "", "text", "h", f"text {i} it's", "en", 5)
        for i in range(3)
    ]
    corpus.write(
        directory,
        meta,
        documents,
        [(101, "GW10K-ET")],
        chunks,
        [pack([1.0, 0.0, 0.5])] * 3 if vectors else None,
    )


def test_quote_escapes_backslashes_and_quotes() -> None:
    assert mariadb.quote("Ben's \\ x") == "'Ben\\'s \\\\ x'"


def test_vectors_become_a_not_null_vector_column_under_a_cosine_index(
    tmp_path: Path,
) -> None:
    write_corpus(tmp_path / "c", vectors=True)

    mariadb.export(tmp_path / "c", tmp_path / "out.sql", prefix="wp_")

    sql = (tmp_path / "out.sql").read_text()
    assert "CREATE TABLE `wp_genie_chunks`" in sql
    assert "`embedding` VECTOR(3) NOT NULL" in sql
    assert "VECTOR INDEX (`embedding`) DISTANCE=cosine" in sql
    assert "FULLTEXT KEY `words` (`header`, `text`)" in sql
    assert sql.count("VEC_FromText('[1,0,0.5]')") == 3
    assert "'Ben\\'s \\\\ manual'" in sql
    assert "(101, 'GW10K-ET')" in sql


def test_a_keywords_only_corpus_has_no_vector_column(tmp_path: Path) -> None:
    write_corpus(tmp_path / "c", vectors=False)

    mariadb.export(tmp_path / "c", tmp_path / "out.sql", prefix="wp_")

    sql = (tmp_path / "out.sql").read_text()
    assert "VECTOR" not in sql
    assert "FULLTEXT KEY" in sql


def test_inserts_are_batched(tmp_path: Path) -> None:
    write_corpus(tmp_path / "c", vectors=False)

    mariadb.export(tmp_path / "c", tmp_path / "out.sql", prefix="x_")

    assert (tmp_path / "out.sql").read_text().count("INSERT INTO `x_genie_chunks`") == 1
