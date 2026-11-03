"""Local contract tests for the guarded #548 installation-facts migration."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    ("site_url", "expected_revision"),
    [
        (
            "https://de-linker.com",
            "3af07553f4a39a73dc37954507f9505b1fc2020e5bb8d3e6d3366aea474cc5f2",
        ),
        (
            "http://127.0.0.1:9347",
            "f2ad0af83a3ded16e161a7024a6f997c3e31f70c1c22ff0ad9231c75f2ad5846",
        ),
    ],
)
def test_controller_cli_selects_reviewed_site_binding_and_filters_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    site_url: str,
    expected_revision: str,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "controller_facts_migration", HERE.parent / "548-controller-facts.py"
    )
    assert spec is not None and spec.loader is not None
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    monkeypatch.setattr(
        os,
        "environ",
        {
            "APIFY_TOKEN_ALT": "fake-research-token",
            "apify_Token_alias": "fake-case-alias",
            "LINKER_DEPLOYMENT_SENTINEL": "preserved",
        },
    )
    observed: dict[str, object] = {}

    def transport(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        observed["env"] = kwargs.get("env")
        source = kwargs["input"]
        assert isinstance(source, str)
        encoded = re.search(r"'([A-Za-z0-9+/=]{100,})'", source)
        assert encoded is not None
        request = json.loads(base64.b64decode(encoded[1]))
        binding = request["plan"]["controller"]["installation_item"]["source"]
        observed["revision"] = binding["document_revision"]
        assert binding["product_id"] == 2409 and binding["page"] == 52
        assert binding["blob_sha256"] == (
            "98bbe6f74e4d4d0e2437c3917e1fb2365c352ad01b5c46d26ad82876cb18850d"
        )
        payload = {
            "schema_version": 1,
            "products": {},
            "site": site_url,
            "state": "restored",
            "observed_source_revision": "a" * 64,
            "changes": [],
        }
        return subprocess.CompletedProcess(
            command, 0, controller.MARKER + json.dumps(payload), ""
        )

    monkeypatch.setattr(controller.subprocess, "run", transport)
    monkeypatch.setattr(
        controller,
        "remote_target",
        lambda: Target("fixture", "/fixture", site_url, ("wp",), None, None),
    )
    monkeypatch.setattr(
        controller, "local_target", lambda _: controller.remote_target()
    )
    monkeypatch.setattr(
        controller.sys,
        "argv",
        [
            "controller",
            *(
                ["--production"]
                if site_url.startswith("https")
                else ["--instance", "p548"]
            ),
            "preview",
            "--receipt",
            str(tmp_path / "receipt"),
        ],
    )

    assert controller.main() == 0
    assert observed["env"] == {"LINKER_DEPLOYMENT_SENTINEL": "preserved"}
    assert observed["revision"] == expected_revision
    assert os.environ["APIFY_TOKEN_ALT"] == "fake-research-token"


def test_controller_binding_refuses_unreviewed_target_without_mutating_plan() -> None:
    spec = importlib.util.spec_from_file_location(
        "controller_facts_target", HERE.parent / "548-controller-facts.py"
    )
    assert spec is not None and spec.loader is not None
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    original = json.loads((HERE.parent / "548-controller-facts.json").read_bytes())
    before = json.dumps(original, sort_keys=True)
    with pytest.raises(ValueError, match="No reviewed installation document version"):
        controller.plan_for_target(original, "https://unreviewed.invalid")
    selected = controller.plan_for_target(original, "https://de-linker.com")
    assert json.dumps(original, sort_keys=True) == before
    old_source = original["controller"]["installation_item"]["source"]
    new_source = selected["controller"]["installation_item"]["source"]
    assert {
        key: value for key, value in old_source.items() if key != "document_revision"
    } == {key: value for key, value in new_source.items() if key != "document_revision"}


def test_batc_sales_unit_source_keeps_reviewed_document_path() -> None:
    spec = importlib.util.spec_from_file_location(
        "batc_sales_unit_migration", HERE.parent / "548-controller-facts.py"
    )
    assert spec is not None and spec.loader is not None
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    original = json.loads((HERE.parent / "548-batc-sales-unit.json").read_bytes())
    before = json.dumps(original, sort_keys=True)
    selected = controller.plan_for_target(original, "http://127.0.0.1:9347")
    source = original["figure"]["citation"]
    rebound = selected["figure"]["citation"]
    assert rebound["url"].startswith("http://127.0.0.1:9347/")
    assert (
        rebound["url"].split("/wp-content/", 1)[1]
        == source["url"].split("/wp-content/", 1)[1]
    )
    assert rebound["page"] == source["page"] == 3
    assert json.dumps(original, sort_keys=True) == before
    with pytest.raises(ValueError, match="target origin"):
        controller.plan_for_target(original, "file:///tmp/invalid")


def test_et_standby_source_rebinds_only_reviewed_origin() -> None:
    spec = importlib.util.spec_from_file_location(
        "et_standby_migration", HERE.parent / "548-controller-facts.py"
    )
    assert spec is not None and spec.loader is not None
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    original = json.loads((HERE.parent / "548-et-pv-standby.json").read_bytes())
    selected = controller.plan_for_target(original, "http://127.0.0.1:9347")
    assert selected["figure"]["value"] == "950 ~ 1000"
    assert selected["figure"]["unit"] == "V"
    assert selected["figure"]["citation"]["page"] == 2
    assert (
        selected["figure"]["citation"]["url"].replace(
            "http://127.0.0.1:9347", "https://de-linker.com"
        )
        == original["figure"]["citation"]["url"]
    )


def load_script() -> ModuleType:
    """Load the ticket-named migration as the CLI itself does."""
    spec = importlib.util.spec_from_file_location(
        "installation_facts_migration", HERE.parent / "548-installation-facts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = load_script()

from linker_cutover.target import Target  # type: ignore[import-not-found]  # noqa: E402


def plan() -> dict[str, object]:
    return {
        "schema_version": 1,
        "products": {
            "6506": {
                "model": "GW75K-ET-G10",
                "product_revision": "a" * 64,
                "items": [
                    {
                        "id": "synthetic-installation-fact",
                        "source": {
                            "document_id": "doc-one",
                            "document_revision": "b" * 64,
                            "blob_sha256": "c" * 64,
                            "product_id": 6506,
                        },
                    }
                ],
            }
        },
    }


def receipt() -> dict[str, object]:
    after = {"schema_version": 1, "items": [{"id": "synthetic-installation-fact"}]}
    return {
        "schema_version": 1,
        "site": "https://de-linker.test",
        "source_revision": "b" * 64,
        "changes": 1,
        "products": {
            "6506": {
                "model": "GW75K-ET-G10",
                "product_revision": "a" * 64,
                "before_exists": False,
                "before": None,
                "after": after,
                "after_hash": "c" * 64,
                "protected": "d" * 64,
                "documents": {},
                "product_documents": {},
                "sources": [],
            }
        },
    }


def test_temporary_minimal_plan_contract(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan()))

    loaded = migration.load_plan(path)

    assert loaded == plan()
    assert migration.build_request("preview", plan=loaded) == {
        "action": "preview",
        "plan": plan(),
    }


def test_batc_delivery_plan_keeps_existing_facts_and_source_conditions() -> None:
    path = HERE.parent / "548-batc-delivery.json"
    parser = migration._parser()
    args = parser.parse_args(
        [
            "--production",
            "preview",
            "--plan",
            str(path),
            "--receipt",
            "/tmp/unused-receipt",
        ]
    )
    migration._validate_args(parser, args)
    reviewed = migration.load_plan(args.plan)["products"]
    assert set(reviewed) == {"1956", "1957", "1958"}
    original = migration.load_plan()["products"]
    for pid, product in reviewed.items():
        items = product["items"]
        ids = [item["id"] for item in items]
        assert len(ids) == len(set(ids)) == 27
        assert {item["id"] for item in original[pid]["items"]} <= set(ids)
        added = items[7:]
        assert len(added) == 20 and sum(bool(item["conditions"]) for item in added) == 6
        assert all(item["handling"] == "manufacturer_included" for item in added)
        assert all(
            item["source"]["blob_sha256"]
            == "ef85dd1a58fc06e52f2dff79dda228884b412d17db7035aa45d41c57840f3f10"
            for item in added
        )
        assert all(item["source"]["product_id"] == int(pid) for item in added)
        bolts = next(item for item in added if item["id"] == "expansion-bolt")
        assert bolts["quantity"] == 4 and bolts["source"]["page"] == 35
        assert (
            next(item for item in added if item["id"] == "m8-screw")["quantity"] == 12
        )
    with pytest.raises(SystemExit):
        migration._validate_args(
            parser,
            parser.parse_args(
                [
                    "--production",
                    "apply",
                    "--plan",
                    str(path),
                    "--receipt",
                    "/tmp/unused-receipt",
                ]
            ),
        )


def test_batc_112_plan_keeps_only_evidenced_delivery_rows() -> None:
    products = migration.load_plan(HERE.parent / "548-batc-112-delivery.json")[
        "products"
    ]
    assert set(products) == {"1955"}
    items = products["1955"]["items"]
    original = migration.load_plan()["products"]["1955"]["items"]
    assert items[: len(original)] == original
    delivery = items[len(original) :]
    assert len(delivery) == 18
    assert len({item["id"] for item in delivery}) == 18
    assert not any(item["id"] == "et100-adapter-bracket" for item in delivery)
    assert (
        next(item for item in delivery if item["id"] == "expansion-anchor")["quantity"]
        == 4
    )
    assert (
        next(item for item in delivery if item["id"] == "pack-interconnection-harness")[
            "quantity"
        ]
        == 10
    )
    assert all(
        item["source"]["blob_sha256"]
        == "0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615"
        and item["source"]["product_id"] == 1955
        and item["source"]["page"] in (100, 101, 102)
        for item in delivery
    )


def test_batc_61_plan_keeps_only_evidenced_delivery_rows() -> None:
    products = migration.load_plan(HERE.parent / "548-batc-61-delivery.json")[
        "products"
    ]
    assert set(products) == {"1954"}
    items = products["1954"]["items"]
    original = migration.load_plan()["products"]["1954"]["items"]
    assert items[: len(original)] == original
    delivery = items[len(original) :]
    # The two packing rows (harness and anchors) moved into the reviewed plan
    # itself, cited to the user manual p.33-34; this plan keeps the rest.
    assert len(delivery) == 17
    assert len({item["id"] for item in delivery}) == 17
    # The GW61.4 quick guide lists the ET100 bracket as a conditional delivery
    # row; unlike the 112 cabinet it stays in the plan with its own condition.
    bracket = next(item for item in delivery if item["id"] == "et100-adapter-bracket")
    assert (
        bracket["quantity"] is None
        and bracket["handling"] == "site_engineering_required"
    )
    assert any("ET100" in condition["en"] for condition in bracket["conditions"])
    anchors = next(item for item in original if item["id"] == "expansion-anchor")
    assert anchors["quantity"] == 4
    assert not any(
        item["id"] in {"pack-interconnection-harness", "expansion-anchor"}
        for item in delivery
    )
    assert all(
        item["source"]["blob_sha256"]
        == "627e5444f47bc7db3afd0b1aeeb27099fcbf8eedfbe15fe7302015743a96bcd2"
        and item["source"]["product_id"] == 1954
        and item["source"]["page"] in (1, 2)
        for item in delivery
    )


def test_batc_plan_passes_native_installation_facts_binding() -> None:
    reviewed = migration.load_plan(HERE.parent / "548-batc-delivery.json")["products"]
    source = reviewed["1956"]["items"][0]["source"]
    manifest = {
        "products": [{"product_id": int(pid)} for pid in reviewed],
        "documents": [
            {
                "document_id": source["document_id"],
                "document_revision": source["document_revision"],
                "blob_sha256": source["blob_sha256"],
                "url": source["url"],
                "product_ids": [1956, 1957, 1958],
            }
        ],
    }
    php = r"""
