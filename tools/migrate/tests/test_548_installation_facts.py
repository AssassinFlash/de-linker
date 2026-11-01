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


def test_reviewed_production_plan_is_frozen() -> None:
    loaded = migration.load_plan()
    products = loaded["products"]
    expected_products = {
        "1946": "0648c8aa0b650d17621e50744c61feb010c58a2e5a448fde016c686fd2438742",
        "1947": "15e0b0767810a724225b087cc3ec73b8fe3a8a1282cc7db3dc1579ee20d15265",
        "1948": "d8e229d764db3166800870ee5c557f84699339dae26b2d2e1e0432f0cf2e0c0a",
        "1954": "1037614099efe170172740951c617922ee5fc85d28804c929f329fdd7329e6f1",
        "1955": "9676819e7e5c10f877b2d35afdbd5ef5e7446fa5ea260edf396777c3df0aa8c4",
        "1956": "9104ae6aaa016d9bd59fc3f5fc83a7d78277aff7cd1fa29fbd2b55de023391fd",
        "1957": "f5596878526182efb277dbcba304d6a1400a2ee111539c3fe2b1809ec20ea2ce",
        "1958": "cd3bffeafc67000c8f94c63b203b13916604d44891ff43200bc3864f0e69230c",
        "6506": "5e368eccda3f40fc1e38bfc4a341bc1eef23e939ba6143af68dfe62dd4a71b2d",
    }
    expected_documents = {
        "doc-3e98151c21d284ce5e01603742e3ef027ca73cff3f42b9cf9b3fe164aa91882b": (
            "aaf54a301d81f354cff2a06dd8bf2c599705fcd5549e0dd271efa49402f28ca1",
            "ef85dd1a58fc06e52f2dff79dda228884b412d17db7035aa45d41c57840f3f10",
        ),
        "doc-cbd6d3d2db163cf7bce09abf348fd8531756f4e1f3e1ae9a2d82418b322a2568": (
            "049d06e27cb8f711c57de5c72058f5c1bc2ddface3b698cd1690ebcac5c0870b",
            "0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615",
        ),
        "doc-d78c367ed40dc7e371bbdb1c6d26d927ba4b8d947fa6b73c777ab11ff0ee345f": (
            "4c1e6ff6e6aba309ab1abfc7cd074c0828df3553b7817a9262e4e49a74a4ccf7",
            "627e5444f47bc7db3afd0b1aeeb27099fcbf8eedfbe15fe7302015743a96bcd2",
        ),
    }

    assert {
        key: value["product_revision"] for key, value in products.items()
    } == expected_products
    items = [item for product in products.values() for item in product["items"]]
    assert len(items) == 79
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
    assert sources == expected_documents

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
        "e431b80f7bcc7decf02ac43e5fd8751f8ab6826848af62138c138e63fa1b1648"
    )


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
    monkeypatch.setattr(migration, "PLAN", path)
    monkeypatch.setattr(migration, "invoke", lambda *_args, **_kw: (0, "", reply))

    assert migration._refresh(_site(), write=True) == 0
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
        ["/opt/homebrew/opt/php@8.3/bin/php"],
        input=php,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["checks"] == "passed"
    migration.validate_terminal_receipt(payload["receipt"])
