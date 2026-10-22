"""Native inventory credential acceptance; no remote target or real key is accepted."""

from __future__ import annotations

import argparse
import base64
import http.cookiejar
import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xmlrpc.client
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from linker_local.cli import require_php
from linker_local.instance import home
from linker_local.registry import Registry
from linker_local.wpcli import WpCli

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "mu-plugins/tests/php/fixtures/inventory-access.php"
LOADER = FIXTURE.with_name("inventory-access-loader.php")
MEDIA = "/wp-json/wp/v2/media?mime_type=application%2Fpdf"
# One more than two full WordPress 100-row pages; acceptance always exercises pagination.
COUNT = 201


class LocalRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, base: str) -> None:
        self.origin = urllib.parse.urlsplit(base)[:2]

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if urllib.parse.urlsplit(newurl)[:2] != self.origin:
            raise RuntimeError("Refused a redirect outside the isolated local origin.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(
    base: str,
    path: str,
    auth: tuple[str, str] | None = None,
    method: str = "GET",
    data: dict[str, Any] | bytes | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, dict[str, str], bytes]:
    url = urllib.parse.urljoin(base, path)
    if urllib.parse.urlsplit(url)[:2] != urllib.parse.urlsplit(base)[:2]:
        raise RuntimeError("Only the owned local origin is accepted.")
    headers = dict(headers or {})
    if auth:
        headers["Authorization"] = (
            "Basic " + base64.b64encode(":".join(auth).encode()).decode()
        )
    payload = (
        data
        if isinstance(data, bytes)
        else json.dumps(data).encode()
        if data is not None
        else None
    )
    if isinstance(data, dict):
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, method=method, headers=headers, data=payload)
    opener = opener or urllib.request.build_opener(LocalRedirect(base))
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return (
            response.code,
            {key.lower(): value for key, value in response.headers.items()},
            response.read(),
        )


def cookie_login(base: str, user: dict[str, Any]) -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        LocalRedirect(base), urllib.request.HTTPCookieProcessor(jar)
    )
    fetch(base, "/wp-login.php", opener=opener)
    form = urllib.parse.urlencode(
        {
            "log": user["login"],
            "pwd": user["password"],
            "wp-submit": "Log In",
            "redirect_to": base + "/inventory-access-native-probe",
            "testcookie": "1",
        }
    ).encode()
    status, _, body = fetch(
        base,
        "/wp-login.php",
        method="POST",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        opener=opener,
    )
    if (
        status != 200
        or not json.loads(body)["authenticated"]
        or not any(cookie.name.startswith("wordpress_logged_in_") for cookie in jar)
    ):
        raise RuntimeError("Native cookie password login did not authenticate.")
    return opener


