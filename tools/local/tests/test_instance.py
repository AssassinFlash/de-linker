from pathlib import Path

import pytest

from linker_local.instance import NAME_MAX_LENGTH, Instance, check_name


@pytest.mark.parametrize("name", ["a", "t5", "review", "a_b", "x" * NAME_MAX_LENGTH])
def test_accepts_names_that_fit_a_database_a_directory_and_a_url(name: str) -> None:
    check_name(name)


@pytest.mark.parametrize(
    "name", ["", "A", "5a", "a-b", "a.b", "../a", "x" * (NAME_MAX_LENGTH + 1)]
)
def test_rejects_other_names(name: str) -> None:
    with pytest.raises(ValueError, match="not an instance name"):
        check_name(name)


def test_the_longest_name_makes_a_64_character_database_name() -> None:
    instance = Instance("x" * NAME_MAX_LENGTH, 1, 2, 3, Path("/data"))

    assert len(instance.database) == 64


def test_derives_every_location_from_the_name_and_the_data_root() -> None:
    instance = Instance("a", 8888, 8889, 8890, Path("/data"))

    assert instance.database == "linker_a"
    assert instance.url == "http://127.0.0.1:8888"
    assert instance.dir == Path("/data/a")
    assert instance.docroot == Path("/data/a/wordpress")
    assert instance.mail_dir == Path("/data/a/mail")
