"""The page reader reads what the visitor's page shows (#234).

The fixtures are the `<main>` of real pages of the live snapshot 2026-10-18
(eval/page/capture_pages.py): the FAQ page (longer than the reader's budget), a blog post,
the German residential storage page and a GoodWe ESA product page.
"""

from pathlib import Path

import httpx
import pytest

from linker_genie import page
from linker_genie.page import PAGE_CHARS, PageReader, PageUnavailable
from linker_genie.schema import PageContext

PAGES = Path(__file__).resolve().parent / "fixtures" / "pages"


def _html(name: str) -> str:
    return (PAGES / name).read_text(encoding="utf-8")


def _site(
    pages: dict[str, httpx.Response], seen: list[str] | None = None
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(str(request.url))
        return pages.get(request.url.path, httpx.Response(404, text="not found"))

    return httpx.MockTransport(handle)


def _reader(
    pages: dict[str, httpx.Response], seen: list[str] | None = None
) -> PageReader:
    return PageReader("http://site.test", transport=_site(pages, seen))


def test_a_long_page_gives_its_opening_and_the_passages_the_question_names() -> None:
    reader = _reader({"/faq-download/": httpx.Response(200, text=_html("faq-en.html"))})
    result = reader.read(
        PageContext(type="faq", url="http://site.test/faq-download/", title="FAQ"),
        "What does this page say about transport damage?",
        logged_in=False,
    )
    assert result["complete"] is False
    assert len(result["text"]) <= PAGE_CHARS + 2_000  # headings and figure tags
    # The opening of the page, then the FAQ answer the question names.
    assert result["text"].startswith("## Answers and documents.")
    assert "freight receipt (CMR)" in result["text"]
    assert "Shipping & logistics" in result["outline"]


def test_a_page_within_the_budget_is_read_whole() -> None:
    path = "/hybrid-inverter-vs-ac-coupled-storage/"
    reader = _reader({path: httpx.Response(200, text=_html("blog-post-en.html"))})
    result = reader.read(
        PageContext(type="blog", url="http://site.test" + path, post_id=551),
        "Summarise this post",
        logged_in=False,
    )
    assert result["complete"] is True
    assert "## What is a hybrid inverter?" in result["text"]


def test_figures_of_the_page_are_tagged_and_become_facts() -> None:
    path = "/de/loesung/heimspeicher/"
    reader = _reader({path: httpx.Response(200, text=_html("solution-de.html"))})
    result = reader.read(
        PageContext(type="solution", url=path, title="Heimspeicher"),
        "Was meint diese Seite mit Notstrom?",
        logged_in=False,
    )
    # "10-kW-Dreiphasen-Heimspeichersystem": the number is a figure the answer cites.
    assert "[n1=10-kW]" in result["text"] or "[n1=" in result["text"]
    facts = page.collect(result)
    assert facts.facts["page"].value == "Heimspeicher"
    assert facts.facts["page.n1"].value == result["figures"]["page.n1"]
    assert "page.text" in facts.facts
    assert "figures" not in page.model_view(result)


def test_a_product_page_brings_its_description_and_product_questions() -> None:
    path = "/product/goodwe-esa-gw10k-eha-g20/"
    reader = _reader({path: httpx.Response(200, text=_html("product-en.html"))})
    result = reader.read(
        PageContext(type="product", url=path, product_id=6528, post_id=6528),
        "What does this page mean by internal bypass?",
        logged_in=False,
    )
    assert "internal bypass" in result["text"]
    assert "## Product questions" in result["text"]


def test_only_the_path_of_the_address_is_read_on_the_served_site() -> None:
    seen: list[str] = []
    reader = _reader(
        {"/blog/": httpx.Response(200, text="<main><p>Latest posts</p></main>")}, seen
    )
    result = reader.read(
        PageContext(type="blog", url="https://elsewhere.example/blog/?x=1"),
        "what is here",
        logged_in=False,
    )
    assert seen == ["http://site.test/blog/"]
    assert result["text"] == "Latest posts"


@pytest.mark.parametrize(
    "url", [None, "/wp-admin/", "/wp-json/wp/v2/users", "/wp-login.php", "/feed/"]
)
def test_an_address_that_is_no_page_is_not_read(url: str | None) -> None:
    seen: list[str] = []
    with pytest.raises(PageUnavailable):
        _reader({}, seen).read(PageContext(type="other", url=url), "q", False)
    assert seen == []


def test_a_redirect_is_followed_on_the_site_only() -> None:
    reader = _reader(
        {
            "/de/loesung": httpx.Response(301, headers={"location": "/de/loesung/"}),
            "/de/loesung/": httpx.Response(200, text="<main><p>Anwendung</p></main>"),
            "/away/": httpx.Response(302, headers={"location": "https://evil.test/"}),
        }
    )
    ok = reader.read(PageContext(type="solution", url="/de/loesung"), "q", False)
    assert ok["text"] == "Anwendung"
    with pytest.raises(PageUnavailable, match="off the site"):
        reader.read(PageContext(type="other", url="/away/"), "q", False)


def test_a_page_that_fails_is_unavailable_with_its_cause() -> None:
    reader = _reader({"/x/": httpx.Response(500, text="boom")})
    with pytest.raises(PageUnavailable, match="returned 500"):
        reader.read(PageContext(type="other", url="/x/"), "q", False)


def test_a_page_is_read_once_within_the_cache_time() -> None:
    seen: list[str] = []
    now = [0.0]
    reader = PageReader(
        "http://site.test",
        transport=_site(
            {"/": httpx.Response(200, text="<main><p>Home</p></main>")}, seen
        ),
        clock=lambda: now[0],
    )
    context = PageContext(type="home", url="/")
    reader.read(context, "a", False)
    reader.read(context, "b", False)
    assert len(seen) == 1
    now[0] = page.TTL_SECONDS + 1
    reader.read(context, "c", False)
    assert len(seen) == 2


def test_hidden_and_non_text_elements_are_left_out() -> None:
    html = (
        "<header><p>Menu</p></header><main><h1>Title</h1>"
        "<div hidden><p>Hidden copy</p></div><p aria-hidden='true'>Icon</p>"
        "<script>var x = 1;</script><!-- note --><p>Shown copy</p>"
        "<select><option>Afghanistan</option></select></main><footer>Foot</footer>"
    )
    found = page.passages(html)
    assert page.render(found) == "## Title\nShown copy"


def test_the_draft_is_its_products_by_name() -> None:
    seen: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.url.path == "/wp-json/wc/store/v1/products"
        assert request.url.params["include"] == "4109,2003"
        return httpx.Response(
            200,
            json=[
                {"id": 2003, "name": "Pylontech OPTIM US L260-OMNI"},
                {"id": 4109, "name": "SAJ HS2-5K-T2-X"},
            ],
        )

    reader = PageReader("http://site.test", transport=httpx.MockTransport(handle))
    result = reader.read(
        PageContext(type="draft", draft_ids=[4109, 2003], title="Solution draft"),
        "Check my draft",
        logged_in=True,
    )
    assert result["products"] == [
        {"product_id": 4109, "title": "SAJ HS2-5K-T2-X"},
        {"product_id": 2003, "title": "Pylontech OPTIM US L260-OMNI"},
    ]
    assert page.collect(result).product_ids == {4109, 2003}


def test_a_signed_in_account_is_not_read_anonymously() -> None:
    seen: list[str] = []
    result = _reader({}, seen).read(
        PageContext(type="account", url="/my-account/"), "Where is my Proforma?", True
    )
    assert seen == []
    assert "inquiry-status" in result["note"]