def inventory(wp: WpCli, state: dict[str, Any], directory: Path) -> dict[str, Any]:
    """Call the actual existing reader in its own native service environment."""
    config = directory / "rest.json"
    config.write_text(
        json.dumps(
            {
                "site_url": wp.instance.url,
                "username": state["users"]["admin"]["login"],
                "application_password": state["applications"]["selected"]["password"],
                "synthetic_collections": state["collections"],
            }
        )
    )
    config.chmod(0o600)
    code = """
import hashlib,json,sys
from pathlib import Path
from index.inventory import RestClient,product_links
config=Path(sys.argv[1]);c=RestClient(config);owned=json.loads(config.read_text())['synthetic_collections'];result={}
for name,path,params in [('media','/wp/v2/media',{'mime_type':'application/pdf','_fields':'id,source_url,title,modified_gmt,media_details'}),('products','/wc/v3/products',{'status':'any'})]:
 first,total,pages=c.get(path,{**params,'per_page':100,'page':1})
 rows=c.get_all(path,params)
 assert len(rows)==total and pages>=3, f'{name}: rows={len(rows)} total={total} pages={pages}'
 selected=[row for row in rows if row['id'] in owned[name]]
 assert len(selected)==len(owned[name])==201
 if name=='media':
  assert all(set(['id','source_url','title','modified_gmt','media_details'])<=set(row) and row['media_details']['filesize']==1234 for row in selected)
 else:
  assert len(product_links(selected))==len(selected)
  assert {'draft','private','publish'}<=set(row['status'] for row in selected)
 result[name]={'count':len(rows),'total':total,'pages':pages,'synthetic_count':len(selected),'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'metadata_complete':True}
print(json.dumps(result))
"""
    process = subprocess.run(
        ["uv", "run", "--locked", "python", "-c", code, str(config)],
        cwd=REPO / "services/genie",
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode:
        log = wp.instance.log_dir / "inventory-reader-error.log"
        log.write_text(process.stderr)
        log.chmod(0o600)
        raise RuntimeError(
            "The actual native inventory reader failed; no credentials are printed."
        )
    result: dict[str, Any] = json.loads(process.stdout)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    instance = Registry(home()).get(args.instance)
    if instance is None:
        raise RuntimeError("Create a registered native instance first.")
    wp = WpCli(require_php(), instance)
    safe = wp.run(
        "eval",
        "echo json_encode(defined('LINKER_LOCAL_MAIL_DIR') && has_filter('pre_wp_mail','linker_local_capture_mail')!==false && has_filter('pre_http_request','linker_local_filter_http')!==false && realpath(WP_PLUGIN_DIR.'/linker-commerce')==="
        + json.dumps(str(REPO / "plugins/linker-commerce"))
        + ");",
    )
    if safe != "true":
        raise RuntimeError("This checkout's isolated local instance is required.")
    if wp.run("eval-file", str(FIXTURE), "exists") != "false":
        raise RuntimeError("An owned fixture needs explicit cleanup first.")
    mode = instance.dir / "inventory-access-binding.json"
    loader = instance.wp_content / "mu-plugins/000-linker-inventory-test.php"
    if mode.exists() or loader.exists():
        raise RuntimeError("Do not overwrite another local fixture.")
    report: dict[str, Any] = {
        "captured_utc": datetime.now(UTC).isoformat(),
        "instance": args.instance,
        "checks": [],
        "synthetic_rows_per_collection": COUNT,
    }
    owned_users: list[int] = []
    owned_posts: list[int] = []

    def check(name: str, condition: bool) -> None:
        report["checks"].append({"case": name, "passed": condition})
        if not condition:
            raise RuntimeError("Native inventory acceptance failed: " + name)

    def binding(value: Any) -> None:
        if value is None:
            mode.unlink(missing_ok=True)
        else:
            temporary = mode.with_suffix(".next")
            temporary.touch(mode=0o600)
            temporary.write_text(json.dumps(value))
            temporary.replace(mode)

    def status() -> str:
        return wp.run(
            "eval",
            "echo class_exists('Linker\\\\Mu\\\\InventoryAccess') ? \\Linker\\Mu\\InventoryAccess::status() : 'not_installed';",
        )

    def usage() -> dict[str, int]:
        result: dict[str, int] = json.loads(
            wp.run(
                "eval",
                "$out=array('credentials'=>0,'used'=>0);foreach("
                + json.dumps(owned_users)
                + " as $id){foreach(WP_Application_Passwords::get_user_application_passwords($id) as $item){++$out['credentials'];if(null!==$item['last_used']){++$out['used'];}}}echo wp_json_encode($out);",
            )
        )
        return result

    try:
        state = json.loads(wp.run("eval-file", str(FIXTURE), "setup", str(COUNT)))
        owned_users = [record["id"] for record in state["users"].values()]
        owned_posts = state["posts"]
        report["native_credential_usage_before"] = usage()
        shutil.copyfile(
            REPO / "mu-plugins/linker-inventory-access.php",
            instance.wp_content / "mu-plugins/linker-inventory-access.php",
        )
        shutil.copyfile(LOADER, loader)
        loader.chmod(0o600)
        user = state["users"]["admin"]
        selected = (user["login"], state["applications"]["selected"]["password"])
        other = (user["login"], state["applications"]["other"]["password"])
        active = {
            "active": True,
            "user_id": user["id"],
            "uuid": state["applications"]["selected"]["uuid"],
        }
        post = f"/wp-json/wp/v2/posts/{state['sentinel']}"
        check("installed_without_binding_is_unconfigured", status() == "unconfigured")
        check(
            "unconfigured_does_not_claim_api_protection",
            fetch(instance.url, "/wp-json/wp/v2/users/me", selected)[0] == 200,
        )
        binding({"active": False})
        check("explicit_inactive_status", status() == "inactive")
        with tempfile.TemporaryDirectory(
            prefix="inventory574-", dir=instance.dir
        ) as temporary:
            directory = Path(temporary)
            baseline = inventory(wp, state, directory)
            binding(active)
            check("valid_native_binding_is_active", status() == "active")
            before = fetch(instance.url, post + "?context=edit", other)[2]
            check(
                "selected_write_denied",
                fetch(
                    instance.url,
                    post,
                    selected,
                    "POST",
                    {"title": "This write must be denied"},
                )[0]
                == 403,
            )
            for name, path in [
                ("pdf", MEDIA),
                ("products", "/wp-json/wc/v3/products?status=any"),
            ]:
                check(
                    name + "_collection_read_allowed",
                    fetch(instance.url, path, selected)[0] == 200,
                )
            check(
                "native_slash_normalization_keeps_same_collection",
                fetch(
                    instance.url,
                    "/wp-json/wp/v2/media/?mime_type=application/pdf",
                    selected,
                )[0]
                == 200,
            )
            embedded = json.loads(
                fetch(instance.url, MEDIA + "&_embed=author", selected)[2]
            )
            check(
                "native_embedded_author_subrequests_denied",
                bool(embedded)
                and all(
                    row.get("_embedded", {}).get("author", [{}])[0].get("code")
                    == "rest_forbidden"
                    for row in embedded
                ),
            )
            after = inventory(wp, state, directory)
            report["reader"] = {"before": baseline, "after": after}
            check(
                "actual_reader_full_pagination_metadata_identical",
                baseline == after,
            )
            cases: list[tuple[str, str, str, dict[str, Any] | None, dict[str, str]]] = [
                ("users", "/wp-json/wp/v2/users/me", "GET", None, {}),
                ("missing_pdf_filter", "/wp-json/wp/v2/media", "GET", None, {}),
                ("json_method_alias", MEDIA, "GET", {"_method": "GET"}, {}),
                ("post_query_get_alias", MEDIA + "&_method=GET", "POST", {}, {}),
                (
                    "single_media",
                    f"/wp-json/wp/v2/media/{state['posts'][0]}",
                    "GET",
                    None,
                    {},
                ),
                (
                    "single_product",
                    f"/wp-json/wc/v3/products/{state['posts'][1]}",
                    "GET",
                    None,
                    {},
                ),
                (
                    "route_case_alias",
                    "/wp-json/WP/v2/media?mime_type=application/pdf",
                    "GET",
                    None,
                    {},
                ),
                (
                    "non_pdf_media",
                    "/wp-json/wp/v2/media?mime_type=image/png",
                    "GET",
                    None,
                    {},
                ),
                ("head", MEDIA, "HEAD", None, {}),
                ("post_collection", MEDIA, "POST", {}, {}),
                ("put", post, "PUT", {"title": "Denied"}, {}),
                ("patch", post, "PATCH", {"title": "Denied"}, {}),
                ("delete", post + "?force=true", "DELETE", None, {}),
                ("options", MEDIA, "OPTIONS", None, {}),
                (
                    "query_method_delete",
                    post + "?_method=DELETE&force=true",
                    "GET",
                    None,
                    {},
                ),
                ("query_get_alias", MEDIA + "&_method=GET", "GET", None, {}),
                (
                    "header_method_delete",
                    post + "?force=true",
                    "GET",
                    None,
                    {"X-HTTP-Method-Override": "DELETE"},
                ),
                (
                    "post_get_alias",
                    MEDIA,
                    "POST",
                    {},
                    {"X-HTTP-Method-Override": "GET"},
                ),
                (
                    "header_get_alias",
                    MEDIA,
                    "GET",
                    None,
                    {"X-HTTP-Method-Override": "GET"},
                ),
                (
                    "batch",
                    "/wp-json/batch/v1",
                    "POST",
                    {
                        "requests": [
                            {
                                "method": "POST",
                                "path": "/linker-inventory-fixture/v1/mutate",
                            }
                        ]
                    },
                    {},
                ),
                (
                    "fake_binding_header",
                    "/wp-json/wp/v2/users/me",
                    "GET",
                    None,
                    {"X-Linker-Inventory-UUID": state["applications"]["other"]["uuid"]},
                ),
            ]
            for name, path, method, data, headers in cases:
                check(
                    name + "_denied",
                    fetch(instance.url, path, selected, method, data, headers)[0]
                    == 403,
                )
            for probe in ("read", "write", "batch", "query_alias", "header_alias"):
                response = fetch(
                    instance.url,
                    MEDIA + "&inventory_fixture_subrequest=" + probe,
                    selected,
                )
                check(
                    "internal_" + probe + "_denied",
                    response[0] == 200
                    and response[1].get("x-inventory-fixture-child-status") == "403",
                )
            check(
                "denied_requests_leave_record_identical",
                fetch(instance.url, post + "?context=edit", other)[2] == before,
            )
            check(
                "denied_subrequests_have_no_side_effect",
                wp.run(
                    "eval",
                    "echo (int)get_option('linker_inventory_fixture_mutations',0);",
                )
                == "0",
            )
            check(
                "canary_callback_positive_control",
                fetch(
                    instance.url,
                    "/wp-json/linker-inventory-fixture/v1/mutate",
                    other,
                    "POST",
                    {},
                )[0]
                == 200
                and wp.run(
                    "eval",
                    "echo (int)get_option('linker_inventory_fixture_mutations',0);",
                )
                == "1",
            )
            check(
                "unrelated_uuid_same_admin_is_unchanged",
                fetch(instance.url, "/wp-json/wp/v2/users/me", other)[0] == 200
                and fetch(
                    instance.url,
                    post,
                    other,
                    "POST",
                    {"title": "Unrelated credential retains native write"},
                )[0]
                == 200,
            )
            other_user = (
                state["users"]["other_admin"]["login"],
                state["applications"]["other_user"]["password"],
            )
            check(
                "same_uuid_on_different_user_is_unchanged",
                fetch(instance.url, "/wp-json/wp/v2/users/me", other_user)[0] == 200
                and fetch(instance.url, "/inventory-access-native-probe", other_user)[0]
                == 200,
            )
            check(
                "selected_nonrest_authentication_denied",
                fetch(instance.url, "/inventory-access-native-probe", selected)[0]
                == 403,
            )
            check(
                "unrelated_nonrest_authentication_unchanged",
                fetch(instance.url, "/inventory-access-native-probe", other)[0] == 200,
            )
            xml = xmlrpc.client.dumps(selected, methodname="wp.getUsersBlogs").encode()
            xml_response = fetch(
                instance.url,
                "/xmlrpc.php",
                method="POST",
                data=xml,
                headers={"Content-Type": "text/xml"},
            )
            try:
                xmlrpc.client.loads(xml_response[2])
                refused = False
            except xmlrpc.client.Fault as error:
                refused = error.faultCode == 403
            check("selected_xmlrpc_authentication_denied", refused)
            xml = xmlrpc.client.dumps(other, methodname="wp.getUsersBlogs").encode()
            xmlrpc.client.loads(
                fetch(
                    instance.url,
                    "/xmlrpc.php",
                    method="POST",
                    data=xml,
                    headers={"Content-Type": "text/xml"},
                )[2]
            )
            check("unrelated_xmlrpc_authentication_unchanged", True)
            sessions = {
                label: cookie_login(instance.url, state["users"][label])
                for label in ("admin", "customer")
            }
            for label, opener in sessions.items():
                check(
                    label + "_native_password_cookie_login_unchanged",
                    fetch(
                        instance.url, "/inventory-access-native-probe", opener=opener
                    )[0]
                    == 200,
                )
            nonce = json.loads(
                fetch(
                    instance.url,
                    "/inventory-access-native-probe",
                    opener=sessions["admin"],
                )[2]
            )["rest_nonce"]
            check(
                "native_admin_cookie_rest_write_unchanged",
                fetch(
                    instance.url,
                    post,
                    method="POST",
                    data={"title": "Native cookie write remains available"},
                    headers={"X-WP-Nonce": nonce},
                    opener=sessions["admin"],
                )[0]
                == 200,
            )
            binding({**active, "uuid": "00000000-0000-4000-8000-000000000001"})
            check("unresolved_active_binding_is_invalid", status() == "invalid")
            check(
                "invalid_binding_does_not_restore_selected_read",
                fetch(instance.url, MEDIA, selected)[0] == 403,
            )
            check(
                "invalid_binding_fails_closed_for_application_auth",
                fetch(instance.url, MEDIA, other)[0] == 403,
            )
            for label, opener in sessions.items():
                check(
                    label + "_cookie_unchanged_under_invalid_binding",
                    fetch(
                        instance.url, "/inventory-access-native-probe", opener=opener
                    )[0]
                    == 200,
                )
            binding("malformed-active-binding")
            check(
                "malformed_binding_invalid_and_closed",
                status() == "invalid"
                and fetch(instance.url, MEDIA, selected)[0] == 403,
            )
            binding(active)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(
                    pool.map(
                        lambda index: fetch(
                            instance.url,
                            MEDIA if index % 2 == 0 else "/wp-json/wp/v2/users/me",
                            selected,
                        )[0],
                        range(12),
                    )
                )
            check("parallel_requests_keep_per_request_scope", results == [200, 403] * 6)
            check("anonymous_page_is_unchanged", fetch(instance.url, "/")[0] == 200)
            check(
                "fake_identity_headers_cannot_authenticate",
                fetch(
                    instance.url,
                    "/wp-json/wp/v2/users/me",
                    headers={
                        "X-Linker-Inventory-UUID": active["uuid"],
                        "X-Linker-Inventory-User": str(active["user_id"]),
                    },
                )[0]
                in (401, 403),
            )
            report["passed"] = True
            report["native_credential_usage_after"] = usage()
    except (RuntimeError, ValueError, OSError, xmlrpc.client.Error) as error:
        report["passed"] = False
        report["failure"] = str(error)
    finally:
        try:
            wp.run("eval-file", str(FIXTURE), "cleanup")
        finally:
            loader.unlink(missing_ok=True)
            mode.unlink(missing_ok=True)
            mode.with_suffix(".next").unlink(missing_ok=True)
    report["cleanup"] = {
        "fixture_absent": wp.run("eval-file", str(FIXTURE), "exists") == "false",
        "binding_status": status(),
        "temporary_loader_absent": not loader.exists(),
    }
    remaining = json.loads(
        wp.run(
            "eval",
            "echo wp_json_encode(array('users'=>count(array_filter("
            + json.dumps(owned_users)
            + ",static fn($id)=>(bool)get_userdata($id))),'posts'=>count(array_filter("
            + json.dumps(owned_posts)
            + ",static fn($id)=>(bool)get_post($id)))));",
        )
    )
    report["cleanup"]["remaining_owned_resources"] = remaining
    check("all_owned_resources_deleted", remaining == {"users": 0, "posts": 0})
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2) + "\n")
        args.evidence.chmod(0o600)
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
