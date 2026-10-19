"""The page reader reads what the visitor's page shows (#234).

A save drops the cached page (#405); a page that was not saved stays cached.

The fixtures are the `<main>` of real pages of the live snapshot 2026-10-18
(eval/page/capture_pages.py): the FAQ page (longer than the reader's budget), a blog post,
the German residential storage page and a GoodWe ESA product page.
"""

import threading
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from conftest import SHELL
from fastapi.testclient import TestClient

from linker_genie import app as genie_app
from linker_genie import page
from linker_genie.page import PAGE_CHARS, PageReader, PageUnavailable
from linker_genie.schema import PageContext, PageInvalidate

PAGES = Path(__file__).resolve().parent / "fixtures" / "pages"


def _html(name: str) -> str:
    return (PAGES / name).read_text(encoding="utf-8")


def _ok(text: str) -> httpx.Response:
    """A page as WordPress serves it."""
    return httpx.Response(
        200, text=text, headers={"content-type": "text/html; charset=UTF-8"}
    )


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
    reader = _reader({"/faq-download/": _ok(_html("faq-en.html"))})
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
    reader = _reader({path: _ok(_html("blog-post-en.html"))})
    result = reader.read(
        PageContext(type="blog", url="http://site.test" + path, post_id=551),
        "Summarise this post",
        logged_in=False,
    )
    assert result["complete"] is True
    assert "## What is a hybrid inverter?" in result["text"]


def test_figures_of_the_page_are_tagged_and_become_facts() -> None:
    path = "/de/loesung/heimspeicher/"
    reader = _reader({path: _ok(_html("solution-de.html"))})
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
    reader = _reader({path: _ok(_html("product-en.html"))})
    result = reader.read(
        PageContext(type="product", url=path, product_id=6528, post_id=6528),
        "What does this page mean by internal bypass?",
        logged_in=False,
    )
    assert "internal bypass" in result["text"]
    assert "## Product questions" in result["text"]


def test_only_the_path_of_the_address_is_read_on_the_served_site() -> None:
    seen: list[str] = []
    reader = _reader({"/blog/": _ok("<main><p>Latest posts</p></main>")}, seen)
    result = reader.read(
        PageContext(type="blog", url="https://elsewhere.example/blog/?x=1"),
        "what is here",
        logged_in=False,
    )
    # The blog index is a listing: its query stays, on the served site.
    assert seen == ["http://site.test/blog/?x=1"]
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
            "/de/loesung/": _ok("<main><p>Anwendung</p></main>"),
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


def test_saving_one_page_drops_it_and_leaves_the_other_cached() -> None:
    seen: list[str] = []
    pages = {
        "/product/a/": "<main><h1>Alpha</h1></main>",
        "/blog/b/": "<main><h1>Beta</h1></main>",
        "/de/produkt/a/": "<main><h1>Alpha DE</h1></main>",
    }

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return _ok(pages[request.url.path])

    reader = PageReader("http://site.test", transport=httpx.MockTransport(handle))
    product = PageContext(type="product", url="/product/a/", post_id=4107)
    post = PageContext(type="blog", url="/blog/b/", post_id=551)
    german = PageContext(type="product", url="/de/produkt/a/", post_id=8200)
    reader.read(product, "q", False)
    reader.read(post, "q", False)
    reader.read(german, "q", False)
    assert reader.invalidate(["/product/a", "/de/produkt/a/"]) == 2
    pages["/product/a/"] = "<main><h1>Alpha C405</h1></main>"
    pages["/de/produkt/a/"] = "<main><h1>Alpha DE C405</h1></main>"
    assert "Alpha C405" in reader.read(product, "q", False)["text"]
    assert "Alpha DE C405" in reader.read(german, "q", False)["text"]
    assert reader.read(post, "q", False)["text"] == "## Beta"
    # The blog post was not saved, so it was not fetched again.
    assert seen.count("/blog/b/") == 1
    assert seen.count("/product/a/") == 2
    assert seen.count("/de/produkt/a/") == 2


