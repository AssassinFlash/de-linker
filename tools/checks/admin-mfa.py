"""Native local administrator MFA acceptance; never accepts a remote target.

Run with tools/local's uv environment through `just admin-mfa <instance>`.
Only synthetic fixture users receive factors or application passwords. Response
bodies, cookies, passwords, TOTP seeds and recovery codes never enter the report.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.cookiejar
import json
import re
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from linker_local.cli import require_php
from linker_local.downloads import fetch
from linker_local.instance import home
from linker_local.registry import Registry
from linker_local.wpcli import WpCli

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests/e2e/fixtures/admin-mfa.php"
# Official stable package and independently verified WP-CLI file checksums,
# captured for #565; the archive remains in the native shared download cache.
VERSION = "0.17.0"
ARCHIVE_SHA256 = "4d1b0f8e5d82e24876c2b4e86f119122e28a8dbaf76dfde495173226c3356f37"
LANGUAGE_SHA256 = "8d5e133f7ef0697f6f8c48a240ff8a078702bda97bc39eac5fc98fe6da9c318c"


@dataclass
class Form:
    attrs: dict[str, str | None]
    fields: dict[str, str] = field(default_factory=dict)


class Forms(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.forms: list[Form] = []
        self.current: Form | None = None
        self.links: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "form":
            self.current = Form(values)
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None and values.get("name"):
            self.current.fields[str(values["name"])] = values.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.current = None

    def having(self, name: str) -> Form:
        matches = [form for form in self.forms if name in form.fields]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one native form containing {name}.")
        return matches[0]


class LocalRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin: str) -> None:
        self.origin = urllib.parse.urlsplit(origin).netloc

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if urllib.parse.urlsplit(newurl).netloc != self.origin:
            raise RuntimeError("Refused a redirect outside this local instance.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Browser:
    """HTTP form transport, separate from the Computer Use visual acceptance."""

    def __init__(self, base: str) -> None:
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar), LocalRedirect(base)
        )
        self.url = base
        self.html = ""
        self.status = 0

    def request(
        self,
        path: str,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        json_data: dict[str, str] | None = None,
    ) -> None:
        url = urllib.parse.urljoin(self.base, path)
        if urllib.parse.urlsplit(url).netloc != urllib.parse.urlsplit(self.base).netloc:
            raise RuntimeError("Only the registered local origin is permitted.")
        payload = urllib.parse.urlencode(data).encode() if data is not None else None
        if json_data is not None:
            if data is not None:
                raise RuntimeError("Choose a single native request encoding.")
            payload = json.dumps(json_data).encode()
            headers = {**(headers or {}), "Content-Type": "application/json"}
        request = urllib.request.Request(url, data=payload, headers=headers or {})
        try:
            response = self.opener.open(request, timeout=45)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.status = response.code
            self.url = response.url
            self.html = response.read().decode("utf-8")

    def submit(self, form: Form, extra: dict[str, str]) -> None:
        action = urllib.parse.urljoin(self.url, form.attrs.get("action") or self.url)
        self.request(action, {**form.fields, **extra})

    def signed_in(self) -> bool:
        return any(
            cookie.name.startswith("wordpress_logged_in_") for cookie in self.jar
        )

    def challenged(self) -> bool:
        return any("wp-auth-nonce" in form.fields for form in Forms(self.html).forms)


def prepare(wp: WpCli) -> dict[str, str]:
    archive = fetch(f"https://downloads.wordpress.org/plugin/two-factor.{VERSION}.zip")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise RuntimeError(
            "Official dependency archive differs from the reviewed package."
        )
    installed = json.loads(wp.run("plugin", "list", "--format=json"))
    current = next((row for row in installed if row["name"] == "two-factor"), None)
    if current is None:
        wp.run("plugin", "install", str(archive), "--activate")
    elif current["version"] != VERSION:
        raise RuntimeError(
            "Installed Two-Factor version differs; review it before replacing."
        )
    elif current["status"] != "active":
        wp.run("plugin", "activate", "two-factor")
    # Same native translation-download mechanism as linker-local's Woo packs.
    language = fetch(
        f"https://downloads.wordpress.org/translation/plugin/two-factor/{VERSION}/de_DE_formal.zip",
        name=f"two-factor-{VERSION}-de_DE_formal.zip",
    )
    if hashlib.sha256(language.read_bytes()).hexdigest() != LANGUAGE_SHA256:
        raise RuntimeError(
            "Official language archive changed; review it before loading."
        )
    with zipfile.ZipFile(language) as package:
        if set(package.namelist()) != {
            "two-factor-de_DE_formal.po",
            "two-factor-de_DE_formal.mo",
            "two-factor-de_DE_formal.l10n.php",
        }:
            raise RuntimeError("Unexpected official translation archive member.")
        target = wp.instance.wp_content / "languages/plugins"
        target.mkdir(parents=True, exist_ok=True)
        package.extractall(target)
    # Merge one observed missing vendor notice using native gettext catalogs.
    # Nothing is copied into or patched in third-party plugin source.
    supplement = REPO / "tools/admin-mfa/two-factor-de_DE_formal.po"
    catalog = target / "two-factor-de_DE_formal.po"
    with tempfile.TemporaryDirectory(prefix="linker-mfa-translation-") as temporary:
        merged = Path(temporary) / catalog.name
        subprocess.run(
            ["msgcat", "--use-first", str(supplement), str(catalog), "-o", str(merged)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["msgfmt", "--check", "-o", str(catalog.with_suffix(".mo")), str(merged)],
            check=True,
            capture_output=True,
            text=True,
        )
        catalog.write_bytes(merged.read_bytes())
    wp.run("i18n", "make-php", str(catalog), str(target))
    # Match the native language upgrader: invalidate only its directory index,
    # otherwise Redis can retain the pre-install list for an hour.
    wp.run(
        "eval", "wp_cache_delete(md5(WP_LANG_DIR . '/plugins/'), 'translation_files');"
    )
    return {
        "archive_sha256": digest,
        "de_pack_sha256": hashlib.sha256(language.read_bytes()).hexdigest(),
        "de_supplement_sha256": hashlib.sha256(supplement.read_bytes()).hexdigest(),
    }


def verify_dependency(wp: WpCli) -> dict[str, str]:
    """Every run verifies the actual dependency before any fixture can write."""
    current = json.loads(
        wp.run(
            "plugin",
            "get",
            "two-factor",
            "--fields=name,status,version",
            "--format=json",
        )
    )
    if not isinstance(current, dict):
        raise RuntimeError("Native Two-Factor dependency metadata is invalid.")
    version = current.get("version")
    status = current.get("status")
    if version != VERSION or status != "active":
        raise RuntimeError(
            f"Require Two-Factor {VERSION} active; found {version} ({status})."
        )
    verified = wp.run("plugin", "verify-checksums", "two-factor", "--strict")
    return {"version": version, "status": status, "official_checksums": verified}


class Acceptance:
    def __init__(self, wp: WpCli) -> None:
        self.wp = wp
        self.base = wp.instance.url
        self.users: dict[str, Any] = {}
        self.results: list[dict[str, Any]] = []
        self.owns_fixture = False

    def fixture(self, *args: str) -> str:
        return self.wp.run("eval-file", str(FIXTURE), *args)

    def check(self, name: str, condition: bool) -> None:
        self.results.append({"case": name, "passed": condition})
        if not condition:
            raise RuntimeError(f"Native MFA acceptance failed: {name}.")

    def state(self, label: str) -> dict[str, Any]:
        state: dict[str, dict[str, Any]] = json.loads(self.fixture("status"))
        return state[label]

    def wait_retry(self, label: str) -> None:
        delay = int(self.state(label)["retry_after"])
        if delay > 10:
            raise RuntimeError(
                "Unexpected native retry delay; do not weaken the provider."
            )
        if delay:
            time.sleep(delay + 1)

    def password(self, label: str, path: str) -> Browser:
        browser = Browser(self.base)
        browser.request(path)
        user = self.users[label]
        form = Forms(browser.html).having(
            "log" if path.startswith("/wp-login") else "woocommerce-login-nonce"
        )
        fields = (
            {"log": user["login"], "pwd": user["password"]}
            if path.startswith("/wp-login")
            else {
                "username": user["login"],
                "password": user["password"],
                "login": "Log in",
            }
        )
        browser.submit(form, fields)
        return browser

    def factor(self, browser: Browser, code: str, backup: bool = False) -> None:
        fields = (
            {"provider": "Two_Factor_Backup_Codes", "two-factor-backup-code": code}
            if backup
            else {"authcode": code}
        )
        browser.submit(Forms(browser.html).having("wp-auth-nonce"), fields)

    def run(self) -> None:
        if self.fixture("exists") != "false":
            raise RuntimeError(
                "An existing owned MFA fixture needs explicit cleanup first."
            )
        self.owns_fixture = True
        data = json.loads(self.fixture("setup"))
        self.users = data["users"]
        self.check(
            "native_setup_rejects_invalid_code",
            all(
                self.users[label]["invalid_setup_refused"]
                for label in ("admin", "woo_admin")
            ),
        )
        browser = self.password("admin", "/wp-login.php")
        self.check(
            "wp_password_requires_factor_without_auth_cookie",
            browser.challenged() and not browser.signed_in(),
        )
        self.check(
            "wp_password_creates_no_authenticated_session",
            self.state("admin")["sessions"] == 0,
        )
        probe = Browser(self.base)
        probe.request("/wp-admin/profile.php")
        self.check(
            "unfinished_factor_cannot_enter_profile", "/wp-login.php" in probe.url
        )
        self.factor(browser, self.fixture("code", "admin", "wrong"))
        self.check(
            "incorrect_totp_creates_no_authentication",
            browser.challenged()
            and not browser.signed_in()
            and self.state("admin")["sessions"] == 0,
        )
        self.wait_retry("admin")
        correct = self.fixture("code", "admin")
        self.factor(browser, correct)
        self.check(
            "correct_totp_authenticates",
            browser.signed_in() and not browser.challenged(),
        )
        browser.request("/wp-admin/profile.php")
        self.check(
            "totp_session_reaches_native_profile",
            "/wp-admin/profile.php" in browser.url
            and 'id="your-profile"' in browser.html,
        )
        self.check(
            "native_session_records_factor", self.state("admin")["mfa_sessions"] == 1
        )
        replay = self.password("admin", "/wp-login.php")
        self.factor(replay, correct)
        self.check(
            "totp_replay_refused", replay.challenged() and not replay.signed_in()
        )
        self.wait_retry("admin")
        backup = self.password("admin", "/wp-login.php")
        code = self.users["admin"]["backup"][0]
        self.factor(backup, code, backup=True)
        self.check(
            "backup_code_authenticates", backup.signed_in() and not backup.challenged()
        )
        self.check("backup_code_consumed", self.state("admin")["backup_remaining"] == 9)
        reused = self.password("admin", "/wp-login.php")
        self.factor(reused, code, backup=True)
        self.check(
            "backup_code_reuse_refused", reused.challenged() and not reused.signed_in()
        )
        for language, path in data["paths"].items():
            before = self.state("woo_admin")["sessions"]
            woo = self.password("woo_admin", path)
            self.check(
                f"woo_{language}_password_requires_factor",
                woo.challenged() and not woo.signed_in(),
            )
            self.check(
                f"woo_{language}_password_creates_no_auth_session",
                self.state("woo_admin")["sessions"] == before,
            )
            self.factor(
                woo,
                self.fixture("code", "woo_admin")
                if language == "en"
                else self.users["woo_admin"]["backup"][0],
                backup=language == "de",
            )
            self.check(
                f"woo_{language}_valid_factor_authenticates",
                woo.signed_in() and not woo.challenged(),
            )
            for label in ("customer", "pending"):
                customer = self.password(label, path)
                self.check(
                    f"{label}_{language}_logs_in_without_extra_factor",
                    customer.signed_in() and not customer.challenged(),
                )
                self.check(
                    f"{label}_{language}_has_no_factor_configuration",
                    not self.state(label)["two_factor_required"],
                )
        for language, path in data["paths"].items():
            reset = Browser(self.base)
            reset.request(path)
            links = [
                link
                for link in Forms(reset.html).links
                if re.search(r"(?:lost-password|passwort-zuruecksetzen)/", link)
            ]
            self.check(f"{language}_native_reset_link_present", len(set(links)) == 1)
            reset.request(links[0])
            form = Forms(reset.html).having("user_login")
            form.attrs["action"] = form.attrs.get("action") or reset.url
            # PublicGuard's existing three-second minimum; no proof bypass.
            time.sleep(3.2)
            proof = ""
            if (
                self.wp.run(
                    "eval",
                    r"echo \Linker\Commerce\Protection\Configuration::active_mode();",
                )
                == "enforce"
            ):
                # Real same-origin preparation, scoped signed proof and journal;
                # only the explicit local provider fixture substitutes transport.
                reset.request(
                    "/wp-json/linker/v1/protection/prepare",
                    headers={"Origin": self.base},
                    json_data={"action": "password_reset"},
                )
                prepared = json.loads(reset.html)
                self.check(
                    f"{language}_native_reset_prepare",
                    reset.status == 200 and "prepare" in prepared,
                )
                reset.request(
                    "/wp-json/linker/v1/protection/verify",
                    headers={"Origin": self.base},
                    json_data={
                        "action": "password_reset",
                        "prepare": prepared["prepare"],
                        "token": "mfa565_password_reset_" + str(uuid.uuid4()),
                    },
                )
                verified = json.loads(reset.html)
                self.check(
                    f"{language}_native_reset_verify",
                    reset.status == 200 and "proof" in verified,
                )
                proof = verified["proof"]
            reset.submit(
                form,
                {
                    "user_login": self.users["customer"]["login"],
                    "wc_reset_password": "true",
                    "linker_proof": proof,
                },
            )
            self.check(
                f"{language}_reset_request_has_no_extra_factor",
                "reset-link-sent=true" in reset.url and not reset.challenged(),
            )
            reset.request(self.fixture("reset-link", "customer"))
            form = Forms(reset.html).having("password_1")
            changed_password = secrets.token_urlsafe(32)
            reset.submit(
                form,
                {
                    "password_1": changed_password,
                    "password_2": changed_password,
                    "save_password": "1",
                },
            )
            self.check(
                f"{language}_native_reset_completion_has_no_factor",
                "password-reset=true" in reset.url and not reset.challenged(),
            )
            self.users["customer"]["password"] = changed_password
            # Keep --keep-fixture usable without exposing the new local password
            # in argv, logs or the public report.
            self.wp.run(
                "eval",
                "$state=get_option('linker_admin_mfa_fixture'); $state['users']['customer']['password']=file_get_contents('php://stdin'); update_option('linker_admin_mfa_fixture',$state,false);",
                stdin=changed_password,
            )
            signed_in = self.password("customer", path)
            self.check(
                f"{language}_new_password_logs_customer_in_without_factor",
                signed_in.signed_in() and not signed_in.challenged(),
            )
        for kind in ("password", "application_password"):
            api = Browser(self.base)
            user = self.users["admin"]
            basic = base64.b64encode(f"{user['login']}:{user[kind]}".encode()).decode()
            api.request(
                "/wp-json/wp/v2/users/me?context=edit",
                headers={"Authorization": "Basic " + basic},
            )
            self.check(
                "api_ordinary_password_refused"
                if kind == "password"
                else "api_application_password_is_separate_working_lane",
                api.status in (401, 403)
                if kind == "password"
                else api.status == 200 and json.loads(api.html)["id"] == user["id"],
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance")
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Install/verify only the official local dependency.",
    )
    parser.add_argument(
        "--keep-fixture",
        action="store_true",
        help="Keep synthetic identities for subsequent Computer Use.",
    )
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    instance = Registry(home()).get(args.instance)
    if instance is None:
        raise RuntimeError("Use just up to create a registered local instance first.")
    wp = WpCli(require_php(), instance)
    # Require the native local mail/HTTP guards and this checkout before writes.
    safe = wp.run(
        "eval",
        "echo json_encode(defined('LINKER_LOCAL_MAIL_DIR') && has_filter('pre_wp_mail','linker_local_capture_mail')!==false && has_filter('pre_http_request','linker_local_filter_http')!==false && realpath(WP_PLUGIN_DIR.'/linker-commerce')==="
        + json.dumps(str(REPO / "plugins/linker-commerce"))
        + ");",
    )
    if safe != "true":
        raise RuntimeError("Native isolation and this checkout are required.")
    report: dict[str, Any] = {
        "instance": args.instance,
        "captured_utc": datetime.now(UTC).isoformat(),
    }
    test = Acceptance(wp)
    try:
        prepared = prepare(wp) if args.prepare else {}
        report["dependency"] = {**prepared, **verify_dependency(wp)}
        test.run()
        report["passed"] = True
    except (RuntimeError, OSError, ValueError) as error:
        report["passed"] = False
        report["failure"] = str(error)
    finally:
        report["checks"] = test.results
        if test.owns_fixture and not args.keep_fixture:
            test.fixture("cleanup")
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2) + "\n")
        args.evidence.chmod(0o600)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
