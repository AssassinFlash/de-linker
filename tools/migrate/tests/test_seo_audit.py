"""The URL/SEO audit distinguishes real page-type defects from empty schema."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

CHECKS = Path(__file__).resolve().parents[2] / "checks"


def load_audit() -> ModuleType:
    sys.path.insert(0, str(CHECKS))
    spec = importlib.util.spec_from_file_location("seo_audit", CHECKS / "seo-audit.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit_module = load_audit()


def page(
    url: str,
    *,
    robots: tuple[str, ...] = ("index", "follow"),
    hreflang: dict[str, str] | None = None,
    jsonld: tuple[object, ...] = (),
) -> Any:
    return audit_module.Page(
        url=url,
        status=200,
        final=url,
        robots=robots,
        hreflang=hreflang or {"en": url, "de": url, "x-default": url},
        canonical=(url,),
        jsonld=jsonld,
        internal_links=(),
    )


def test_noindex_and_unclassified_pages_do_not_require_schema() -> None:
    noindex_category = page(
        "https://de-linker.com/de/kategorie/systemauslegung/",
        robots=("follow", "noindex"),
    )
    ordinary_page = page("https://de-linker.com/privacy-policy/")

    result = audit_module.audit(
        {
            noindex_category.url: noindex_category,
            ordinary_page.url: ordinary_page,
        },
        {},
    )

    assert all(item.kind != "structured-data" for item in result.findings)


def test_the_indexable_library_requires_faqpage() -> None:
    library = page("https://de-linker.com/de/faq-dokumente/")

    result = audit_module.audit({library.url: library}, {})

    assert [(item.kind, item.url, item.detail) for item in result.findings] == [
        (
            "structured-data",
            library.url,
            "missing required type(s): FAQPage",
        )
    ]


def test_the_indexable_category_requires_collection_and_breadcrumb() -> None:
    category = page("https://de-linker.com/category/monitoring-energy-management/")

    result = audit_module.audit({category.url: category}, {})

    assert len(result.findings) == 1
    assert result.findings[0].detail == (
        "missing required type(s): BreadcrumbList, CollectionPage"
    )


def test_a_doubled_language_jsonld_url_is_a_self_url_defect() -> None:
    blog = page(
        "https://de-linker.com/de/blog/",
        jsonld=(
            {
                "@context": "https://schema.org",
                "@type": ["CollectionPage", "WebPage"],
                "url": "https://de-linker.com/de/de/blog/",
            },
        ),
    )

    result = audit_module.audit({blog.url: blog}, {})

    assert [
        (item.kind, item.detail)
        for item in result.findings
        if item.kind == "jsonld-self-url"
    ] == [
        (
            "jsonld-self-url",
            "['CollectionPage', 'WebPage'] claims https://de-linker.com/de/de/blog/",
        )
    ]


def test_a_retired_alias_is_not_judged_by_the_canonical_page_schema() -> None:
    alias_url = (
        "https://de-linker.com/product-category/residential-storage/res-accessories/"
    )
    final_url = "https://de-linker.com/product-category/accessories/"
    alias = audit_module.Page(
        url=alias_url,
        status=200,
        final=final_url,
        robots=("index", "follow"),
        hreflang={"en": final_url},
        canonical=(final_url,),
        jsonld=(
            {
                "@type": "CollectionPage",
                "url": final_url,
            },
        ),
        internal_links=(),
    )

    result = audit_module.audit({}, {alias_url: alias})

    assert result.findings == ()


def test_hreflang_indexability_is_symmetric() -> None:
    german = page(
        "https://de-linker.com/de/danke/",
        hreflang={
            "en": "https://de-linker.com/thank-you/",
            "de": "https://de-linker.com/de/danke/",
            "x-default": "https://de-linker.com/thank-you/",
        },
    )
    english = page(
        "https://de-linker.com/thank-you/",
        robots=("follow", "noindex"),
        hreflang={
            "en": "https://de-linker.com/thank-you/",
            "de": "https://de-linker.com/de/danke/",
            "x-default": "https://de-linker.com/thank-you/",
        },
    )

    result = audit_module.audit({german.url: german}, {english.url: english})

    assert [
        (item.kind, item.url, item.detail)
        for item in result.findings
        if item.kind == "indexability-asymmetry"
    ] == [
        (
            "indexability-asymmetry",
            german.url,
            "en alternate https://de-linker.com/thank-you/ is noindex",
        )
    ]
