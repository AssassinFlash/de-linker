"""Read actual MFA-fixture reset links from native MIME without changing bytes."""

import base64
import quopri
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from linker_local.cli import require_php

REPO = Path(__file__).resolve().parents[3]
ORIGIN = "http://127.0.0.1:9999"
KEY = "12abcdefSYNTHETIC"
HARNESS = r"""
define('LINKER_LOCAL_MAIL_DIR', $argv[2]);
class Two_Factor_Core {}
class WP_Error {}
function home_url() { return 'http://127.0.0.1:9999'; }
function wp_parse_url($url, $component) { return parse_url($url, $component); }
function get_option($key) {
    return ['users' => ['customer' => ['id' => 127, 'login' => 'synthetic']],
        'job_marker' => 0, 'started' => time() - 1];
}
function check_password_reset_key($key, $login) {
    return $key === $GLOBALS['current_key'] && $login === 'synthetic'
        ? (object) ['ID' => 127] : new WP_Error();
}
function is_wp_error($value) { return $value instanceof WP_Error; }
$wpdb = new class {
    public $posts = 'synthetic_posts';
    function prepare($query, ...$args) { return $query; }
    function get_col($query) { return []; }
};
$GLOBALS['current_key'] = $argv[3];
$args = ['reset-link', 'customer'];
require $argv[1];
"""


def run_fixture(
    tmp_path: Path, message: bytes, key: str = KEY
) -> subprocess.CompletedProcess[str]:
    (tmp_path / "reset.eml").write_bytes(message)
    return subprocess.run(
        [
            str(require_php()),
            "-d",
            "display_errors=stderr",
            "-d",
            "log_errors=0",
            "-r",
            HARNESS,
            str(REPO / "tests/e2e/fixtures/admin-mfa.php"),
            str(tmp_path),
            key,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def mime(body: str, transfer: str, *, html: bool = False) -> bytes:
    raw = body.replace("\r\n", "\n").encode()
    if transfer == "quoted-printable":
        raw = quopri.encodestring(raw).replace(b"\n", b"\r\n")
    elif transfer == "base64":
        raw = base64.encodebytes(raw).replace(b"\n", b"\r\n")
    content_type = "text/html" if html else "text/plain"
    return (
        f"MIME-Version: 1.0\r\nContent-Type: {content_type}; charset=UTF-8\r\n"
        f"Content-Transfer-Encoding: {transfer}\r\n\r\n"
    ).encode() + raw


@pytest.mark.parametrize(
    "path", ["/my-account/lost-password/", "/de/mein-konto/passwort-vergessen/"]
)
@pytest.mark.parametrize("transfer", ["7bit", "8bit", "quoted-printable", "base64"])
def test_actual_fixture_preserves_native_reset_url(
    tmp_path: Path, path: str, transfer: str
) -> None:
    url = f"{ORIGIN}{path}?key={KEY}&id=127&login=synthetic"
    message = mime(f"Reset: {url}\r\n", transfer)
    if transfer == "quoted-printable":
        assert b"=3D" in message and b"=\r\n" in message
    result = run_fixture(tmp_path, message)
    assert result.returncode == 0, result.stderr
    assert result.stdout == url
    query = parse_qs(urlsplit(result.stdout).query)
    assert query["key"] == [KEY]
    assert query["id"] == ["127"]


def test_raw_8bit_id_is_unchanged_even_with_non_hexadecimal_key(tmp_path: Path) -> None:
    key = "XYsynthetic"
    url = f"{ORIGIN}/my-account/lost-password/?key={key}&id=127&login=synthetic"
    result = run_fixture(tmp_path, mime(url, "8bit"), key)
    assert result.returncode == 0, result.stderr
    assert result.stdout == url


@pytest.mark.parametrize("nested", [False, True])
def test_actual_fixture_decodes_each_mime_part_and_html_entities(
    tmp_path: Path, nested: bool
) -> None:
    url = f"{ORIGIN}/de/mein-konto/passwort-vergessen/?key={KEY}&id=127"
    html = f'<a href="{url.replace("&", "&amp;")}">Reset</a>'
    part = mime(html, "quoted-printable", html=True)
    alternative = (
        b'MIME-Version: 1.0\r\nContent-Type: multipart/alternative;\r\n boundary="inner"\r\n\r\n'
        b"Preamble without a link\r\n--inner\r\n"
        + mime("No reset link in this part", "8bit")
        + b"\r\n--inner\r\n"
        + part
        + b"\r\n--inner--\r\nEpilogue"
    )
    message = (
        b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n--outer\r\n"
        + alternative
        + b"\r\n--outer--\r\n"
        if nested
        else alternative
    )
    result = run_fixture(tmp_path, message)
    assert result.returncode == 0, result.stderr
    assert result.stdout == url


@pytest.mark.parametrize(
    "url",
    [
        f"{ORIGIN}/my-account/?key=stale&id=127",
        f"https://outside.example.test/my-account/?key={KEY}&id=127",
        f"{ORIGIN}/my-account/?key={KEY}&id=128",
        f"{ORIGIN}/my-account/?key={KEY}&id=127\x12",
    ],
)
def test_actual_fixture_rejects_wrong_key_origin_user_or_control_byte(
    tmp_path: Path, url: str
) -> None:
    result = run_fixture(tmp_path, mime(url, "8bit"))
    assert result.returncode != 0
    assert result.stdout == ""
    assert "Synthetic reset message link was not captured or queued." in result.stderr