function __($text, $domain = null) { return $text; }
function wp_parse_url($url, $part = -1) { return parse_url($url, $part); }
require $argv[1];
$input = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
$out = [];
foreach ($input['products'] as $id => $product) {
    foreach ($product['items'] as $item) {
        $out[$id][] = \Linker\Commerce\Products\Publication\InstallationFacts::bind((int) $id, $item, $input['manifest']);
    }
}
echo json_encode($out, JSON_THROW_ON_ERROR);
"""
    native_class = (
        HERE.parents[2]
        / "plugins/linker-commerce/includes/Products/Publication/InstallationFacts.php"
    )
    result = subprocess.run(
        ["php", "-r", php, str(native_class)],
        input=json.dumps({"products": reviewed, "manifest": manifest}),
        capture_output=True,
        text=True,
        check=True,
    )
    bound = json.loads(result.stdout)
    assert {pid: len(items) for pid, items in bound.items()} == {
        "1956": 27,
        "1957": 27,
        "1958": 27,
    }
    for pid, rows in bound.items():
        assert all(row["source"]["product_id"] == int(pid) for row in rows)


def test_preview_uses_the_explicit_plan_and_writes_private_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "reviewed.json"
    custom.write_text(json.dumps(plan()))
    receipt_path = tmp_path / "receipt.json"
    seen: list[dict[str, object]] = []

    def invoke(
        _site: object, request: dict[str, object]
    ) -> tuple[int, str, dict[str, object]]:
        seen.append(request)
        return 0, "", receipt()

    monkeypatch.setattr(migration, "remote_target", _site)
    monkeypatch.setattr(migration, "invoke", invoke)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "migration",
            "--production",
            "preview",
            "--plan",
            str(custom),
            "--receipt",
            str(receipt_path),
        ],
    )
    assert migration.main() == 0
    assert seen == [{"action": "preview", "plan": plan()}]
    assert receipt_path.stat().st_mode & 0o777 == 0o600


def test_reviewed_production_plan_is_frozen() -> None:
    loaded = migration.load_plan()
    products = loaded["products"]
    # Every revision is the production engineering feed's current revision for
    # that product; a drift must be re-frozen deliberately, never silently.
    assert {key: value["product_revision"] for key, value in products.items()} == {
        "1946": "1905e54d159db08b051fd5f4c4a2a0482553ecba6b3cb69281f2655cec6f0079",
        "1947": "57645b8a899a88306789a8a5438e5ae149e776ab15671c62d31358de85ae45f5",
        "1948": "6a90f36f123d723c8b3d4521c5c7370c2c5c013a07b637661194999a6cd92456",
        "6506": "09a55babbc7084f36f3f5cfbe7df2af0f41c4062ef53260a302fa6cab8c69b1a",
        "1954": "dd9f785d4f4111cad28b36a399aa18120520af65450027e4e852177a79ac0576",
        "1955": "c48c197c2ded9e1e8649605d4df814bcf0f2a73708376c5d741512c6f1ed1bfa",
        "1956": "36d74190a353e7d0feeeb0b39eaf2132fae7b62b89494c43d118f59174643df4",
        "1957": "ab932ff62fafe8258a289655ceed3844b266c413c2ee7a5592c055b2db087fd3",
        "1958": "7bf010528262953fc52fdce9e9f01131c857331745f4dd716ced8f46ec427923",
        "6508": "6d219f809af9df61366af537ac5aa2ebae92126c6349f246b6e8c8fc13248c0c",
        "6509": "3b7f8c0e00aff5a9bf25b77a3999a21f78ca81c13f6946100b2804f657a26691",
        "6510": "5a0d03c3019daaf62a44905f71fa20d7bc735f0b61b78f480a3356f45cafb1c9",
        "6511": "e06d299cdcddc5d052169accd523c0a1a149792b374c24a5d47d08eaa6405039",
        "6507": "cb1b6e1929d1d909884cd9fc877c90a0a861b29518f68c2d35598a6af42a3eb5",
        "3556": "c61d005dd608416b42ca50cbbfb3c3becaf8683323dcf5a972c03e039ba2ecdb",
        "3583": "0b06639d065d0274f3238694eb3d546c9b0dbe39601a02908a15b7fde62f4aa4",
        "3584": "4d19772168857ce10e0afdc2441eb549a8ceccef69e0759feeddb893ac92597c",
        "3585": "1660557909692586588594c653ecc7a7cfec82fc7f3c3b7079a5e861f721049f",
        "6512": "6ddcff19b8e4cdfdc42f57f0b83d3626a7b4110525ac90202a27ba193140d0a8",
        "6513": "3fb82f2e52ac14fabb0242f0cb6a8979b0d1b362ebcdb175ca2c738cbdda0d1f",
        "6514": "f416421f7a010ba040c71a74142c9fd36da746e5c07bab1a7ebdcf728979d049",
        "6515": "2104492d0f27b6b4f20bdae90182678b2f9f51b8f1140bea1575d64c89362e87",
        "6516": "d2b572d65dea4c75755a8d7f0ff5e98e7da26dc0934c83e2217e1c4045cb0f10",
        "6517": "186176acb187a2a5e10916f828233b8fb4ae3bb80078a10f91ac04566328b704",
        "6518": "1b7295f6cfb5839bcc420aaaf943f385887e6b2f42674efb0ead30e5512dc5b3",
        "6523": "6a057ec30223888f8e72dd56f82990d046393c9aa80520516700c49a8354251a",
        "6524": "4a142d8ba66d41ec66c5062f52b3e42c0b8d182a4020a0cd895fcf1e4ed471d9",
        "6525": "9d98356f090e9d13370dbe727b250eeb1a783f7e9ca031dce04394e1b5571812",
        "6526": "516da9f7e81d38a5b7d0c259a453ced9969b786980a2354f23465c4fa63cce8a",
        "6527": "53803361db782dcc92b499cfc7c2d21c9efa9503bc48e6ba1c21471cf80a19a1",
        "6528": "087c31c1b966063adb4fe3d288628e8c1c6f385c039800d99598e2a3f4829604",
        "1179": "1dc26f004eba03a95b54971efac6f0bbf3e954c21ed8350fc4fd59a9bef471e4",
        "1181": "04df76aded6d942785a2038708978e85f3c35c6fe5b8f4e1f58e973aeb2bc1fa",
        "2063": "8e949f05e2a8e160a20277179bcc0a6710b369db712d38ec0c77836f1ef9a92f",
        "2064": "fe3af484e443e4b15a0489172278cdb58fbbf93b7091267be08625a3bd1c4f8e",
        "4107": "9b1031b5fbf03d272a3feab2c98e51801a8678a3a9636ed219f071fccbdfa483",
        "4108": "8aeb8912cbb86c764e456468882945e5e00082e8e668b703083289039688b8f0",
    }
    items = [item for product in products.values() for item in product["items"]]
    assert len(items) == 244
    assert (
        len(
            {
                (key, item["id"])
                for key, product in products.items()
                for item in product["items"]
            }
        )
        == 244
    )
    terminal_uses = {
        (key, item["id"]): item["specification"]["terminal_use"]
        for key, product in products.items()
        for item in product["items"]
        if "terminal_use" in item["specification"]
    }
    assert terminal_uses == {
        (key, item_id): value
        for key in ("1956", "1957", "1958")
        for item_id, value in migration.TERMINAL_USES.items()
    }
    sources = {
        item["source"]["document_id"]: (
            item["source"]["document_revision"],
            item["source"]["blob_sha256"],
        )
        for item in items
    }
    assert sources == {
        "doc-cbd6d3d2db163cf7bce09abf348fd8531756f4e1f3e1ae9a2d82418b322a2568": (
            "049d06e27cb8f711c57de5c72058f5c1bc2ddface3b698cd1690ebcac5c0870b",
            "0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615",
        ),
        "doc-e135c80bd4befdcd3c7e807944036da9a13c966b4c61ad40e6ff7886cf10b42f": (
            "f802c3c76d87d6e4dc6b724b400a1ce6fe9ebcb38a3475f3e4d5dcfaffc2ba63",
            "50bdd49b7be0ef036cafec286994f33af79dab5fc54dfcebbf4549f7e429acf9",
        ),
        "doc-a7cfa5ad5c55cfba8128f3992a05ac5cb86138460b1e9dcbea4fd833142abdf7": (
            "50f227b4ca819bc905bda317c96e5b0cfbab936e282dd03c04a0372498ddc695",
            "67a7f715ca9db734edba1b4f15b50d1a29c866b172ffd1909759e0abc66c8d2a",
        ),
        "doc-c4fbcd9555254fb0b1bf2e727cf62baeba7508def61a72cad65bee85e88cba1c": (
            "45179e2995ca322ecb0da13093dd34f62f19f2fc3ae929cac23fcc958cfe297e",
            "5cd104b9e006bd3b8265d0518dabdaaec01058f44ac065544da1d00d8cb4b619",
        ),
        "doc-71f7f3e62a4027f2314d84c508116dcfc51e08b7aae750b747d055c94fc41551": (
            "ef3d49749a232536940ce99dcc245820cd53bbfa1cd05b12057d4e398c4cef49",
            "770ccafa080cb6f4484453c976e48a44df71d7fe63bc220506c1f3e9191a75b3",
        ),
        "doc-d78c367ed40dc7e371bbdb1c6d26d927ba4b8d947fa6b73c777ab11ff0ee345f": (
            "4c1e6ff6e6aba309ab1abfc7cd074c0828df3553b7817a9262e4e49a74a4ccf7",
            "627e5444f47bc7db3afd0b1aeeb27099fcbf8eedfbe15fe7302015743a96bcd2",
        ),
        "doc-3e98151c21d284ce5e01603742e3ef027ca73cff3f42b9cf9b3fe164aa91882b": (
            "aaf54a301d81f354cff2a06dd8bf2c599705fcd5549e0dd271efa49402f28ca1",
            "ef85dd1a58fc06e52f2dff79dda228884b412d17db7035aa45d41c57840f3f10",
        ),
        "doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a": (
            "caa2e292a2c784906f32f2ab98153b4c3e2cfc1e05436627a53cf2caec7571bc",
            "c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7",
        ),
    }

    def without_revisions(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: without_revisions(item)
                for key, item in value.items()
                if key not in {"product_revision", "document_revision", "terminal_use"}
            }
        if isinstance(value, list):
            return [without_revisions(item) for item in value]
        return value

    canonical = json.dumps(
        without_revisions(loaded),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == (
        "ac3a6f44c621cdbc2b72ceb40c3b765dd06094d8b4fb9e9cddb2ebbe94beb3ce"
    )


def test_every_quote_appears_on_the_page_its_source_cites() -> None:
    """A page number alone is not evidence; the quote must be on that page."""
    excerpts = json.loads((HERE.parent / "548-page-excerpts.json").read_text())
    plan = migration.load_plan()
    checked = 0
    for key, product in plan["products"].items():
        for item in product["items"]:
            source = item["source"]
            document = excerpts["documents"].get(source["document_id"])
            assert document is not None, f"{key}/{item['id']} has no excerpt"
            assert document["blob_sha256"] == source["blob_sha256"]
            page = document["pages"].get(str(source["page"]))
            assert page is not None, (
                f"{key}/{item['id']} cites an excerpted-missing page"
            )
            assert not _absent_words(source["quote"], page), f"{key}/{item['id']}"
            checked += 1
    assert checked == 244


def _absent_words(quote: str, page: str) -> list[str]:
    """Words of the quote that do not appear on the page, ignoring line wrapping.

    PDF extraction splits words at column and line breaks ("pre- assembled",
    "50- 70mm²"), so a word is present when its letters and digits appear in
    order on the page with nothing between them.
    """

    def squash(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    flat = squash(page)
    return [
        word
        for word in quote.split()
        if len(re.sub(r"[^A-Za-z0-9]", "", word)) >= 3 and squash(word) not in flat
    ]


def test_plan_rejects_extra_fields_and_empty_products(tmp_path: Path) -> None:
    changed = plan()
    changed["purpose"] = "not part of the transport contract"
    path = tmp_path / "extra.json"
    path.write_text(json.dumps(changed))
    with pytest.raises(migration.MigrationError, match="only schema_version"):
        migration.load_plan(path)

    path.write_text(json.dumps({"schema_version": 1, "products": {}}))
    with pytest.raises(migration.MigrationError, match="no products"):
        migration.load_plan(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("document_id", "", "needs a document ID"),
        ("document_revision", "", "valid document_revision"),
        ("document_revision", None, "valid document_revision"),
        ("blob_sha256", "not-a-hash", "valid blob_sha256"),
        ("product_id", 6507, "belongs to another product"),
    ],
)
def test_plan_rejects_an_invalid_source_identity(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    changed = plan()
    products = migration._json_object(changed["products"], "products")
    product = migration._json_object(products["6506"], "product")
    items = product["items"]
    assert isinstance(items, list)
    item = migration._json_object(items[0], "item")
    source = migration._json_object(item["source"], "source")
    source[field] = value
    path = tmp_path / "invalid-source.json"
    path.write_text(json.dumps(changed))

    with pytest.raises(migration.MigrationError, match=message):
        migration.load_plan(path)


def test_receipt_is_exclusive_and_private(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    migration.write_receipt(path, receipt())

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert migration.load_receipt(path) == receipt()
    with pytest.raises(FileExistsError):
        migration.write_receipt(path, receipt())


def test_receipt_rejects_group_access(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    migration.write_receipt(path, receipt())
    path.chmod(0o640)

    with pytest.raises(migration.MigrationError, match="0600"):
        migration.load_receipt(path)


def test_stable_marker_is_unique() -> None:
    output = "noise\n" + migration.MARKER + json.dumps({"status": "ok"}) + "\n"

    assert migration.parse_marker(output) == {"status": "ok"}
    with pytest.raises(migration.MigrationError, match="found 2"):
        migration.parse_marker(output + output)


def test_invoke_keeps_verify_result_from_nonzero_php(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def run(
        command: list[str], *, input: str, capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        observed.update(
            command=command,
            input=input,
            capture_output=capture_output,
            text=text,
            check=check,
        )
        output = migration.MARKER + json.dumps(
            {**receipt(), "products": [{"status": "failed"}]}
        )
        return subprocess.CompletedProcess(command, 1, output, "verification failed")

    monkeypatch.setattr(migration.subprocess, "run", run)
    site = migration.Target(
        label="local:fixture",
        root="/tmp/fixture",
        base_url="http://fixture.invalid",
        prefix=("wp",),
        shell_prefix=None,
        rsync_remote=None,
    )

    code, error, result = migration.invoke(
        site, migration.build_request("verify", receipt=receipt())
    )

    assert code == 1
    assert error == "verification failed"
    assert result is not None and result["products"] == [{"status": "failed"}]
    assert observed["check"] is False
    assert "eval-file" in str(observed["command"])
    assert str(observed["input"]).startswith("<?php")


def refresh_plan(tmp_path: Path) -> Path:
    """A two-product plan with one cited document, written where refresh can find it."""
    path = tmp_path / "plan.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "products": {
                    "6506": {
                        "model": "GW75K-ET-G10",
                        "product_revision": "a" * 64,
                        "items": [
                            {
                                "id": "ac-conductor",
                                "source": {
                                    "document_id": "doc-one",
                                    "document_revision": "b" * 64,
                                    "blob_sha256": "c" * 64,
                                    "product_id": 6506,
                                },
                            }
                        ],
                    }
                },
            },
            indent=2,
        )
        + "\n"
    )
    return path


def _site() -> Target:
    return Target(
        label="local:fixture",
        root="/tmp/fixture",
        base_url="http://fixture.invalid",
        prefix=("wp",),
        shell_prefix=None,
        rsync_remote=None,
    )


def test_refresh_reports_without_writing_and_keeps_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A revision moves; the plan is only rewritten when asked."""
    path = refresh_plan(tmp_path)
    before = path.read_text()
    reply = {
        "schema_version": 1,
        "site": "https://fixture.invalid",
        "source_revision": "d" * 64,
        "products": {
            "6506": {
                "product_revision": "e" * 64,
                "documents": {
                    "doc-one": {"document_revision": "f" * 64, "blob_sha256": "c" * 64}
                },
            }
        },
    }
    monkeypatch.setattr(migration, "PLAN", path)
    monkeypatch.setattr(migration, "invoke", lambda *_args, **_kw: (0, "", reply))

    assert migration._refresh(_site(), write=False) == 0
    assert path.read_text() == before
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed == {"action": "refresh", "changes": 2, "written": False}


