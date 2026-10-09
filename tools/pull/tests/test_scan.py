"""The check every snapshot's SQL passes before the snapshot is kept.

The lines are written as mysqldump writes them: double quotes inside a value
carry a backslash.
"""

from __future__ import annotations

import gzip
from pathlib import Path

from linker_pull.scan import scan_dump, scan_lines

STAFF = ["owner@mail.example"]


def test_what_the_rules_keep_passes() -> None:
    findings = scan_lines(
        [
            "('owner@mail.example','Owner@Mail.example'),\n",
            "('customer-18@example.test','sales@de-linker.com','sales@sunriverinverter.com'),\n",
            "('<img src=\\\"logo@2x.png\\\">','@media print','a:1:{s:7:\\\"api_key\\\";s:0:\\\"\\\";}'),\n",
            "('{\\\"token\\\": \\\"\\\", \\\"use_api_key\\\": \\\"yes\\\"}','define( \\'SMTP_PASS\\', \\'\\' );'),\n",
        ],
        STAFF,
    )

    assert findings.clean, findings.as_dict()
    assert findings.emails == {
        "staff account": 2,
        "example.test": 1,
        "de-linker.com": 1,
        "sunriverinverter.com": 1,
    }


def test_each_kind_of_leak_is_found_and_addresses_are_reported_by_domain_only() -> None:
    findings = scan_lines(
        [
            "('$wp$2y$10$abcdefghijklmnopqrstuuMZcYxN0cqI7m3Ve6U2HHq0cS8yEJ9g.'),\n",
            "('1760000000:$generic$5f4dcc3b5aa765d61d8327deb882cf99','$P$ alone'),\n",
            "(5,1,'_application_passwords','a:0:{}'),\n",
            "('sk_live_0123456789abcdefghijklmnop','whsec_0123456789abcdef0123456789abcdef'),\n",
            '(\'[\\"woocommerce_created_customer\\",{\\"user_pass\\":\\"Gen3rated!Pass\\"}]\'),\n',
            '(\'a:1:{s:9:\\"smtp_pass\\";s:7:\\"hunter2\\";}\'),\n',
            "('$token = \\'0f0f0f0f\\';'),\n",
            "('Charge ID: ch_3SAbCdEfGhIjKlMn0pQrStUv'),\n",
            "('Refunded 0.01 EUR (Refund ID: pyr_1Q2w3e4r5t6y7u8i9o0p1q2w).'),\n",
            "('jana@kunde.example','jörg.müller@kunde.example','mailto:max%40post.example'),\n",
        ],
        STAFF,
    )

    assert findings.password_hashes == {"$wp$": 1, "$generic$": 1, "$P$": 1}
    assert findings.application_passwords == 1
    assert findings.secrets == {"shape": 2, "user_pass": 1, "smtp_pass": 1, "token": 1}
    assert findings.payment_ids == 2
    assert findings.unexpected_domains == {"kunde.example": 2, "post.example": 1}
    assert "jana" not in str(findings.as_dict())
    assert not findings.clean


def test_a_gzip_file_is_read_as_text(tmp_path: Path) -> None:
    dump = tmp_path / "db.sql.gz"
    with gzip.open(dump, "wt", encoding="utf-8") as handle:
        handle.write("('customer-1@example.test','Grüße');\n")

    findings = scan_dump(dump, STAFF)

    assert findings.clean
    assert findings.emails == {"example.test": 1}