def test_a_read_in_flight_during_a_save_does_not_store_the_old_page() -> None:
    started = threading.Event()
    release = threading.Event()
    bodies = {"/edited/": "<main><p>OLD</p></main>"}
    seen: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        # The body is taken before the wait: the save changes the page while
        # this fetch is still open, and the fetch must return the page it started.
        if request.url.path == "/edited/" and not started.is_set():
            body = bodies[request.url.path]
            started.set()
            assert release.wait(2)
            return _ok(body)
        return _ok(bodies[request.url.path])

    reader = PageReader("http://site.test", transport=httpx.MockTransport(handle))
    context = PageContext(type="blog", url="/edited/", post_id=551)
    found: list[str] = []

    def read() -> None:
        found.append(reader.read(context, "q", False)["text"])

    thread = threading.Thread(target=read)
    thread.start()
    assert started.wait(2)
    assert reader.invalidate(["/edited/"]) == 0
    bodies["/edited/"] = "<main><p>NEW</p></main>"
    release.set()
    thread.join(2)
    assert not thread.is_alive()
    assert found == ["OLD"]
    assert reader.read(context, "q", False)["text"] == "NEW"
    assert seen.count("/edited/") == 2


def test_an_address_that_is_not_a_page_is_not_a_cache_key() -> None:
    reader = _reader({"/": _ok("<main><p>Home</p></main>")})
    reader.read(PageContext(type="home", url="/"), "q", False)
    assert reader.invalidate(["/wp-admin/", "", "not a path"]) == 0
    assert reader.invalidate(["/"]) == 1


def test_the_service_drops_a_cached_page_for_the_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []
    pages = {"/product/a/": "<main><h1>Alpha</h1></main>"}

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return _ok(pages[request.url.path])

    reader = PageReader("http://site.test", transport=httpx.MockTransport(handle))
    monkeypatch.setattr(genie_app, "_pages", reader)
    context = PageContext(type="product", url="/product/a/", post_id=4107)
    reader.read(context, "q", False)
    client = TestClient(genie_app.app, headers=SHELL)
    response = client.post("/pages/invalidate", json={"paths": ["/product/a/"]})
    assert response.status_code == 200
    assert response.json() == {"forgotten": 1}
    pages["/product/a/"] = "<main><h1>Alpha C405</h1></main>"
    assert "Alpha C405" in reader.read(context, "q", False)["text"]
    assert seen.count("/product/a/") == 2
    denied = TestClient(genie_app.app).post(
        "/pages/invalidate", json={"paths": ["/product/a/"]}
    )
    assert denied.status_code == 401
    empty = client.post("/pages/invalidate", json={"paths": []})
    assert empty.status_code == 422
    assert PageInvalidate.model_json_schema()["properties"]["paths"]["maxItems"] == (
        page.INVALIDATE_LIMIT
    )


