"""Pseudonymizing the live database dump before any of it is written to disk.

Rules (docs/specs/6-live-pull.md, "anonymize"; what the live tables hold was
read from a dump stream on 2026-10-09 without storing it):

- Accounts. A staff account (role administrator or shop_manager) keeps its
  login and e-mail address; its password becomes a local value that is no
  hash. Every other account becomes customer-<ID>: login, nicename, display
  name, e-mail customer-<ID>@example.test, password and activation key empty,
  billing/shipping/company fields placeholders, every other user meta value
  emptied unless it is known to be a setting. Application passwords and
  session tokens are dropped for everyone.
- E-mail addresses anywhere else (orders, comments, options, scheduled
  actions, content) are replaced with the address of their account, or
  customer-<n>@example.test from GUEST_FIRST up. Kept: staff accounts,
  example.test, and the company's own mailboxes (COMPANY_DOMAINS), which the
  site publishes on its pages.
- Orders: addresses, phone numbers, IP addresses, user agents, notes and
  payment-provider identifiers are replaced or emptied, by one rule for the
  order tables and the order meta of either storage (wp_postmeta for classic
  orders, wp_wc_orders_meta for HPOS); every copy of an order key becomes the
  same local key.
- Customer submissions of the old plugins (contact and project requests,
  project events and artifacts, the audit log, VAT declarations, AI
  conversations) and the session/rate-limit/API-key tables keep their schema
  but not their rows: no specification reads them (docs/specs/*), and they
  hold names, addresses, site coordinates and free text.
- Options: transients, options holding keys, tokens and licences, and the
  old plugins' mail and request logs are dropped.
- Scheduled jobs (Action Scheduler) keep their tables but not their rows:
  mail jobs hold recipients, bodies and a new account's plain-text password.
- Code Snippets: the code of every snippet that is not running is emptied;
  running snippets lose credentials written into their code.
- Everywhere: password hashes, recognisable credentials, Stripe object ids,
  and any value stored under a key named for a credential (api_key,
  user_pass, …) inside serialized or JSON data are removed.

Strings inside PHP-serialized values are changed with their lengths fixed
(phpserial), so WordPress can still unserialize them.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Iterator
from dataclasses import dataclass, field

from linker_pull import phpserial, sqldump
from linker_pull.sqldump import Insert, Table, Value

# The live site's table prefix (`wp config get table_prefix` over SSH, 2026-10-09).
TABLE_PREFIX = "wp_"
# Roles whose accounts are kept (docs/specs/6-live-pull.md).
STAFF_ROLES = frozenset({"administrator", "shop_manager"})
# Reserved for tests (RFC 6761 §6.2); never a real mailbox.
TEST_DOMAIN = "example.test"
# The company's own mail domains. de-linker.com is the site's; sales@ and
# chester@ are on its published pages. sales@sunriverinverter.com was in the
# site's footer (option dlk_pp_footer_en_a122ea69b7_before) and is the
# notification copy recipient in the live snippets (2026-10-09 dump).
COMPANY_DOMAINS = frozenset({"de-linker.com", "sunriverinverter.com"})
# Pseudonyms for addresses without an account start here, above every user ID
# on live (36 on 2026-10-09), so customer-<n> never names two people.
GUEST_FIRST = 100001

# Placeholder values. A field that was empty stays empty.
FIRST_NAME = "Customer"
COMPANY = "Example Company"
STREET = "Musterstraße 1"
CITY = "Musterstadt"
POSTCODE = "12345"
PHONE = "+49 30 0000000"
VAT_ID = "DE000000000"

# An address; local part and domain may hold letters of any script (jörg@müller.de).
EMAIL = re.compile(
    r"(?<![\w.%+-])[\w.%+-]+@(?:[^\W_](?:[\w-]*[^\W_])?\.)+([^\W\d_]{2,63})(?![\w-])"
)
# "logo@2x.png" is a file name, not an address.
FILE_SUFFIXES = frozenset(
    "png jpg jpeg gif webp svg avif ico pdf js mjs css map json xml txt html htm php "
    "mp4 webm mov woff woff2 ttf otf zip gz".split()
)
# Password hashes WordPress writes: phpass ($P$), bcrypt behind $wp$ (6.8+),
# plain bcrypt, BLAKE2b behind $generic$ (application passwords, reset keys)
# and argon2 (wp-includes/pluggable.php, wp_hash_password()/wp_fast_hash()).
HASH = re.compile(
    r"\$(?:P|H)\$[./0-9A-Za-z\\]{31,}|\$wp\$2[aby]\$[./0-9A-Za-z$\\]+|\$2[aby]\$\d\d\$[./0-9A-Za-z\\]{53,}|\$generic\$[0-9a-f]+|\$argon2(?:id|i|d)\$[^\s'\"]+"
)
# Credentials with a recognisable shape: those the live data held on 2026-10-09
# (Stripe keys and webhook secret in woocommerce_stripe_settings, JWTs in
# hostinger_ai_assistant_mcp_jwt_token_registry) and those of the services this
# project uses (DeepSeek, aihubmix, Apify; AGENTS.md §4, §6). The minimum
# lengths sit at or below the shortest real key, measured without printing any:
# Stripe keys have 99 characters after their prefix (the live option and
# ~/.config/terravolt-builder/stripe-de.json), the live webhook secret 32,
# DeepSeek keys 32 after "sk-" (aihubmix 48), Apify tokens 36 after
# "apify_api_". Shorter "sk-…" runs in the live posts (22–25 characters) are
# words, not keys.
SECRET = re.compile(
    r"\b(?:sk|rk|pk)_(?:live|test)_[0-9A-Za-z]{24,}"
    r"|\bwhsec_[0-9A-Za-z]{32,}"
    r"|\bsk-[0-9A-Za-z]{32,}"
    r"|\bapify_api_[0-9A-Za-z]{36,}"
    r"|\bnvapi-[\w-]{32,}"  # NVIDIA API key (live snippet 224 held one of 70 characters)
    r"|\beyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[^-]*-----END [A-Z ]*PRIVATE KEY-----"
)
# Stripe object ids: the live order notes held pi_, ch_, py_ and re_ ids of 24
# characters after the prefix and the order meta cus_, pm_ and src_ ids; a
# wp_comments row held a refund's pyr_ id (Spec review round 2, 2026-10-09
# snapshot). seti_ (setup intents) and tok_ (card tokens) are the remaining
# payment objects WooCommerce's Stripe extension records.
PAYMENT_ID = re.compile(r"\b(?:pyr|seti|tok|pi|ch|py|re|cus|pm|src)_[0-9A-Za-z]{14,}\b")
# A value worth decoding: it may hold an address, a hash, a credential or a payment id.
SENSITIVE = re.compile(
    r"@|\$(?:P|H|wp|generic|2[aby]|argon2)|_live_|_test_|whsec_|sk-|apify_api_|nvapi-|eyJ"
    r"|PRIVATE KEY|\b(?:pyr|seti|tok|pi|ch|py|re|cus|pm|src)_"
)

# Options dropped whole: the specification's patterns (*_api_key, *_secret,
# *token*, woocommerce_stripe_*) and, from the live option names of
# 2026-10-09, the LiveCanvas API key (lc_apikey), licence keys and the
# licence server's cached reply (edd_sl_*), the cached Stripe account
# (wcstripe_cache_*), the mail-server password, the recovery-mode keys and
# WooCommerce's share key.
SECRET_OPTION = re.compile(
    r"_api_key$|_secret|token|^woocommerce_stripe_|apikey|licen[cs]e|^edd_sl_|^wcstripe_cache_|^mailserver_pass$|^recovery_keys$|^woocommerce_share_key$"
)
TRANSIENT_OPTION = re.compile(r"^_(?:site_)?transient_")
# Logs the old plugins kept in options: mail logs and intercepts with
# recipients and bodies (tv_089_mail_log, tv_b2b_089_mail_intercept_*,
# tv_b2b_089_mail_wpmail_*, linker104_mail_*), request logs with contact
# details (tv_b2b_project_request_log, tv_b2b_utility_quote_log) and the demo
# account's creation result (dlk_demo_partner_account_result_*), 2026-10-09.
LOG_OPTION = re.compile(
    r"_mail_log$|_mail_intercept_|_mail_wpmail_|^linker\d+_mail_|_request_log$|_quote_log$|_account_result_"
)
# Inside an option's array or JSON, a value stored under a key whose name ends
# in one of these words is a credential (api_key, webhook_secret, smtp_pass,
# engine_token_encrypted). A key that only contains such a word is not:
# lost_password_endpoint, or the rewrite rule "(.?.+?)/lost-password(/(.*))?/?$"
# of the 2026-10-09 rewrite_rules option.
SECRET_KEY = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|apikey|secret(?:[_-]?key)?|(?:access[_-]|refresh[_-])?token"
    r"|passw(?:or)?d|pass|licen[cs]e[_-]?key|private[_-]?key)(?:[_-]encrypted)?$",
    re.IGNORECASE,
)
# Whether an option's value can hold such a key at all (a cheap test first).
SECRET_KEY_HINT = re.compile(r"key|secret|token|pass|licen", re.IGNORECASE)
# What a setting stored under such a key holds instead of a credential: nothing,
# a number or a yes/no word (seopress_instant_indexing_bing_api_key is "" when
# unset, use_api_key is "yes"). Everything else under such a key is emptied.
SETTING_VALUE = re.compile(r"|\d+|yes|no|on|off|true|false", re.IGNORECASE)
JSON_MEMBER = re.compile(r'"([^"\\]*)"(\s*:\s*)"((?:[^"\\]|\\.)*)"')
# A credential written into PHP code: define( 'NAME', '…' ), $name = '…' or
# 'name' => '…', where the name ends in a credential word (SECRET_KEY).
CODE_LITERAL = re.compile(
    r"""(?P<head>define\s*\(\s*(?P<q1>['"])(?P<n1>\w+)(?P=q1)\s*,\s*"""
    r"""|\$(?P<n2>\w+)\s*=\s*"""
    r"""|(?P<q3>['"])(?P<n3>\w+)(?P=q3)\s*=>\s*)"""
    r"""(?P<q>['"])(?P<value>[^'"\\]*)(?P=q)"""
)

# Tables whose rows are dropped (see the module docstring).
DROPPED_TABLES = frozenset(
    TABLE_PREFIX + name
    for name in (
        "tv_b2b_contact_request",
        "tv_b2b_project_request",
        "tv_b2b_project_event",
        "tv_b2b_project_artifact",
        "tv_b2b_audit_log",
        "tv_b2b_vat_declarations",
        "linker_ai_conversation",
        "seopress_ai_conversations",
        "woocommerce_sessions",
        "wc_rate_limits",
        "woocommerce_api_keys",
        "woocommerce_payment_tokens",
        "woocommerce_payment_tokenmeta",
        # Scheduled jobs and their log: mail jobs with recipients and bodies,
        # and WooCommerce's new-account mail with the plain-text password
        # (2026-10-09). WooCommerce schedules its recurring jobs again by itself.
        "actionscheduler_actions",
        "actionscheduler_logs",
        "actionscheduler_claims",
    )
)

# User meta dropped for every account: credentials and login sessions (with
# their IP addresses), the IP-derived events location, the Stripe customer.
DROPPED_USERMETA = frozenset(
    {
        "_application_passwords",
        "session_tokens",
        "community-events-location",
        TABLE_PREFIX + "_stripe_customer_id",
    }
)
# User meta of a customer that is a setting, not about the person (the live
# keys of 2026-10-09); every other value of a customer is emptied.
SETTING_USERMETA = frozenset(
    {
        TABLE_PREFIX + "capabilities",
        TABLE_PREFIX + "user_level",
        TABLE_PREFIX + "user-settings",
        TABLE_PREFIX + "user-settings-time",
        TABLE_PREFIX + "dashboard_quick_press_last_post_id",
        "locale",
        "rich_editing",
        "syntax_highlighting",
        "comment_shortcuts",
        "admin_color",
        "use_ssl",
        "show_admin_bar_front",
        "show_welcome_panel",
        "dismissed_wp_pointers",
        "default_password_nag",
        "infinite_scrolling",
        "acf_user_settings",
        "seopress_redirections_view",
        "seopress_schemas_view",
        "paying_customer",
        "wc_last_active",
        "last_update",
        "_woocommerce_persistent_cart_1",
        "billing_country",
        "billing_state",
        "shipping_country",
        "shipping_state",
        "shipping_method",
        "_linker_i18n_locale",
        "tv_b2b_locale",
        "tv_b2b_status",
        "tv_b2b_status_changed_at",
        "tv_b2b_group",
        "tv_b2b_active_project_ref",
        "tv_b2b_recently_bound_project_ref",
        "tv_b2b_dismissed_notifications",
        "tv_b2b_vies_status",
        "tv_b2b_vies_valid",
        "tv_b2b_vies_checked_at",
        "tv_b2b_vies_last_attempt_at",
        "tv_b2b_vies_generation",
        "tv_b2b_vies_last_error",
        "tv_credit_limit_cents",
        "tv_credit_used_cents",
        "tv_payment_due_days",
        "tv_payment_terms",
        "tv_payment_terms_code",
        "linker_ai_conversations_imported",
    }
)
SETTING_USERMETA_PREFIXES = (
    "closedpostboxes_",
    "metaboxhidden_",
    "manageedit-",
    "meta-box-order_",
)
# Order meta about the buyer rather than the order. WooCommerce writes the same
# keys into wp_postmeta (classic orders) and wp_wc_orders_meta (HPOS); the keys
# are the live ones of 2026-10-09 and WooCommerce's classic order fields.
EMPTIED_ORDER_META = frozenset(
    {
        "_billing_address_index",
        "_shipping_address_index",
        "_customer_ip_address",
        "_customer_user_agent",
        "_transaction_id",
        "_stripe_customer_id",
        "_stripe_intent_id",
        "_stripe_source_id",
        "_wc_order_attribution_user_agent",
        "_wc_order_attribution_session_entry",
        "_wc_order_attribution_referrer",
        # Native public-admission retry links identify an individual order's
        # request and subject; they must not survive a live-to-local pull (#520).
        "_linker_public_request",
        "_linker_public_input",
        "_linker_public_subject",
        "tv_b2b_company_snapshot",
        "tv_b2b_document_ledger_v2",  # the buyer block of every proforma
        "tv_b2b_order_vat_snapshot",  # VIES name and address
        "tv_b2b_vat_id_submitted",
        "tv_b2b_vies_request_identifier",
        "tv_b2b_project_title",
        "tv_b2b_freight_confirmation_note",
        "tv_b2b_proforma_internal_note",
    }
)
ORDER_POST_TYPES = frozenset(
    {"shop_order", "shop_order_placehold", "shop_order_refund"}
)


@dataclass(frozen=True)
class Account:
    """A WordPress user as the rules need it."""

    id: int
    login: str
    email: str
    roles: frozenset[str]

    @property
    def staff(self) -> bool:
        return bool(self.roles & STAFF_ROLES)


def local_password(user_pass: str) -> str:
    """A staff account's local password field: no hash of any password, so no password logs in.

    Derived from the live value, so two snapshots of an unchanged account agree.
    """
    return "local-" + hashlib.sha256(user_pass.encode()).hexdigest()[:32]


def order_key(live_key: str) -> str:
    """An order key in WooCommerce's form (wc_order_ + 13 characters) that opens no live order."""
    return "wc_order_" + hashlib.sha256(live_key.encode()).hexdigest()[:13]


class Emails:
    """Which address replaces an address."""

    def __init__(self, accounts: Iterable[Account]) -> None:
        self.staff: set[str] = set()
        self.customers: dict[str, int] = {}
        for account in accounts:
            address = account.email.lower()
            if account.staff:
                self.staff.add(address)
            elif address:
                self.customers[address] = account.id
        self.guests: dict[str, int] = {}
        self.kept: Counter[str] = Counter()
        self.replaced = 0

    def keeps(self, address: str) -> bool:
        """Whether `address` stays as it is (no counting, no pseudonym assigned)."""
        key = address.lower()
        return key not in self.customers and kept_as(key, self.staff) is not None

    def replace(self, address: str) -> str:
        key = address.lower()
        if key in self.customers:
            self.replaced += 1
            return customer_email(self.customers[key])
        reason = kept_as(key, self.staff)
        if reason is not None:
            self.kept[reason] += 1
            return address
        number = self.guests.setdefault(key, GUEST_FIRST + len(self.guests))
        self.replaced += 1
        return customer_email(number)

    def replace_all(self, text: str) -> str:
        if "@" not in text:
            return text
        return EMAIL.sub(self._replace_match, text)

    def _replace_match(self, found: re.Match[str]) -> str:
        if found.group(1).lower() in FILE_SUFFIXES:
            return found.group()
        return self.replace(found.group())


def kept_as(address: str, staff: Collection[str]) -> str | None:
    """Why an address (lower case) stays: "staff account", the test domain or a company domain; None if it does not."""
    domain = address.rpartition("@")[2]
    if address in staff:
        return "staff account"
    if domain == TEST_DOMAIN or domain in COMPANY_DOMAINS:
        return domain
    return None


def customer_email(number: int) -> str:
    return f"customer-{number}@{TEST_DOMAIN}"


@dataclass
class Report:
    """What the anonymizer changed: counts and names, never values."""

    rows_dropped: Counter[str] = field(default_factory=Counter)
    columns_changed: Counter[str] = field(default_factory=Counter)
    hashes_removed: int = 0
    secrets_removed: int = 0
    payment_ids_removed: int = 0
    credentials_by_key: Counter[str] = field(default_factory=Counter)
    emptied_usermeta: Counter[str] = field(default_factory=Counter)

    def as_dict(self, emails: Emails) -> dict[str, object]:
        return {
            "rows_dropped": dict(sorted(self.rows_dropped.items())),
            "columns_changed": dict(sorted(self.columns_changed.items())),
            "emails": {
                "replaced": emails.replaced,
                "guests": len(emails.guests),
                "kept": dict(sorted(emails.kept.items())),
            },
            "hashes_removed": self.hashes_removed,
            "secrets_removed": self.secrets_removed,
            "payment_ids_removed": self.payment_ids_removed,
            "credentials_emptied_by_key": dict(sorted(self.credentials_by_key.items())),
            "customer_usermeta_emptied": dict(sorted(self.emptied_usermeta.items())),
        }


Row = list[Value]
Rule = Callable[[Table, Row], bool]


class Anonymizer:
    """Runs a dump through the rules."""

    def __init__(self, accounts: Iterable[Account]) -> None:
        accounts = list(accounts)
        self.accounts = {account.id: account for account in accounts}
        self.emails = Emails(accounts)
        self.report = Report()
        self.rules: dict[str, Rule] = {
            TABLE_PREFIX + "users": self._users,
            TABLE_PREFIX + "usermeta": self._usermeta,
            TABLE_PREFIX + "options": self._options,
            TABLE_PREFIX + "posts": self._posts,
            TABLE_PREFIX + "postmeta": self._order_meta,
            TABLE_PREFIX + "comments": self._comments,
            TABLE_PREFIX + "wc_orders": self._orders,
            TABLE_PREFIX + "wc_order_addresses": self._order_addresses,
            TABLE_PREFIX + "wc_orders_meta": self._order_meta,
            TABLE_PREFIX + "wc_order_operational_data": self._order_operational_data,
            TABLE_PREFIX + "wc_customer_lookup": self._customer_lookup,
            TABLE_PREFIX + "wc_download_log": self._download_log,
            TABLE_PREFIX + "wc_webhooks": self._webhooks,
            TABLE_PREFIX + "snippets": self._snippets,
            TABLE_PREFIX
            + "woocommerce_downloadable_product_permissions": self._download_permissions,
        }

    def process(self, items: Iterator[sqldump.Line]) -> Iterator[sqldump.Line]:
        """The dump's parsed lines with every INSERT's rows pseudonymized."""
        for item in items:
            if isinstance(item, Insert):
                self._insert(item)
            yield item

    def run(self, lines: Iterator[str]) -> Iterator[str]:
        """The dump's text, pseudonymized."""
        return sqldump.write(self.process(sqldump.read(lines)))

    def _insert(self, insert: Insert) -> None:
        table = insert.table
        if table.name in DROPPED_TABLES:
            self.report.rows_dropped[table.name] += len(insert.rows)
            insert.rows = []
            return
        rule = self.rules.get(table.name)
        kept: list[Row] = []
        for row in insert.rows:
            if rule is not None and not rule(table, row):
                self.report.rows_dropped[table.name] += 1
                continue
            for index, value in enumerate(row):
                if value.is_string and (
                    SENSITIVE.search(value.raw)
                    # A credential may only show by the key it is stored under.
                    or SECRET_KEY_HINT.search(value.raw)
                ):
                    text = value.text
                    assert text is not None
                    new = self.scrub(text)
                    if new != text:
                        row[index] = Value.of(new)
            kept.append(row)
        insert.rows = kept

    # -- text -------------------------------------------------------------

    def scrub(self, text: str) -> str:
        """`text` without customers' addresses, hashes, credentials and payment ids; serialized data stays valid."""
        if phpserial.looks_serialized(text):

            def member(inner: str, key: str | None) -> str:
                if key is not None and self._is_credential(key, inner):
                    self.report.credentials_by_key[key] += 1
                    return ""
                return self.scrub(inner)

            rewritten = phpserial.rewrite(text, member)
            if rewritten is not None:
                return rewritten
        if text[:1] in ("{", "["):
            text = JSON_MEMBER.sub(self._json_member, text)
        text = self.emails.replace_all(text)
        text, hashes = HASH.subn("", text)
        text, secrets = SECRET.subn("", text)
        text, payments = PAYMENT_ID.subn("", text)
        self.report.hashes_removed += hashes
        self.report.secrets_removed += secrets
        self.report.payment_ids_removed += payments
        return text

    def _json_member(self, found: re.Match[str]) -> str:
        key, colon, value = found.groups()
        if self._is_credential(key, value):
            self.report.credentials_by_key[key] += 1
            return f'"{key}"{colon}""'
        return found.group()

    @staticmethod
    def _is_credential(key: str, value: str) -> bool:
        return bool(SECRET_KEY.search(key)) and not SETTING_VALUE.fullmatch(
            value.strip()
        )

    # -- per-table rules (True keeps the row) ------------------------------

    def _set(self, table: Table, row: Row, column: str, text: str | None) -> None:
        index = table.index(column)
        if row[index].text != text:
            row[index] = Value.of(text)
            self.report.columns_changed[f"{table.name}.{column}"] += 1

    def _placeholder(self, table: Table, row: Row, column: str, text: str) -> None:
        """Replace a non-empty value; an empty one stays empty."""
        if row[table.index(column)].text:
            self._set(table, row, column, text)

    def _account(self, table: Table, row: Row, column: str) -> Account | None:
        value = row[table.index(column)].text
        return self.accounts.get(int(value)) if value and value.isdigit() else None

    def _users(self, table: Table, row: Row) -> bool:
        account = self._account(table, row, "ID")
        user_pass = row[table.index("user_pass")].text or ""
        self._set(table, row, "user_activation_key", "")
        if account is not None and account.staff:
            self._set(table, row, "user_pass", local_password(user_pass))
            return True
        number = int(row[table.index("ID")].text or 0)
        self._set(table, row, "user_pass", "")
        self._set(table, row, "user_login", f"customer-{number}")
        self._set(table, row, "user_nicename", f"customer-{number}")
        self._set(table, row, "user_email", customer_email(number))
        self._set(table, row, "display_name", f"{FIRST_NAME} {number}")
        self._set(table, row, "user_url", "")
        return True

    def _usermeta(self, table: Table, row: Row) -> bool:
        key = row[table.index("meta_key")].text or ""
        if key in DROPPED_USERMETA:
            return False
        account = self._account(table, row, "user_id")
        if account is not None and account.staff:
            return True
        number = int(row[table.index("user_id")].text or 0)
        placeholder = customer_meta(key, number)
        if placeholder is not None:
            self._placeholder(table, row, "meta_value", placeholder)
        elif key not in SETTING_USERMETA and not key.startswith(
            SETTING_USERMETA_PREFIXES
        ):
            if row[table.index("meta_value")].text:
                self.report.emptied_usermeta[key] += 1
            self._set(table, row, "meta_value", "")
        return True

    def _options(self, table: Table, row: Row) -> bool:
        name = row[table.index("option_name")].text or ""
        return not (
            name == "linker_public_admission_ledger"
            or TRANSIENT_OPTION.search(name)
            or SECRET_OPTION.search(name)
            or LOG_OPTION.search(name)
        )

    def _posts(self, table: Table, row: Row) -> bool:
        if row[table.index("post_type")].text in ORDER_POST_TYPES:
            # A classic order keeps its order key in post_password and the
            # customer's note in its excerpt.
            live_key = row[table.index("post_password")].text
            if live_key:
                self._set(table, row, "post_password", order_key(live_key))
            self._set(table, row, "post_excerpt", "")
        else:
            self._set(table, row, "post_password", "")
        return True

    def _comments(self, table: Table, row: Row) -> bool:
        self._set(table, row, "comment_author_IP", "")
        self._set(table, row, "comment_agent", "")
        self._set(table, row, "comment_author_url", "")
        address = row[table.index("comment_author_email")].text or ""
        if address and not self.emails.keeps(address):
            self._set(table, row, "comment_author", FIRST_NAME)
        return True

    def _orders(self, table: Table, row: Row) -> bool:
        for column in ("ip_address", "user_agent", "customer_note", "transaction_id"):
            self._set(table, row, column, "")
        return True

    def _order_addresses(self, table: Table, row: Row) -> bool:
        for column, text in (
            ("first_name", FIRST_NAME),
            ("last_name", "Example"),
            ("company", COMPANY),
            ("address_1", STREET),
            ("city", CITY),
            ("postcode", POSTCODE),
            ("phone", PHONE),
        ):
            self._placeholder(table, row, column, text)
        self._set(table, row, "address_2", "")
        return True

    def _order_meta(self, table: Table, row: Row) -> bool:
        """The buyer's order meta, in wp_postmeta or wp_wc_orders_meta."""
        key = row[table.index("meta_key")].text or ""
        value = row[table.index("meta_value")].text
        if key in EMPTIED_ORDER_META:
            self._set(table, row, "meta_value", "")
        elif key == "_order_key" and value:
            self._set(table, row, "meta_value", order_key(value))
        elif key.startswith(("_billing_", "_shipping_")):
            placeholder = customer_meta(key[1:], None)
            if placeholder is not None:
                self._placeholder(table, row, "meta_value", placeholder)
        return True

    def _order_operational_data(self, table: Table, row: Row) -> bool:
        live_key = row[table.index("order_key")].text
        if live_key:
            self._set(table, row, "order_key", order_key(live_key))
        return True

    def _customer_lookup(self, table: Table, row: Row) -> bool:
        account = self._account(table, row, "user_id")
        if account is not None and account.staff:
            return True
        if account is not None:
            self._set(table, row, "username", f"customer-{account.id}")
        for column, text in (
            ("first_name", FIRST_NAME),
            ("last_name", "Example"),
            ("city", CITY),
            ("postcode", POSTCODE),
            ("billing_phone", PHONE),
            ("shipping_phone", PHONE),
        ):
            self._placeholder(table, row, column, text)
        return True

    def _download_log(self, table: Table, row: Row) -> bool:
        self._set(table, row, "user_ip_address", "")
        return True

    def _webhooks(self, table: Table, row: Row) -> bool:
        self._set(table, row, "secret", "")
        return True

    def _snippets(self, table: Table, row: Row) -> bool:
        """Code Snippets: the code of a snippet that is not running is emptied.

        On 2026-10-09 2 snippets ran (active 1); 570 had run once (-1) or were
        off (0), among them an NVIDIA API key (snippet 224) and the engine's
        token in clear (snippet 276). No specification reads their code, and
        the plugin stays off locally. Running snippets keep their code without
        credentials written into it.
        """
        if row[table.index("active")].text != "1":
            self._set(table, row, "code", "")
            return True
        code = row[table.index("code")].text or ""
        self._set(table, row, "code", CODE_LITERAL.sub(self._code_literal, code))
        return True

    def _code_literal(self, found: re.Match[str]) -> str:
        name = found.group("n1") or found.group("n2") or found.group("n3") or ""
        if self._is_credential(name, found.group("value")):
            self.report.credentials_by_key[name] += 1
            return found.group("head") + found.group("q") * 2
        return found.group()

    def _download_permissions(self, table: Table, row: Row) -> bool:
        live_key = row[table.index("order_key")].text
        if live_key:
            self._set(table, row, "order_key", order_key(live_key))
        return True


def customer_meta(key: str, number: int | None) -> str | None:
    """The placeholder for a customer's billing/shipping/company field, None if `key` is none of them."""
    suffix = f" {number}" if number is not None else ""
    for prefix in ("billing_", "shipping_"):
        if key.startswith(prefix):
            field_name = key.removeprefix(prefix)
            break
    else:
        field_name = key
    placeholders = {
        "first_name": FIRST_NAME,
        "last_name": str(number) if number is not None else "Example",
        "nickname": f"customer-{number}" if number is not None else None,
        "company": COMPANY + suffix,
        "tv_company_name": COMPANY + suffix,
        "address_1": STREET,
        "address_2": "",
        "city": CITY,
        "postcode": POSTCODE,
        "phone": PHONE,
        "tv_phone": PHONE,
        "email": customer_email(number) if number is not None else None,
        "tv_vat_id": VAT_ID,
        "tv_b2b_vies_vat_id": VAT_ID,
    }
    if field_name not in placeholders:
        return None
    return placeholders[field_name]


def accounts_from_dump(lines: Iterator[str]) -> list[Account]:
    """The accounts of a dump: users and the roles in their capabilities meta."""
    users: dict[int, tuple[str, str]] = {}
    roles: dict[int, frozenset[str]] = {}
    for item in sqldump.read(lines):
        if not isinstance(item, Insert):
            continue
        table = item.table
        if table.name == TABLE_PREFIX + "users":
            for row in item.rows:
                users[int(row[table.index("ID")].text or 0)] = (
                    row[table.index("user_login")].text or "",
                    row[table.index("user_email")].text or "",
                )
        elif table.name == TABLE_PREFIX + "usermeta":
            for row in item.rows:
                if row[table.index("meta_key")].text == TABLE_PREFIX + "capabilities":
                    user_id = int(row[table.index("user_id")].text or 0)
                    roles[user_id] = capability_roles(
                        row[table.index("meta_value")].text or ""
                    )
    return [
        Account(user_id, login, email, roles.get(user_id, frozenset()))
        for user_id, (login, email) in sorted(users.items())
    ]


def capability_roles(serialized: str) -> frozenset[str]:
    """The roles granted in a serialized capabilities array, e.g. a:1:{s:8:"customer";b:1;}."""
    return frozenset(re.findall(r's:\d+:"([^"]+)";b:1;', serialized))
