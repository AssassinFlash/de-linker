"""Inventory: every hosted PDF, deduplicated by sha256, with what the products say it is.

Sources, read with GET only (`python -m index.inventory`):
- the media library: every attachment with mime type application/pdf
  (`/wp/v2/media?mime_type=application/pdf`), the bytes downloaded from our own URL;
- the products' documents field: the ACF `downloads` rows in `_tv_legacy_acf_json`
  (EN title, type, language, attachment ID) and `_linker_de_acf_json` (DE title), read
  from `/wc/v3/products`. Brand and model come from the products that link a document;
  a document no product links keeps empty brands and models and the type `other`.

Credentials: a JSON file `{site_url, username, application_password}`
(`--rest-config`, default ~/.config/terravolt-builder/rest-de.json); never printed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from index.paths import INVENTORY_PATH, PDF_DIR

DEFAULT_REST_CONFIG = Path("~/.config/terravolt-builder/rest-de.json").expanduser()
# WordPress caps per_page at 100 (WP_REST_Controller::get_collection_params).
PER_PAGE = 100
# Four parallel downloads: the host is shared hosting; four keeps one PDF list
# (2.0 GB, 417 files on 2026-10-09) to minutes without opening many connections.
DOWNLOAD_WORKERS = 4
DOWNLOAD_ATTEMPTS = 3

# The documents field's own vocabulary (every `download_type` / `download_role` value
# on the live products, 2026-10-09) mapped onto the spec's five types
# (docs/specs/10-knowledge-index.md, Sources). Warranty, brochure and generic
# "document" rows are `other`.
_TYPE_BY_ROLE = {"compatibility_list": "compatibility"}
_TYPE_BY_LABEL = {
    "datasheet": "datasheet",
    "manual": "manual",
    "installation manual": "manual",
    "certificate": "certificate",
    "compatibility": "compatibility",
}
# `download_language` values on the live products (2026-10-09): EN, DE, MUL, MULTI,
# EN/DE, DE/EN, ES and empty. One language is that language; several are `multi`.
_LANG_BY_LABEL = {"EN": "en", "DE": "de", "ES": "es"}


@dataclass(frozen=True)
class Product:
    """A product and the model it sells; a search narrows by product through it."""

    id: int
    status: str
    brand: str
    model: str


@dataclass(frozen=True)
class ProductLink:
    """One row of a product's documents field."""

    product_id: int
    status: str
    brand: str
    model: str
    title_en: str
    title_de: str
    doc_type: str
    lang: str


@dataclass
class Document:
    """One unique PDF (by sha256) and everything the inventory knows about it."""

    sha256: str
    bytes: int
    urls: list[str]
    media_ids: list[int]
    title_en: str
    title_de: str
    brands: list[str]
    models: list[str]
    product_ids: list[int]
    doc_type: str
    lang: str
    linked: bool = field(default=False)


class RestClient:
    """GET-only client of the WordPress REST API."""

    def __init__(self, config_path: Path) -> None:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.base = str(config["site_url"]).rstrip("/")
        token = f"{config['username']}:{config['application_password']}".encode()
        self._auth = "Basic " + base64.b64encode(token).decode()

    def get(self, path: str, params: Mapping[str, str | int]) -> tuple[Any, int, int]:
        """One page: the decoded body, X-WP-Total and X-WP-TotalPages."""
        url = f"{self.base}/wp-json{path}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={"Authorization": self._auth, "User-Agent": "linker-genie-index"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.load(response)
            total = int(response.headers.get("X-WP-Total", "0"))
            pages = int(response.headers.get("X-WP-TotalPages", "0"))
        return body, total, pages

    def get_all(
        self, path: str, params: Mapping[str, str | int]
    ) -> list[dict[str, Any]]:
        """Every page of a collection; fails unless the count matches X-WP-Total."""
        rows: list[dict[str, Any]] = []
        page, pages, total = 1, 1, 0
        while page <= pages:
            body, total, pages = self.get(
                path, {**params, "per_page": PER_PAGE, "page": page}
            )
            rows.extend(body)
            page += 1
        if len(rows) != total:
            raise RuntimeError(
                f"{path}: read {len(rows)} rows, X-WP-Total says {total}"
            )
        return rows


