"""Published page presentation must not inherit a colliding customer's pseudonym."""

from __future__ import annotations

import json

import pytest

from linker_pull import phpserial
from linker_pull.anonymize import Anonymizer, accounts_from_dump
from linker_pull.sqldump import Insert, Table, Value, read

PUBLIC = "chester@de-linker.com"
PSEUDONYM = "customer-42@example.test"


def dump_table(name: str, columns: list[str], rows: list[list[str | None]]) -> str:
    schema = ",\n".join(f"  `{column}` text" for column in columns)
    insert = Insert(Table(name, columns), [[Value.of(v) for v in row] for row in rows])
    return f"CREATE TABLE `{name}` (\n{schema}\n) ENGINE=InnoDB;\n" + insert.line()


def customer() -> str:
    return dump_table(
        "wp_users",
        [
            "ID",
            "user_login",
            "user_pass",
            "user_nicename",
            "user_email",
            "user_url",
            "user_activation_key",
            "display_name",
        ],
        [
            [
                "42",
                "company-customer",
                "",
                "company-customer",
                PUBLIC,
                "",
                "",
                "Customer",
            ]
        ],
    ) + dump_table(
        "wp_usermeta",
        ["umeta_id", "user_id", "meta_key", "meta_value"],
        [
            ["1", "42", "wp_capabilities", 'a:1:{s:8:"customer";b:1;}'],
            ["2", "42", "billing_email", PUBLIC],
        ],
    )


def cleaned_rows(source: str) -> dict[str, list[dict[str, str | None]]]:
    lines = source.splitlines(keepends=True)
    anonymizer = Anonymizer(accounts_from_dump(iter(lines)))
    result = "".join(anonymizer.run(iter(lines)))
    tables: dict[str, list[dict[str, str | None]]] = {}
    for item in read(iter(result.splitlines(keepends=True))):
        if isinstance(item, Insert):
            tables.setdefault(item.table.name, []).extend(
                {
                    name: value.text
                    for name, value in zip(item.table.columns, row, strict=True)
                }
                for row in item.rows
            )
    return tables


def test_public_company_email_collision_does_not_relax_customer_records() -> None:
    content = f'<p>Contact "Linker": <a href="mailto:{PUBLIC}">{PUBLIC}</a></p>'
    source = (
        customer()
        + dump_table(
            "wp_posts",
            [
                "ID",
                "post_type",
                "post_status",
                "post_password",
                "post_content",
                "post_title",
                "post_excerpt",
            ],
            [["7", "page", "publish", "", content, PUBLIC, PUBLIC]],
        )
        + dump_table(
            "wp_wc_orders",
            [
                "id",
                "billing_email",
                "ip_address",
                "user_agent",
                "customer_note",
                "transaction_id",
            ],
            [["8", PUBLIC, "", "", "", ""]],
        )
        + dump_table(
            "wp_postmeta",
            ["meta_id", "post_id", "meta_key", "meta_value"],
            [["9", "7", "custom_private_note", PUBLIC]],
        )
    )
    rows = cleaned_rows(source)

    assert rows["wp_posts"][0]["post_content"] == content
    assert rows["wp_posts"][0]["post_title"] == PSEUDONYM
    assert rows["wp_posts"][0]["post_excerpt"] == PSEUDONYM
    assert rows["wp_users"][0]["user_email"] == PSEUDONYM
    assert rows["wp_usermeta"][1]["meta_value"] == PSEUDONYM
    assert rows["wp_wc_orders"][0]["billing_email"] == PSEUDONYM
    assert rows["wp_postmeta"][0]["meta_value"] == PSEUDONYM


@pytest.mark.parametrize(
    ("post_type", "status", "password"),
    [
        ("page", "draft", ""),
        ("page", "private", ""),
        ("page", "pending", ""),
        ("page", "future", ""),
        ("page", "trash", ""),
        ("page", "inherit", ""),
        ("page", None, ""),
        ("page", "publish", "protected"),
        ("page", "publish", None),
        ("post", "publish", ""),
        ("product", "publish", ""),
        ("revision", "inherit", ""),
        ("shop_order", "wc-completed", ""),
    ],
)
def test_unconfirmed_public_page_content_keeps_customer_mapping(
    post_type: str, status: str | None, password: str | None
) -> None:
    source = customer() + dump_table(
        "wp_posts",
        [
            "ID",
            "post_type",
            "post_status",
            "post_password",
            "post_content",
            "post_excerpt",
        ],
        [["7", post_type, status, password, PUBLIC, ""]],
    )
    assert cleaned_rows(source)["wp_posts"][0]["post_content"] == PSEUDONYM


def test_public_exception_does_not_bleed_into_the_next_row_or_unknown_table() -> None:
    source = (
        customer()
        + dump_table(
            "wp_posts",
            [
                "ID",
                "post_type",
                "post_status",
                "post_password",
                "post_content",
                "unknown_field",
            ],
            [
                ["7", "page", "publish", "", PUBLIC, PUBLIC],
                ["8", "page", "draft", "", PUBLIC, PUBLIC],
            ],
        )
        + dump_table(
            "wp_unrecognized_content",
            ["post_type", "post_status", "post_password", "post_content"],
            [["page", "publish", "", PUBLIC]],
        )
    )
    rows = cleaned_rows(source)
    assert [row["post_content"] for row in rows["wp_posts"]] == [PUBLIC, PSEUDONYM]
    assert [row["unknown_field"] for row in rows["wp_posts"]] == [PSEUDONYM, PSEUDONYM]
    assert rows["wp_unrecognized_content"][0]["post_content"] == PSEUDONYM


