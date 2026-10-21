"""The pseudonymization rules, on the live table structure (tests/fixtures/live-dump.sql).

The fixture's rows are synthetic but shaped like what the live tables held on
2026-10-09: a staff account and customers, an application password, session
tokens, options holding keys, logs and addresses, an order in both storages
with the old plugin's snapshots of the buyer, order notes with Stripe ids, a
review, scheduled jobs (one carrying a plain-text password), snippets (one
holding an NVIDIA key, one the engine token), a contact request, a session.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linker_pull import phpserial, scan
from linker_pull.anonymize import (
    Account,
    Anonymizer,
    accounts_from_dump,
    local_password,
    order_key,
)
from linker_pull.sqldump import Insert, read

FIXTURE = Path(__file__).parent / "fixtures" / "live-dump.sql"
Rows = dict[str, list[dict[str, str | None]]]
STAFF = ["owner@mail.example"]


def fixture_lines() -> list[str]:
    return FIXTURE.read_text().splitlines(keepends=True)


def tables(lines: list[str]) -> Rows:
    found: Rows = {}
    for item in read(iter(lines)):
        if isinstance(item, Insert):
            found.setdefault(item.table.name, []).extend(
                {
                    column: value.text
                    for column, value in zip(item.table.columns, row, strict=True)
                }
                for row in item.rows
            )
    return found


@pytest.fixture(scope="module")
def anonymized() -> tuple[list[str], Anonymizer]:
    anonymizer = Anonymizer(accounts_from_dump(iter(fixture_lines())))
    # The anonymizer yields whole statements; a file of them reads back as lines.
    text = "".join(anonymizer.run(iter(fixture_lines())))
    return text.splitlines(keepends=True), anonymizer


@pytest.fixture(scope="module")
def rows(anonymized: tuple[list[str], Anonymizer]) -> Rows:
    return tables(anonymized[0])


def find(rows: Rows, table: str, column: str, value: str) -> dict[str, str | None]:
    found = [row for row in rows[table] if row[column] == value]
    assert len(found) == 1, (table, column, value)
    return found[0]


def meta(rows: Rows, user_id: str, key: str) -> str | None:
    found = [
        row["meta_value"]
        for row in rows["wp_usermeta"]
        if row["user_id"] == user_id and row["meta_key"] == key
    ]
    assert len(found) <= 1
    return found[0] if found else None


def option(rows: Rows, name: str) -> str | None:
    found = [
        row["option_value"] for row in rows["wp_options"] if row["option_name"] == name
    ]
    return found[0] if found else None


def members(serialized: str) -> dict[str | None, str]:
    """The strings of a serialized value by the key they are stored under (it must parse)."""
    found: dict[str | None, str] = {}

    def collect(text: str, key: str | None) -> str:
        found[key] = text
        return text

    assert phpserial.rewrite(serialized, collect) == serialized
    return found


def test_accounts_and_their_roles_are_read_from_the_dump() -> None:
    accounts = accounts_from_dump(iter(fixture_lines()))

    assert accounts == [
        Account(
            1, "owner@mail.example", "owner@mail.example", frozenset({"administrator"})
        ),
        Account(2, "tester", "test@example.com", frozenset({"customer"})),
        Account(18, "jana.doe", "jdoe@kunde.example", frozenset({"customer"})),
    ]


def test_a_staff_account_keeps_its_login_and_address_and_no_hash(rows: Rows) -> None:
    owner = find(rows, "wp_users", "ID", "1")

    assert owner["user_login"] == "owner@mail.example"
    assert owner["user_email"] == "owner@mail.example"
    assert owner["user_pass"] == local_password(
        "$wp$2y$10$abcdefghijklmnopqrstuuMZcYxN0cqI7m3Ve6U2HHq0cS8yEJ9g."
    )
    assert owner["user_pass"] is not None and "$" not in owner["user_pass"]
    assert meta(rows, "1", "first_name") == "Owner"


def test_a_customer_account_becomes_customer_id(rows: Rows) -> None:
    jana = find(rows, "wp_users", "ID", "18")
    columns = (
        "user_login",
        "user_nicename",
        "user_email",
        "display_name",
        "user_url",
        "user_pass",
    )

    assert {column: jana[column] for column in columns} == {
        "user_login": "customer-18",
        "user_nicename": "customer-18",
        "user_email": "customer-18@example.test",
        "display_name": "Customer 18",
        "user_url": "",
        "user_pass": "",
    }
    assert jana["user_activation_key"] == ""


def test_application_passwords_sessions_and_located_ips_are_dropped(rows: Rows) -> None:
    keys = {row["meta_key"] for row in rows["wp_usermeta"]}

    assert not keys & {
        "_application_passwords",
        "session_tokens",
        "community-events-location",
    }


def test_customer_meta_gets_placeholders_settings_stay_the_rest_is_emptied(
    rows: Rows,
) -> None:
    assert meta(rows, "18", "first_name") == "Customer"
    assert meta(rows, "18", "last_name") == "18"
    assert meta(rows, "18", "nickname") == "customer-18"
    assert meta(rows, "18", "billing_email") == "customer-18@example.test"
    assert meta(rows, "18", "billing_phone") == "+49 30 0000000"
    assert meta(rows, "18", "billing_address_1") == "Musterstraße 1"
    assert meta(rows, "18", "billing_address_2") == ""
    assert meta(rows, "18", "billing_country") == "DE"
    assert meta(rows, "18", "tv_vat_id") == "DE000000000"
    assert meta(rows, "18", "tv_company_name") == "Example Company 18"
    assert meta(rows, "18", "tv_b2b_status") == "approved"
    assert meta(rows, "18", "linker_ai_conversations") == ""
    assert meta(rows, "18", "wp_capabilities") == 'a:1:{s:8:"customer";b:1;}'


def test_transients_credential_options_and_logs_are_dropped(rows: Rows) -> None:
    names = {row["option_name"] for row in rows["wp_options"]}

    assert names == {
        "siteurl",
        "home",
        "admin_email",
        "linker_ai_settings_v1",
        "dlk_widget_state",
        "woocommerce_myaccount_lost_password_endpoint",
        "woocommerce_new_order_settings",
        "dlk_links",
    }


def test_a_value_stored_under_a_credential_name_is_emptied_in_any_table(
    rows: Rows,
) -> None:
    settings = members(option(rows, "linker_ai_settings_v1") or "")
    assert settings["api_key"] == ""
    assert settings["model"] == "deepseek-chat"
    assert settings["max_tokens"] == "800"  # not a credential's name
    widget = json.loads(option(rows, "dlk_widget_state") or "")
    assert widget == {
        "token": "",
        "label": "Kontakt",
        "url": "https://de-linker.com/kontakt/",
    }
    integration = find(rows, "wp_postmeta", "meta_key", "_dlk_integration")[
        "meta_value"
    ]
    assert json.loads(integration or "") == {
        "endpoint": "https://de-linker.com/api/",
        "api_key": "",
        "enabled": "yes",
    }
    assert (
        option(rows, "woocommerce_myaccount_lost_password_endpoint") == "lost-password"
    )


def test_addresses_are_replaced_inside_serialized_values(rows: Rows) -> None:
    settings = members(option(rows, "woocommerce_new_order_settings") or "")

    # Jana's account, the company's mailbox and the staff account.
    assert settings["recipient"] == (
        "sales@de-linker.com, customer-18@example.test, owner@mail.example"
    )


def test_content_keeps_company_mailboxes_and_file_names(rows: Rows) -> None:
    page = find(rows, "wp_posts", "ID", "10")["post_content"] or ""

    assert "sales@de-linker.com" in page
    assert "logo@2x.png" in page
    assert "name@company.com" not in page
    assert "jörg.müller@kunde.example" not in page  # letters of any script
    assert page.count("@example.test") == 2


def test_guests_get_numbers_above_every_account_one_per_address(rows: Rows) -> None:
    review = find(rows, "wp_comments", "comment_ID", "2")
    address = review["comment_author_email"] or ""

    assert address.startswith("customer-1000") and address.endswith("@example.test")
    assert review["comment_author"] == "Customer"
    assert (
        review["comment_author_IP"],
        review["comment_agent"],
        review["comment_author_url"],
    ) == ("", "", "")
    assert review["comment_content"] == f"Gut, Rückfragen an {address}"
    note = find(rows, "wp_comments", "comment_ID", "1")
    assert (note["comment_author"], note["comment_author_email"]) == (
        "WooCommerce",
        "woocommerce@de-linker.com",
    )


def test_stripe_ids_leave_the_order_notes(rows: Rows) -> None:
    note = find(rows, "wp_comments", "comment_ID", "3")["comment_content"]

    assert note == "Stripe charge complete (Charge ID: ). Payment Intent: "


def test_orders_lose_the_buyer_and_keep_the_order(rows: Rows) -> None:
    order = find(rows, "wp_wc_orders", "id", "13")
    assert order["billing_email"] == "customer-18@example.test"
    assert (
        order["ip_address"],
        order["user_agent"],
        order["customer_note"],
        order["transaction_id"],
    ) == ("", "", "", "")
    assert order["total_amount"] == "1234.00000000"

    address = find(rows, "wp_wc_order_addresses", "order_id", "13")
    columns = (
        "first_name",
        "last_name",
        "company",
        "address_1",
        "address_2",
        "city",
        "postcode",
        "country",
        "email",
        "phone",
    )
    assert {column: address[column] for column in columns} == {
        "first_name": "Customer",
        "last_name": "Example",
        "company": "Example Company",
        "address_1": "Musterstraße 1",
        "address_2": "",
        "city": "Musterstadt",
        "postcode": "12345",
        "country": "DE",
        "email": "customer-18@example.test",
        "phone": "+49 30 0000000",
    }
    hpos_meta = {
        row["meta_key"]: row["meta_value"] for row in rows["wp_wc_orders_meta"]
    }
    assert hpos_meta == {
        "_billing_address_index": "",
        "is_vat_exempt": "no",
        "tv_b2b_document_ledger_v2": "",
        "tv_b2b_order_vat_snapshot": "",
    }
    classic_meta = {
        row["meta_key"]: row["meta_value"]
        for row in rows["wp_postmeta"]
        if row["post_id"] == "13"
    }
    local_key = order_key("wc_order_AbCdEf1234567")
    assert classic_meta == {
        "_billing_email": "customer-18@example.test",
        "_billing_first_name": "Customer",
        "_customer_ip_address": "",
        "_order_key": local_key,
    }
    # Every copy of the order key is the same local key.
    operational = find(rows, "wp_wc_order_operational_data", "order_id", "13")
    assert operational["order_key"] == local_key
    post = find(rows, "wp_posts", "ID", "13")
    assert (post["post_password"], post["post_excerpt"]) == (local_key, "")
    lookup = find(rows, "wp_wc_customer_lookup", "user_id", "18")
    assert (
        lookup["username"],
        lookup["first_name"],
        lookup["email"],
        lookup["city"],
        lookup["postcode"],
        lookup["billing_phone"],
    ) == (
        "customer-18",
        "Customer",
        "customer-18@example.test",
        "Musterstadt",
        "12345",
        "+49 30 0000000",
    )


def test_snippets_that_do_not_run_lose_their_code(rows: Rows) -> None:
    code = {row["id"]: row["code"] for row in rows["wp_snippets"]}

    assert code["27"] == "add_filter( 'linker_year', static fn() => gmdate( 'Y' ) );"
    assert code["224"] == ""  # off: held an NVIDIA key
    assert code["276"] == ""  # ran once: held the engine token


def test_a_credential_written_into_running_code_is_emptied() -> None:
    dump = (
        "CREATE TABLE `wp_snippets` (\n  `id` bigint,\n  `code` longtext,\n"
        "  `active` tinyint\n) ENGINE=InnoDB;\n"
        "INSERT INTO `wp_snippets` VALUES\n"
        "(1,'define( \\'SMTP_PASS\\', \\'hunter2!\\' ); $key = \\'billing_email\\';"
        " $args = array( \\'api_key\\' => \\'abc123\\', \\'mode\\' => \\'yes\\' );',1);\n"
    )
    anonymizer = Anonymizer([])

    out = "".join(anonymizer.run(iter(dump.splitlines(keepends=True))))

    assert tables(out.splitlines(keepends=True))["wp_snippets"][0]["code"] == (
        "define( 'SMTP_PASS', '' ); $key = 'billing_email';"
        " $args = array( 'api_key' => '', 'mode' => 'yes' );"
    )


def test_submissions_jobs_and_sessions_keep_their_tables_but_no_rows(
    anonymized: tuple[list[str], Anonymizer], rows: Rows
) -> None:
    text = "".join(anonymized[0])
    report = anonymized[1].report

    for table in (
        "wp_tv_b2b_contact_request",
        "wp_woocommerce_sessions",
        "wp_actionscheduler_actions",
    ):
        assert f"CREATE TABLE `{table}`" in text
        assert table not in rows
    assert report.rows_dropped["wp_actionscheduler_actions"] == 2
    assert "Gen3rated!Pass" not in text


def test_only_keys_named_for_a_credential_are_emptied() -> None:
    rules = (
        'a:2:{s:32:"(.?.+?)/lost-password(/(.*))?/?$";'
        's:56:"index.php?pagename=$matches[1]&lost-password=$matches[3]";'
        's:10:"(.?.+?)/?$";s:30:"index.php?pagename=$matches[1]";}'
    )
    settings = (
        'a:5:{s:22:"lost_password_endpoint";s:13:"lost-password";'
        's:9:"smtp_pass";s:7:"hunter2";s:10:"max_tokens";s:8:"80000000";'
        's:22:"engine_token_encrypted";s:12:"b64:abcdefgh";s:11:"use_api_key";s:3:"yes";}'
    )
    # Both are valid serialized arrays, so the rules really look inside them.
    members(rules)
    members(settings)
    dump = (
        "CREATE TABLE `wp_options` (\n  `option_id` bigint,\n  `option_name` varchar(191),\n"
        "  `option_value` longtext,\n  `autoload` varchar(20)\n) ENGINE=InnoDB;\n"
        "INSERT INTO `wp_options` VALUES\n"
        f"(1,'rewrite_rules','{rules}','on'),\n"
        f"(2,'mail_settings','{settings}','off');\n"
    )
    anonymizer = Anonymizer([])

    out = "".join(anonymizer.run(iter(dump.splitlines(keepends=True))))

    values = {
        row["option_name"]: row["option_value"]
        for row in tables(out.splitlines(keepends=True))["wp_options"]
    }
    assert values["rewrite_rules"] == rules
    stored = members(values["mail_settings"] or "")
    assert {key: stored[key] for key in stored if key is not None} == {
        "lost_password_endpoint": "lost-password",
        "smtp_pass": "",  # whatever its length
        "max_tokens": "80000000",
        "engine_token_encrypted": "",
        "use_api_key": "yes",  # a setting, not a credential
    }
    assert dict(anonymizer.report.credentials_by_key) == {
        "smtp_pass": 1,
        "engine_token_encrypted": 1,
    }


def test_the_result_passes_the_check_that_the_fixture_fails(
    anonymized: tuple[list[str], Anonymizer],
) -> None:
    before = scan.scan_lines(fixture_lines(), STAFF)
    after = scan.scan_lines(anonymized[0], STAFF)

    assert not before.clean
    assert before.password_hashes["$wp$"] == 3
    assert before.password_hashes["$generic$"] == 3
    assert before.application_passwords == 1
    assert {
        "shape",
        "api_key",
        "token",
        "user_pass",
        "test_secret_key",
        "webhook_secret",
    } <= set(before.secrets)
    assert before.payment_ids == 3
    assert before.unexpected_domains["kunde.example"] > 0
    assert after.clean, after.as_dict()
    assert after.emails["staff account"] >= 2
    assert after.emails["de-linker.com"] >= 2


def test_two_runs_over_the_same_dump_write_the_same_bytes() -> None:
    first = list(
        Anonymizer(accounts_from_dump(iter(fixture_lines()))).run(iter(fixture_lines()))
    )
    second = list(
        Anonymizer(accounts_from_dump(iter(fixture_lines()))).run(iter(fixture_lines()))
    )

    assert first == second


def test_public_admission_receipts_are_dropped_without_replacing_site_settings() -> (
    None
):
    dump = (
        "CREATE TABLE `wp_options` (\n  `option_id` bigint,\n  `option_name` varchar(191),\n"
        "  `option_value` longtext,\n  `autoload` varchar(20)\n) ENGINE=InnoDB;\n"
        "INSERT INTO `wp_options` VALUES\n"
        "(1,'linker_public_admission_ledger','private-pseudonymous-receipts','off'),\n"
        "(2,'blogname','Linker','on');\n"
    )
    out = "".join(Anonymizer([]).run(iter(dump.splitlines(keepends=True))))
    names = {
        row["option_name"]
        for row in tables(out.splitlines(keepends=True))["wp_options"]
    }
    assert "linker_public_admission_ledger" not in names
    assert "blogname" in names
    assert "private-pseudonymous-receipts" not in out


def test_private_tool_answers_and_encoded_pdfs_never_enter_snapshots() -> None:
    dump = (
        "CREATE TABLE `wp_posts` (\n  `ID` bigint,\n  `post_type` varchar(20),\n"
        "  `post_content` longtext,\n  `post_password` varchar(255)\n) ENGINE=InnoDB;\n"
        "INSERT INTO `wp_posts` VALUES\n"
        "(1,'linker_tool_reply','cHJpdmF0ZS1jdXN0b21lci1QREY=',''),\n"
        "(2,'page','Published page','');\n"
        "CREATE TABLE `wp_postmeta` (\n  `meta_id` bigint,\n  `post_id` bigint,\n"
        "  `meta_key` varchar(255),\n  `meta_value` longtext\n) ENGINE=InnoDB;\n"
        "INSERT INTO `wp_postmeta` VALUES\n"
        "(1,1,'_linker_binding','private-binding'),\n"
        "(2,1,'_linker_recipient','private-recipient'),\n"
        "(3,1,'_linker_expires','123456'),\n"
        "(4,2,'public_field','Published meta');\n"
    )
    out = "".join(Anonymizer([]).run(iter(dump.splitlines(keepends=True))))
    assert "cHJpdmF0ZS1jdXN0b21lci1QREY=" not in out
    assert "private-binding" not in out
    assert "private-recipient" not in out
    assert "123456" not in out
    assert "Published page" in out
    assert "Published meta" in out