def _meta(product: Mapping[str, Any], key: str) -> Any:
    for row in product.get("meta_data", []):
        if row.get("key") == key:
            return row.get("value")
    return None


def _attribute(product: Mapping[str, Any], name: str) -> str:
    for attribute in product.get("attributes", []):
        if attribute.get("name") == name and attribute.get("options"):
            return str(attribute["options"][0])
    return ""


def _downloads(product: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    raw = _meta(product, key)
    if not raw:
        return []
    rows = json.loads(raw).get("downloads") if isinstance(raw, str) else None
    return [row for row in rows or [] if isinstance(row, dict)]


def doc_type_of(label: str, role: str) -> str:
    """The spec's type for one documents-field row."""
    if role.strip().lower() in _TYPE_BY_ROLE:
        return _TYPE_BY_ROLE[role.strip().lower()]
    return _TYPE_BY_LABEL.get(label.strip().lower(), "other")


def lang_of(label: str) -> str:
    """`en`, `de`, another ISO code, `multi` for several, or "" when unstated."""
    label = label.strip().upper()
    if not label:
        return ""
    if label in _LANG_BY_LABEL:
        return _LANG_BY_LABEL[label]
    return "multi"


def product_of(product: Mapping[str, Any]) -> Product:
    """Brand and model of one product: its Brand and Model attributes, else the
    `_delinker_brand` / `_delinker_model` meta and the brand taxonomy that drafts carry."""
    brand = _attribute(product, "Brand") or str(_meta(product, "_delinker_brand") or "")
    if not brand and product.get("brands"):
        brand = str(product["brands"][0].get("name", ""))
    model = _attribute(product, "Model") or str(_meta(product, "_delinker_model") or "")
    return Product(int(product["id"]), str(product.get("status", "")), brand, model)


def product_links(
    products: Sequence[Mapping[str, Any]],
) -> dict[int, list[ProductLink]]:
    """Attachment ID -> the documents-field rows that link it."""
    links: dict[int, list[ProductLink]] = {}
    for product in products:
        identity = product_of(product)
        titles_de = {
            row.get("download_file"): str(row.get("download_title") or "")
            for row in _downloads(product, "_linker_de_acf_json")
        }
        for row in _downloads(product, "_tv_legacy_acf_json"):
            attachment = row.get("download_file")
            if not isinstance(attachment, int):
                continue
            links.setdefault(attachment, []).append(
                ProductLink(
                    product_id=identity.id,
                    status=identity.status,
                    brand=identity.brand,
                    model=identity.model,
                    title_en=str(row.get("download_title") or ""),
                    title_de=titles_de.get(attachment, ""),
                    doc_type=doc_type_of(
                        str(row.get("download_type") or ""),
                        str(row.get("download_role") or ""),
                    ),
                    lang=lang_of(str(row.get("download_language") or "")),
                )
            )
    return links


def _most_common(values: Sequence[str]) -> str:
    """The most frequent non-empty value; ties go to the alphabetically first."""
    counts = Counter(value for value in values if value)
    if not counts:
        return ""
    best = max(counts.values())
    return min(value for value, count in counts.items() if count == best)


def build_documents(
    media: Sequence[Mapping[str, Any]],
    sha_by_media: Mapping[int, str],
    links: Mapping[int, Sequence[ProductLink]],
) -> list[Document]:
    """One Document per sha256, merging every attachment that serves those bytes."""
    by_sha: dict[str, list[Mapping[str, Any]]] = {}
    for item in media:
        by_sha.setdefault(sha_by_media[int(item["id"])], []).append(item)
    documents = []
    for sha, items in sorted(by_sha.items()):
        items = sorted(items, key=lambda item: int(item["id"]))
        rows = [link for item in items for link in links.get(int(item["id"]), [])]
        media_titles = [str(item["title"]["rendered"]) for item in items]
        documents.append(
            Document(
                sha256=sha,
                bytes=int(items[0]["media_details"]["filesize"]),
                urls=[str(item["source_url"]) for item in items],
                media_ids=[int(item["id"]) for item in items],
                title_en=_most_common([row.title_en for row in rows])
                or media_titles[0],
                title_de=_most_common([row.title_de for row in rows]),
                brands=sorted({row.brand for row in rows if row.brand}),
                models=sorted({row.model for row in rows if row.model}),
                product_ids=sorted({row.product_id for row in rows}),
                doc_type=_most_common([row.doc_type for row in rows]) or "other",
                lang=_most_common([row.lang for row in rows]),
                linked=bool(rows),
            )
        )
    return documents


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_one(
    item: Mapping[str, Any], pdf_dir: Path, cached: Mapping[str, Any]
) -> str:
    """Bytes of one attachment into `<sha256>.pdf`; returns the sha256."""
    size = int(item["media_details"]["filesize"])
    if (
        cached.get("source_url") == item["source_url"]
        and cached.get("modified_gmt") == item["modified_gmt"]
        and (pdf_dir / f"{cached.get('sha256')}.pdf").is_file()
        and (pdf_dir / f"{cached.get('sha256')}.pdf").stat().st_size == size
    ):
        return str(cached["sha256"])
    last_error: Exception | None = None
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            with tempfile.NamedTemporaryFile(
                dir=pdf_dir, suffix=".part", delete=False
            ) as handle:
                part = Path(handle.name)
                request = urllib.request.Request(
                    str(item["source_url"]),
                    headers={"User-Agent": "linker-genie-index"},
                )
                with urllib.request.urlopen(request, timeout=300) as response:
                    for block in iter(lambda: response.read(1 << 20), b""):
                        handle.write(block)
            if part.stat().st_size != size:
                raise OSError(
                    f"{item['source_url']}: {part.stat().st_size} bytes, media says {size}"
                )
            sha = _sha256_of(part)
            part.replace(pdf_dir / f"{sha}.pdf")
            return sha
        except OSError as error:
            last_error = error
            part.unlink(missing_ok=True)
            time.sleep(2**attempt)
    raise RuntimeError(f"download failed: {item['source_url']}") from last_error


def download_all(media: Sequence[Mapping[str, Any]], pdf_dir: Path) -> dict[int, str]:
    """Every attachment's sha256, downloading only what the media cache lacks."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    cache_path = pdf_dir / "media-cache.json"
    cache: dict[str, Any] = (
        json.loads(cache_path.read_text(encoding="utf-8"))
        if cache_path.is_file()
        else {}
    )

    def one(item: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
        return item, _download_one(item, pdf_dir, cache.get(str(item["id"]), {}))

    shas: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        for done, (item, sha) in enumerate(pool.map(one, media), start=1):
            shas[int(item["id"])] = sha
            cache[str(item["id"])] = {
                "source_url": item["source_url"],
                "modified_gmt": item["modified_gmt"],
                "sha256": sha,
            }
            if done % 25 == 0 or done == len(media):
                print(f"downloaded {done}/{len(media)}", flush=True)
                cache_path.write_text(
                    json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8"
                )
    return shas


def _iter_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument("--rest-config", type=Path, default=DEFAULT_REST_CONFIG)
    parser.add_argument("--out", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    return parser.parse_args(argv)


def run(rest_config: Path, out: Path, pdf_dir: Path) -> list[Document]:
    """Read the live lists, download the bytes and write the inventory JSON."""
    client = RestClient(rest_config)
    media = client.get_all(
        "/wp/v2/media",
        {
            "mime_type": "application/pdf",
            "_fields": "id,source_url,title,modified_gmt,media_details",
        },
    )
    products = client.get_all("/wc/v3/products", {"status": "any"})
    print(f"{len(media)} PDF attachments, {len(products)} products", flush=True)
    documents = build_documents(
        media, download_all(media, pdf_dir), product_links(products)
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": client.base,
        "read_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attachments": len(media),
        "products": [asdict(product_of(product)) for product in products],
        "documents": [asdict(document) for document in documents],
    }
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(documents)} unique documents -> {out}", flush=True)
    return documents


def load(path: Path = INVENTORY_PATH) -> list[Document]:
    """The documents of an inventory written by `run`."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Document(**row) for row in payload["documents"]]


def load_products(path: Path = INVENTORY_PATH) -> list[Product]:
    """The products of an inventory written by `run`."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Product(**row) for row in payload["products"]]


def main(argv: Sequence[str] | None = None) -> int:
    args = _iter_args(argv)
    run(args.rest_config, args.out, args.pdf_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