def test_missing_public_status_schema_never_grants_the_exception() -> None:
    source = customer() + dump_table(
        "wp_posts",
        ["ID", "post_type", "post_password", "post_content"],
        [["7", "page", "", PUBLIC]],
    )
    assert cleaned_rows(source)["wp_posts"][0]["post_content"] == PSEUDONYM


@pytest.mark.parametrize(
    "content",
    [
        '<p>Customer\'s "quoted" Contact: chester@de-linker.com</p>\n'
        r'<script>const escaped="\u003c"; const path="C:\schematic.pdf";</script>',
        json.dumps(
            {
                "contact": PUBLIC,
                "html": f'<a href="mailto:{PUBLIC}">Übersicht</a>',
                "path": r"C:\schematic.pdf",
            },
            ensure_ascii=False,
        ).replace("/", r"\/"),
        'a:1:{s:7:"contact";s:21:"chester@de-linker.com";}',
    ],
    ids=["sql-quotes-and-backslashes", "json-escaped-markup", "php-serialized"],
)
def test_public_body_roundtrips_escaping_and_serialized_private_meta(
    content: str,
) -> None:
    source = (
        customer()
        + dump_table(
            "wp_posts",
            ["ID", "post_type", "post_status", "post_password", "post_content"],
            [["7", "page", "publish", "", content]],
        )
        + dump_table(
            "wp_wc_orders_meta",
            ["id", "order_id", "meta_key", "meta_value"],
            [["8", "7", "private_payload", content]],
        )
    )
    rows = cleaned_rows(source)
    assert rows["wp_posts"][0]["post_content"] == content
    private = rows["wp_wc_orders_meta"][0]["meta_value"] or ""
    assert PUBLIC not in private
    assert PSEUDONYM in private
    if phpserial.looks_serialized(content):
        assert private == 'a:1:{s:7:"contact";s:24:"customer-42@example.test";}'
        assert phpserial.rewrite(private, lambda text, key: text) == private
    if content.startswith("{"):
        assert json.loads(private)["contact"] == PSEUDONYM


def test_company_presentation_still_scrubs_guests_and_credentials() -> None:
    content = json.dumps(
        {
            "contact": PUBLIC,
            "buyer": "buyer@customer.test",
            "api_key": "synthetic-secret",
            "smtp_pass": PUBLIC,
        }
    )
    source = customer() + dump_table(
        "wp_posts",
        ["ID", "post_type", "post_status", "post_password", "post_content"],
        [["7", "page", "publish", "", content]],
    )
    row = cleaned_rows(source)["wp_posts"][0]
    assert json.loads(row["post_content"] or "") == {
        "contact": PUBLIC,
        "buyer": "customer-100001@example.test",
        "api_key": "",
        "smtp_pass": "",
    }


def test_comments_and_hpos_metadata_keep_the_original_customer_mapping() -> None:
    source = (
        customer()
        + dump_table(
            "wp_comments",
            [
                "comment_ID",
                "comment_author",
                "comment_author_email",
                "comment_author_IP",
                "comment_agent",
                "comment_author_url",
                "comment_content",
            ],
            [["7", "Client", PUBLIC, "", "", "", f"Note from {PUBLIC}"]],
        )
        + dump_table(
            "wp_wc_orders_meta",
            ["id", "order_id", "meta_key", "meta_value"],
            [["8", "7", "private_note", PUBLIC]],
        )
    )
    rows = cleaned_rows(source)
    assert rows["wp_comments"][0]["comment_author_email"] == PSEUDONYM
    assert rows["wp_comments"][0]["comment_content"] == f"Note from {PSEUDONYM}"
    assert rows["wp_wc_orders_meta"][0]["meta_value"] == PSEUDONYM


@pytest.mark.parametrize("address", [PUBLIC.upper(), "sales@sunriverinverter.com"])
def test_existing_company_domain_policy_is_case_insensitive(address: str) -> None:
    source = customer().replace(PUBLIC, address) + dump_table(
        "wp_posts",
        ["ID", "post_type", "post_status", "post_password", "post_content"],
        [["7", "page", "publish", "", address]],
    )
    rows = cleaned_rows(source)
    assert rows["wp_posts"][0]["post_content"] == address
    assert rows["wp_users"][0]["user_email"] == PSEUDONYM


def test_company_like_subdomain_does_not_grant_public_preservation() -> None:
    address = "chester@de-linker.com.evil.test"
    source = customer().replace(PUBLIC, address) + dump_table(
        "wp_posts",
        ["ID", "post_type", "post_status", "post_password", "post_content"],
        [["7", "page", "publish", "", address]],
    )
    rows = cleaned_rows(source)
    assert rows["wp_posts"][0]["post_content"] == PSEUDONYM