def test_refresh_refuses_moved_source_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Different bytes mean the page and quote need a human, not a re-pin."""
    path = refresh_plan(tmp_path)
    before = path.read_text()
    reply = {
        "schema_version": 1,
        "site": "https://fixture.invalid",
        "source_revision": "d" * 64,
        "products": {
            "6506": {
                "product_revision": "e" * 64,
                "documents": {
                    "doc-one": {"document_revision": "f" * 64, "blob_sha256": "9" * 64}
                },
            }
        },
    }
    monkeypatch.setattr(migration, "PLAN", path)
    monkeypatch.setattr(migration, "invoke", lambda *_args, **_kw: (0, "", reply))

    with pytest.raises(migration.MigrationError, match="Source bytes changed"):
        migration._refresh(_site(), write=True)
    assert path.read_text() == before


def test_refresh_writes_only_revisions_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The written file keeps its formatting and changes two values."""
    path = refresh_plan(tmp_path)
    before = path.read_text()
    reply = {
        "schema_version": 1,
        "site": "https://fixture.invalid",
        "source_revision": "d" * 64,
        "products": {
            "6506": {
                "product_revision": "e" * 64,
                "documents": {
                    "doc-one": {"document_revision": "f" * 64, "blob_sha256": "c" * 64}
                },
            }
        },
    }
    monkeypatch.setattr(migration, "invoke", lambda *_args, **_kw: (0, "", reply))

    assert migration._refresh(_site(), write=True, plan_path=path) == 0
    written = path.read_text()
    loaded = json.loads(written)
    assert loaded["products"]["6506"]["product_revision"] == "e" * 64
    assert (
        loaded["products"]["6506"]["items"][0]["source"]["document_revision"]
        == "f" * 64
    )
    # Only the two revisions moved: every other line is byte-identical.
    before_lines = before.splitlines()
    after_lines = written.splitlines()
    assert len(before_lines) == len(after_lines)
    differing = [
        (old, new)
        for old, new in zip(before_lines, after_lines, strict=True)
        if old != new
    ]
    assert len(differing) == 2
    assert all("aaaa" in old or "bbbb" in old for old, _new in differing)


