import re

from linker_local.secret import password


def test_passwords_are_24_characters_that_need_no_quoting() -> None:
    # mysql.py puts the password into SQL between single quotes.
    passwords = {password() for _ in range(50)}

    assert all(re.fullmatch(r"[A-Za-z0-9_-]{24}", candidate) for candidate in passwords)
    assert len(passwords) == 50
