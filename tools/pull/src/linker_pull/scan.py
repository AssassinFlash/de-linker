"""The check a snapshot's SQL must pass before the snapshot is kept.

It reads the written file as text, not the anonymizer's bookkeeping, and looks
wider than the anonymizer changes: password hashes by their prefixes alone,
application passwords, credentials by their shape and by the name they are
stored under (in JSON, in serialized PHP and in PHP code, with the SQL dump's
escaped quotes), Stripe object ids, and e-mail addresses written plainly or
URL-encoded. An address passes only if the anonymizer's rule keeps it
(anonymize.kept_as); what it may not hold is reported by kind and domain,
never by value.

The check is enumeration, not proof: it finds the shapes and prefixes it
knows (HASH, SECRET, PAYMENT_ID, SECRET_KEY). A credential of an unknown
shape, under an unrelated name, passes — which is why the anonymizer's rule
side ("anything that looks like a credential goes") is the primary defense
and this scan is the backstop that catches rules the data outgrew.
"""

from __future__ import annotations

import gzip
import re
from collections import Counter
from collections.abc import Callable, Collection, Iterable
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO
from urllib.parse import unquote

from linker_pull.anonymize import (
    EMAIL,
    FILE_SUFFIXES,
    HASH,
    PAYMENT_ID,
    SECRET,
    SECRET_KEY,
    SETTING_VALUE,
    kept_as,
)

# The prefixes WordPress's hashes start with, counted wherever they occur
# (the acceptance's grep); HASH also finds bcrypt and argon2 hashes without them.
HASH_PREFIXES = ("$P$", "$wp$", "$generic$")
# The meta key WordPress stores application passwords under, as a quoted SQL value.
APPLICATION_PASSWORDS = "'_application_passwords'"
# "name": "value" in JSON and s:4:"name";s:5:"value"; in serialized PHP, with
# the backslash mysqldump writes before every double quote of a value.
JSON_MEMBER = re.compile(r'\\?"(\w+)\\?"\s*:\s*\\?"((?:[^"\\]|\\[^"])*)\\?"')
SERIALIZED_MEMBER = re.compile(
    r's:\d+:\\?"(\w+)\\?";s:\d+:\\?"((?:[^"\\]|\\[^"])*)\\?";'
)
# define( 'NAME', '…' ), $name = '…' and 'name' => '…' in PHP code, whose
# quotes the dump escapes too.
CODE_MEMBER = re.compile(
    r"""(?:define\s*\(\s*\\?['"](\w+)\\?['"]\s*,\s*|\$(\w+)\s*=\s*|\\?['"](\w+)\\?['"]\s*=>\s*)"""
    r"""\\?['"]((?:[^'"\\]|\\[^'"])*)\\?['"]"""
)
# An address with its @ URL-encoded, as in a query string.
ENCODED_EMAIL = re.compile(r"[\w.+-]+%40(?:[\w-]+\.)+[^\W\d_]{2,63}", re.IGNORECASE)


@dataclass
class Findings:
    password_hashes: Counter[str] = field(default_factory=Counter)
    application_passwords: int = 0
    # Credentials by kind: "shape", or the name they are stored under.
    secrets: Counter[str] = field(default_factory=Counter)
    payment_ids: int = 0
    emails: Counter[str] = field(default_factory=Counter)
    unexpected_domains: Counter[str] = field(default_factory=Counter)

    @property
    def clean(self) -> bool:
        return not (
            self.password_hashes
            or self.application_passwords
            or self.secrets
            or self.payment_ids
            or self.unexpected_domains
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "clean": self.clean,
            "password_hashes": dict(sorted(self.password_hashes.items())),
            "application_passwords": self.application_passwords,
            "secrets": dict(sorted(self.secrets.items())),
            "payment_ids": self.payment_ids,
            "emails": dict(sorted(self.emails.items())),
            "unexpected_email_domains": dict(sorted(self.unexpected_domains.items())),
        }


def scan_lines(lines: Iterable[str], staff_emails: Iterable[str]) -> Findings:
    staff = {address.lower() for address in staff_emails}
    findings = Findings()
    for line in lines:
        if "$" in line:
            for prefix in HASH_PREFIXES:
                if prefix in line:
                    findings.password_hashes[prefix] += line.count(prefix)
            for found in HASH.finditer(line):
                if not found.group().startswith(HASH_PREFIXES):
                    findings.password_hashes["bcrypt/argon2"] += 1
        findings.application_passwords += line.count(APPLICATION_PASSWORDS)
        shapes = len(SECRET.findall(line))
        if shapes:
            findings.secrets["shape"] += shapes
        for pattern in (JSON_MEMBER, SERIALIZED_MEMBER):
            for found in pattern.finditer(line):
                _credential(found.group(1), found.group(2), findings)
        for found in CODE_MEMBER.finditer(line):
            name = found.group(1) or found.group(2) or found.group(3) or ""
            _credential(name, found.group(4), findings)
        findings.payment_ids += len(PAYMENT_ID.findall(line))
        if "@" in line:
            for found in EMAIL.finditer(line):
                if found.group(1).lower() not in FILE_SUFFIXES:
                    _address(found.group(), staff, findings)
        if "%40" in line:
            for found in ENCODED_EMAIL.finditer(line):
                _address(unquote(found.group()), staff, findings)
    return findings


def scan_dump(path: Path, staff_emails: Iterable[str]) -> Findings:
    """Scan a dump, gzip-compressed (.sql.gz) or plain (.sql), like _text() elsewhere."""
    with closing(_text(path)) as dump:
        return scan_lines(dump, staff_emails)


def _text(path: Path) -> IO[str]:
    """A dump file as text lines, gzip-compressed or not (cli._text's rule)."""
    opener: Callable[..., IO[str]] = gzip.open if path.suffix == ".gz" else open
    return opener(path, "rt", encoding="utf-8", errors="surrogateescape")


def _credential(name: str, value: str, findings: Findings) -> None:
    if SECRET_KEY.search(name) and not SETTING_VALUE.fullmatch(value.strip()):
        findings.secrets[name.lower()] += 1


def _address(address: str, staff: Collection[str], findings: Findings) -> None:
    lower = address.lower()
    reason = kept_as(lower, staff)
    if reason is None:
        findings.emails["unexpected"] += 1
        findings.unexpected_domains[lower.rpartition("@")[2]] += 1
    else:
        findings.emails[reason] += 1