def test_refresh_refuses_a_product_set_that_differs_from_the_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An extra or missing product means the two sides disagree; say so."""
    path = refresh_plan(tmp_path)
    reply = {
        "schema_version": 1,
        "site": "https://fixture.invalid",
        "source_revision": "d" * 64,
        "products": {
            "6506": {
                "product_revision": "e" * 64,
                "documents": {
                    "doc-one": {"document_revision": "f" * 64, "blob_sha256": "c" * 64}
                },
            },
            # The plan never named this one; ignoring it would hide the mismatch.
            "9999": {"product_revision": "1" * 64, "documents": {}},
        },
    }
    monkeypatch.setattr(migration, "PLAN", path)
    monkeypatch.setattr(migration, "invoke", lambda *_args, **_kw: (0, "", reply))
    before = path.read_text()

    with pytest.raises(migration.MigrationError, match="different product set"):
        migration._refresh(_site(), write=True)
    assert path.read_text() == before


def test_refresh_refuses_conflicting_revision_substitutions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One old hash cannot be rewritten into two different current hashes."""
    path = refresh_plan(tmp_path)
    loaded = json.loads(path.read_text())
    loaded["products"]["6507"] = {
        **json.loads(json.dumps(loaded["products"]["6506"])),
        "model": "GW70K-ET-G10",
    }
    source = loaded["products"]["6507"]["items"][0]["source"]
    source["product_id"] = 6507
    path.write_text(json.dumps(loaded, indent=2) + "\n")
    before = path.read_text()
    reply = {
        "schema_version": 1,
        "site": "https://fixture.invalid",
        "source_revision": "d" * 64,
        "products": {
            "6506": {
                "product_revision": "e" * 64,
                "documents": {
                    "doc-one": {"document_revision": "b" * 64, "blob_sha256": "c" * 64}
                },
            },
            "6507": {
                "product_revision": "f" * 64,
                "documents": {
                    "doc-one": {"document_revision": "b" * 64, "blob_sha256": "c" * 64}
                },
            },
        },
    }
    monkeypatch.setattr(migration, "PLAN", path)
    monkeypatch.setattr(migration, "invoke", lambda *_args, **_kw: (0, "", reply))

    with pytest.raises(migration.MigrationError, match="multiple values"):
        migration._refresh(_site(), write=True)
    assert path.read_text() == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["--production", "refresh", "--receipt", "/tmp/not-used.json"],
        ["--production", "preview", "--write"],
        ["--production", "preview"],
    ],
)
def test_action_specific_options_are_rejected(arguments: list[str]) -> None:
    parser = migration._parser()
    args = parser.parse_args(arguments)

    with pytest.raises(SystemExit):
        migration._validate_args(parser, args)