def test_a_page_is_read_once_within_the_cache_time() -> None:
    seen: list[str] = []
    now = [0.0]
    reader = PageReader(
        "http://site.test",
        transport=_site({"/": _ok("<main><p>Home</p></main>")}, seen),
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


# Round 1 of the review of PR #295: fetch safety, prices and delivery, the query.


def _streamed(
    chunks: list[bytes], sent: list[int], content_type: str
) -> httpx.Response:
    def body() -> Iterator[bytes]:
        for chunk in chunks:
            sent.append(len(chunk))
            yield chunk

    return httpx.Response(200, headers={"content-type": content_type}, content=body())


@pytest.mark.parametrize(
    "url",
    [
        "/wp-content/uploads/2026/10/GW_ESA-3-10kW_Datasheet_EMEA-EN_V1.1.pdf",
        "/wp-content/themes/x/",
        "/xmlrpc.php",
        "/product/saj-h2-10k-t3/datasheet.pdf",
        "/sitemap.xml",
    ],
)
def test_a_file_or_a_system_path_is_never_requested(url: str) -> None:
    seen: list[str] = []
    with pytest.raises(PageUnavailable):
        _reader({}, seen).read(PageContext(type="other", url=url), "q", False)
    assert seen == []


def test_a_body_over_the_byte_cap_is_refused_without_reading_it_all() -> None:
    sent: list[int] = []
    chunk = b"<main><p>" + b"x" * (64 * 1024) + b"</p></main>"
    count = page.MAX_PAGE_BYTES // len(chunk) + 50
    reader = _reader({"/big/": _streamed([chunk] * count, sent, "text/html")})
    with pytest.raises(PageUnavailable, match="larger than"):
        reader.read(PageContext(type="other", url="/big/"), "q", False)
    assert len(sent) < count


def test_a_page_that_is_not_html_is_refused_without_reading_it() -> None:
    sent: list[int] = []
    reader = _reader({"/doc/": _streamed([b"%PDF-1.7"] * 10, sent, "application/pdf")})
    with pytest.raises(PageUnavailable, match="not HTML"):
        reader.read(PageContext(type="other", url="/doc/"), "q", False)
    assert len(sent) <= 1


def test_every_read_is_anonymous_a_cookie_is_never_sent_back() -> None:
    cookies: list[str | None] = []

    def handle(request: httpx.Request) -> httpx.Response:
        cookies.append(request.headers.get("cookie"))
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html",
                "set-cookie": "wp_woocommerce_session=abc; Path=/",
            },
            text="<main><p>Page</p></main>",
        )

    reader = PageReader("http://site.test", transport=httpx.MockTransport(handle))
    reader.read(PageContext(type="other", url="/a/"), "q", False)
    reader.read(PageContext(type="other", url="/b/"), "q", False)
    assert cookies == [None, None]


@pytest.mark.parametrize(
    "location",
    ["https://site.test/x/", "http://site.test:8080/x/", "http://evil.test/x/"],
)
def test_a_redirect_must_keep_scheme_host_and_port(location: str) -> None:
    reader = _reader({"/a/": httpx.Response(301, headers={"location": location})})
    with pytest.raises(PageUnavailable, match="off the site"):
        reader.read(PageContext(type="other", url="/a/"), "q", False)


def test_a_listing_keeps_its_query_and_a_single_page_drops_it() -> None:
    seen: list[str] = []
    html = _ok("<main><p>Listing</p></main>")
    reader = _reader({"/product-category/inverters/": html, "/blog/x/": html}, seen)
    reader.read(
        PageContext(
            type="category",
            url="/product-category/inverters/?filter_brand=saj",
            category_id=449,
        ),
        "q",
        False,
    )
    reader.read(
        PageContext(type="blog", url="/blog/x/?utm_source=mail", post_id=5), "q", False
    )
    assert seen == [
        "http://site.test/product-category/inverters/?filter_brand=saj",
        "http://site.test/blog/x/",
    ]


def test_prices_and_delivery_estimates_never_come_from_the_page() -> None:
    path = "/product/goodwe-esa-gw10k-eha-g20/"
    reader = _reader({path: _ok(_html("product-en.html"))})
    result = reader.read(
        PageContext(type="product", url=path, product_id=6528, post_id=6528),
        "What does this page say about the price and delivery?",
        logged_in=False,
    )
    text = result["text"]
    for gone in ("Net price", "partner pricing", "delivery estimate", "€", "39.00"):
        assert gone not in text, gone
    assert "internal bypass" in text
    assert "In stock" in text


def test_a_sentence_about_prices_stays_only_a_price_gate_goes() -> None:
    html = (
        "<main><h2>Sign in</h2><p>Your inquiries, documents and prices in one place.</p>"
        "<a>Sign in for partner pricing</a><a>Für Partnerpreise anmelden</a>"
        "<p>Nettopreis nach Partner-Anmeldung</p></main>"
    )
    assert page.render(page.passages(html)) == (
        "## Sign in\nYour inquiries, documents and prices in one place."
    )
