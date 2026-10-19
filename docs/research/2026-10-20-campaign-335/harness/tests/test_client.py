"""Page parsing. The live Polylang tag puts href before hreflang."""

from __future__ import annotations

import client


def test_german_alternate_accepts_the_live_attribute_order() -> None:
    live = (
        '<link rel="alternate" href="http://127.0.0.1:9190/de/" hreflang="de" />'
        '<link rel="alternate" href="http://127.0.0.1:9190/" hreflang="en" />'
    )
    assert client.german_alternate(live) == "http://127.0.0.1:9190/de/"
    href_last = '<link rel="alternate" hreflang="de" href="http://127.0.0.1:9190/de/">'
    assert client.german_alternate(href_last) == "http://127.0.0.1:9190/de/"
    assert client.mount(live)["de_url"] == "http://127.0.0.1:9190/de/"


def test_german_alternate_ignores_other_languages() -> None:
    html = '<link rel="alternate" href="http://127.0.0.1:9190/" hreflang="en" />'
    assert client.german_alternate(html) is None