def test_terminal_patch_selects_exact_reviewed_items_without_mutating_plan() -> None:
    original = migration.load_plan()
    frozen = json.dumps(original, sort_keys=True)
    selected = migration.terminal_use_plan(original)

    assert set(selected["products"]) == {"1956", "1957", "1958"}
    assert all(
        {item["id"] for item in entry["items"]} == set(migration.TERMINAL_USES)
        for entry in selected["products"].values()
    )
    assert json.dumps(original, sort_keys=True) == frozen
    assert set(migration.terminal_use_plan(original, "1958")["products"]) == {"1958"}

    selected["products"]["1958"]["items"][0]["specification"]["terminal_use"] = (
        "changed"
    )
    assert json.dumps(original, sort_keys=True) == frozen


def test_terminal_patch_local_rebind_keeps_original_bytes_and_plan_in_memory() -> None:
    selected = migration.terminal_use_plan(migration.load_plan(), "1958")
    entry = selected["products"]["1958"]
    source = entry["items"][0]["source"]
    pinned: dict[str, Any] = {
        "products": {
            "1958": {
                "product_revision": "e" * 64,
                "documents": {
                    source["document_id"]: {
                        "document_revision": "f" * 64,
                        "blob_sha256": source["blob_sha256"],
                    }
                },
            }
        }
    }
    migration.rebind_local_patch(selected, pinned)
    assert entry["product_revision"] == "e" * 64
    assert all(
        item["source"]["document_revision"] == "f" * 64 for item in entry["items"]
    )
    pinned["products"]["1958"]["documents"][source["document_id"]]["blob_sha256"] = (
        "0" * 64
    )
    with pytest.raises(migration.MigrationError, match="Source bytes changed"):
        migration.rebind_local_patch(selected, pinned)


