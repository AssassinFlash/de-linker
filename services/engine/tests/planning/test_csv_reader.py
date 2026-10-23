"""Concurrent bounded sources retain their original cells without an implicit cap."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from linker_engine.planning.csv_reader import source_reader


def test_a_shorter_concurrent_source_cannot_lower_a_larger_readers_cell_limit() -> None:
    ready = Barrier(2)

    def read_cell(size: int) -> str:
        text = "note\n" + "x" * size + "\n"
        reader = source_reader(text, ";")
        assert next(reader) == ["note"]
        ready.wait(timeout=5)
        return next(reader)[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        large = pool.submit(read_cell, 200_000)
        small = pool.submit(read_cell, 10)
        assert large.result(timeout=10) == "x" * 200_000
        assert small.result(timeout=10) == "x" * 10
