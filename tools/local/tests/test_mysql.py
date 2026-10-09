from linker_local.mysql import _like_literal


def test_like_patterns_match_the_database_name_only() -> None:
    # SHOW DATABASES LIKE 'linker_a' would also match linkerXa.
    assert _like_literal("linker_a") == "linker\\_a"