@pytest.mark.parametrize(
    "arguments",
    [
        [
            "--production",
            "preview",
            "--terminal-use-patch",
            "--product",
            "1958",
            "--receipt",
            "/tmp/x",
        ],
        ["--instance", "p548", "apply", "--terminal-use-patch", "--receipt", "/tmp/x"],
        ["--instance", "p548", "preview", "--product", "1958", "--receipt", "/tmp/x"],
    ],
)
def test_terminal_patch_rejects_partial_production_or_invalid_actions(
    arguments: list[str],
) -> None:
    parser = migration._parser()
    with pytest.raises(SystemExit):
        migration._validate_args(parser, parser.parse_args(arguments))


def test_terminal_receipt_refuses_unrelated_changes_and_conflicting_scope() -> None:
    before: dict[str, Any] = {
        "schema_version": 1,
        "items": [
            {
                "id": "external-communication-terminal",
                "specification": {"other": "preserved"},
            },
            {"id": "internal-communication-terminals", "specification": {}},
            {"id": "later-added-fact", "specification": {"x": 1}},
        ],
        "other_metadata": "preserved",
    }
    after = json.loads(json.dumps(before))
    for item in after["items"]:
        if item["id"] in migration.TERMINAL_USES:
            item["specification"]["terminal_use"] = migration.TERMINAL_USES[item["id"]]
    diff = [
        {
            "product_id": 1958,
            "item_id": item["id"],
            "before": None,
            "after": migration.TERMINAL_USES[item["id"]],
        }
        for item in before["items"]
        if item["id"] in migration.TERMINAL_USES
    ]
    data = {
        "site": "http://127.0.0.1:9347",
        "products": {"1958": {"before_exists": True, "before": before, "after": after}},
        "terminal_use_changes": diff,
    }
    migration.validate_terminal_receipt(data)

    after["items"][2]["specification"]["x"] = 2
    with pytest.raises(migration.MigrationError, match="unrelated metadata"):
        migration.validate_terminal_receipt(data)
    after["items"][2]["specification"]["x"] = 1
    data["site"] = "https://de-linker.com"
    with pytest.raises(migration.MigrationError, match="all three products"):
        migration.validate_terminal_receipt(data)


