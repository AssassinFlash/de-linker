"""Local contract tests for the guarded #548 installation-facts migration."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parent


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


def plan() -> dict[str, object]:
    return {
        "schema_version": 1,
        "products": {
            "6506": {
                "model": "GW75K-ET-G10",
                "product_revision": "a" * 64,
                "items": [{"id": "synthetic-installation-fact"}],
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
        "1946": "8c58ef59d9a26c71ceef4b50a7a292db2eb05be5c026f19c02c25d6c67691cff",
        "1947": "9847a57dd2e25496ae7b7ddf3eb5f0f0a202c62ccf47f1e7cbd2fe8432e42ce5",
        "1948": "0c392521153a0a71eed2410649899a49b9b21e58359b66afd02c755a69a36ec3",
        "1954": "090af3986f95c2efc1d8d56b385950856e66875c3e1414b026fe37e417f9ba3c",
        "1955": "25f07a8dc18233724e00a7c76358eb41f20e2693b4a3281797e8663e2828d160",
        "1956": "fb06653f64b58ffdc8ab3fd4a3ae378dc197994de9351786c3a17e9b5687a1ed",
        "1957": "31ea4f4167bd968f27a7b9a5bf1388453947dff28c44586d5f5eaf82c9d8fba5",
        "1958": "27d0043f7c585933fecd6791cf5c84e1eb50f19f6be42cb9787687ae1e621a4b",
        "6506": "6649e8812b5d8512a5e3378ff0c3747f59bd04a4849d71a6e72611af6271bd8f",
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
                if key not in {"product_revision", "document_revision"}
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