def test_terminal_patch_php_preserves_extra_facts_and_rejects_conflicts() -> None:
    """Run the real PHP binder and migration against an in-memory Woo fixture."""
    reviewed = migration.load_plan()
    fixture = {
        "full": reviewed["products"]["1958"],
        "patch": migration.terminal_use_plan(reviewed, "1958"),
        "migration": str(HERE.parent / "548-installation-facts.php"),
        "binder": str(
            migration.ROOT
            / "plugins/linker-commerce/includes/Products/Publication/InstallationFacts.php"
        ),
    }
    encoded = base64.b64encode(json.dumps(fixture).encode()).decode()
    php = r"""<?php
namespace Linker\Commerce\Products {
 final class Publication {
  public static function manifest(): array {
   $manifest = $GLOBALS['fixture_manifest'];
   $manifest['source_revision'] = hash('sha256', json_encode($GLOBALS['fixture_meta']));
   return $manifest;
  }
  public static function canonical_id(int $id): int { return $id; }
  public static function is_published(int $id): bool { return $id === 1958; }
  public static function revision(mixed $data): string {
   return hash('sha256', json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
  }
 }
 final class EngineeringFeed {
  public static function item(int $id, array $manifest): array {
   return ['installation_facts' => \Linker\Commerce\Products\Publication\InstallationFacts::projection($id, $manifest)];
  }
 }
}
namespace {
 define('ABSPATH', '/fixture/');
 class WC_Product {
  public function __construct(private int $id) {}
  public function get_attribute(string $name): string { return $GLOBALS['fixture_full']['model']; }
  public function get_data(): array { return ['id' => $this->id, 'meta_data' => []]; }
 }
 class WP_CLI { public static function error(string $message): never { throw new \RuntimeException($message); } }
 function __(string $message, string $domain): string { return $message; }
 function esc_html(string $message): string { return $message; }
 function home_url(): string { return $GLOBALS['fixture_site']; }
 function wp_parse_url(string $url, int $part): mixed { return parse_url($url, $part); }
 function wp_json_encode(mixed $value, int $flags = 0): string|false { return json_encode($value, $flags); }
 function wc_get_product(int $id): WC_Product { return new WC_Product($id); }
 function metadata_exists(string $type, int $id, string $key): bool { return array_key_exists($id, $GLOBALS['fixture_meta']); }
 function get_post_meta(int $id, string $key, bool $single): mixed { return $GLOBALS['fixture_meta'][$id] ?? ''; }
 function wp_slash(mixed $value): mixed { return $value; }
 function update_post_meta(int $id, string $key, mixed $next, mixed $previous): bool {
  if (($GLOBALS['fixture_meta'][$id] ?? null) !== $previous) { return false; }
  $GLOBALS['fixture_meta'][$id] = $next; return true;
 }
 function add_post_meta(int $id, string $key, mixed $value, bool $unique): bool {
  if (array_key_exists($id, $GLOBALS['fixture_meta'])) { return false; }
  $GLOBALS['fixture_meta'][$id] = $value; return true;
 }
 function delete_post_meta(int $id, string $key, mixed $value): bool {
  if (($GLOBALS['fixture_meta'][$id] ?? null) !== $value) { return false; }
  unset($GLOBALS['fixture_meta'][$id]); return true;
 }
 function wc_delete_product_transients(int $id): void {}
 function require_it(bool $condition, string $message): void {
  if (!$condition) { throw new \RuntimeException($message); }
 }
 function run_migration(array $request): array {
  $source = file_get_contents($GLOBALS['fixture_script']);
  $payload = base64_encode(json_encode($request, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
  $needle = "'548-installation-facts-payload'";
  require_it(substr_count($source, $needle) === 1, 'payload placeholder');
  $source = str_replace($needle, "'" . $payload . "'", $source);
  ob_start();
  try { eval('?>' . $source); $output = ob_get_clean(); }
  catch (\Throwable $error) { ob_end_clean(); throw $error; }
  require_it((bool) preg_match('/@@548-installation-facts@@([^\n]+)/', $output, $match), 'result marker');
  return json_decode($match[1], true, 512, JSON_THROW_ON_ERROR);
 }
 $fixture = json_decode(base64_decode('__FIXTURE__'), true, 512, JSON_THROW_ON_ERROR);
 $GLOBALS['fixture_full'] = $fixture['full'];
 $GLOBALS['fixture_script'] = $fixture['migration'];
 $GLOBALS['fixture_site'] = 'http://127.0.0.1:9347';
 $src = $fixture['full']['items'][0]['source'];
 $GLOBALS['fixture_manifest'] = [
  'products' => [['product_id' => 1958, 'product_revision' => $fixture['full']['product_revision']]],
  'documents' => [[
   'document_id' => $src['document_id'], 'document_revision' => $src['document_revision'],
   'blob_sha256' => $src['blob_sha256'], 'product_ids' => [1958], 'url' => 'https://de-linker.com/document.pdf',
  ]],
 ];
 $GLOBALS['fixture_meta'] = [2409 => ['controller' => 'preserve']];
 require $fixture['binder'];
 $rows = [];
 foreach ($fixture['full']['items'] as $item) {
  unset($item['specification']['terminal_use']);
  $rows[] = json_decode(json_encode(\Linker\Commerce\Products\Publication\InstallationFacts::bind(1958, $item, $GLOBALS['fixture_manifest'])), true);
 }
 $rows[1]['customer_note'] = 'keep even when projection ignores this key';
 $extra = $rows[0]; $extra['id'] = 'later-added-fact'; $rows[] = $extra;
 $GLOBALS['fixture_meta'][1958] = ['schema_version' => 1, 'items' => $rows, 'other_metadata' => 'keep'];
 $before = $GLOBALS['fixture_meta'];
 $request = ['action' => 'preview', 'plan' => $fixture['patch'], 'terminal_use_patch' => true];
 $receipt = run_migration($request);
 $expected = $before[1958];
 foreach ($expected['items'] as &$item) {
  if ($item['id'] === 'external-communication-terminal') { $item['specification']['terminal_use'] = 'external_communication'; }
  if ($item['id'] === 'internal-communication-terminals') { $item['specification']['terminal_use'] = 'internal_communication'; }
 }
 unset($item);
 require_it($receipt['products'][1958]['before'] === $before[1958], 'exact preimage');
 require_it($receipt['products'][1958]['after'] === $expected, 'only reviewed fields changed');
 require_it(count($receipt['terminal_use_changes']) === 2, 'two diffs');
 $GLOBALS['fixture_meta'][1958]['items'][7]['label']['en'] = 'concurrent edit';
 $concurrent = $GLOBALS['fixture_meta'];
 try { run_migration(['action' => 'apply', 'receipt' => $receipt]); throw new \RuntimeException('concurrent edit accepted'); }
 catch (\RuntimeException $error) { require_it(str_contains($error->getMessage(), 'Concurrent edit'), 'concurrent edit error'); }
 require_it($GLOBALS['fixture_meta'] === $concurrent, 'concurrent edit overwritten');
 $GLOBALS['fixture_meta'] = $before;
 run_migration(['action' => 'apply', 'receipt' => $receipt]);
 require_it($GLOBALS['fixture_meta'][1958] === $expected && $GLOBALS['fixture_meta'][2409] === $before[2409], 'apply preserved other data');
 $verified = run_migration(['action' => 'verify', 'receipt' => $receipt]);
 require_it($verified['products'][0]['status'] === 'verified' && $verified['products'][0]['item_count'] === 8, 'projection verification');
 run_migration(['action' => 'rollback', 'receipt' => $receipt]);
 require_it($GLOBALS['fixture_meta'] === $before, 'rollback restored exact preimage');
 $verified = run_migration(['action' => 'verify', 'receipt' => $receipt]);
 require_it($verified['products'][0]['status'] === 'restored', 'rollback verification');
 $GLOBALS['fixture_meta'][1958]['items'][1]['source']['quote'] = 'changed source quote';
 $source_changed = $GLOBALS['fixture_meta'];
 try { run_migration($request); throw new \RuntimeException('changed source quote accepted'); }
 catch (\RuntimeException $error) { require_it(str_contains($error->getMessage(), 'reviewed source'), 'source error'); }
 require_it($GLOBALS['fixture_meta'] === $source_changed, 'source change mutated data');
 $GLOBALS['fixture_meta'] = $before;
 $GLOBALS['fixture_meta'][1958]['items'][1]['specification']['terminal_use'] = 'internal_communication';
 $conflict = $GLOBALS['fixture_meta'];
 try { run_migration($request); throw new \RuntimeException('conflicting terminal use accepted'); }
 catch (\RuntimeException $error) { require_it(str_contains($error->getMessage(), 'Conflicting terminal use'), 'conflict error'); }
 require_it($GLOBALS['fixture_meta'] === $conflict, 'conflict mutated data');
 $GLOBALS['fixture_meta'] = $before;
 $GLOBALS['fixture_meta'][1958]['items'][] = $GLOBALS['fixture_meta'][1958]['items'][1];
 $duplicate = $GLOBALS['fixture_meta'];
 try { run_migration($request); throw new \RuntimeException('duplicate accepted'); }
 catch (\RuntimeException $error) { require_it(str_contains($error->getMessage(), 'identities'), 'duplicate error'); }
 require_it($GLOBALS['fixture_meta'] === $duplicate, 'duplicate mutated data');
 $GLOBALS['fixture_meta'] = $before;
 $GLOBALS['fixture_site'] = 'https://de-linker.com';
 try { run_migration($request); throw new \RuntimeException('partial production scope accepted'); }
 catch (\RuntimeException $error) { require_it(str_contains($error->getMessage(), 'product scope'), 'production scope error'); }
 echo json_encode(['receipt' => $receipt, 'checks' => 'passed']);
}
""".replace("__FIXTURE__", encoded)
    result = subprocess.run(
        [os.environ.get("PHP", "php")],
        input=php,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["checks"] == "passed"
    migration.validate_terminal_receipt(payload["receipt"])
