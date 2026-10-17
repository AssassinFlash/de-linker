"""A turn about the page the customer is on (#234): Jev decides, the route reads it.

The seam is the understanding layer (`Understander.prepare`) and the turn's checks
and hydration (`cycle.run`): what code fetches before the model when Jev says the
message is about the page, and that an answer citing the page passes and reads well.
"""

from collections.abc import Sequence
from typing import Any

import httpx

from linker_genie.abilities import AbilityClient
from linker_genie.agent import MAX_TOOL_CALLS, _user_prompt
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.page import PageUnavailable
from linker_genie.route import TURN_CALLS
from linker_genie.schema import PageContext, TextBlock, TurnOutput, TurnRequest
from linker_genie.understand import Understander

BLOG = {
    "type": "blog",
    "url": "http://127.0.0.1:9102/hybrid-inverter-vs-ac-coupled-storage/",
    "title": "How to Choose Between a Hybrid Inverter and an AC-Coupled Storage Setup",
    "post_id": 551,
}
PAGE_RESULT = {
    "type": "blog",
    "title": BLOG["title"],
    "url": "/hybrid-inverter-vs-ac-coupled-storage/",
    "outline": ["What is AC coupling?"],
    "text": "## What is AC coupling?\nAC coupling adds a battery inverter "
    "beside an existing [page.n1=5 kW] PV inverter.",
    "figures": {"page.n1": "5 kW"},
    "complete": True,
}


class Jev:
    def __init__(self, intent: str, about_page: float, confidence: float = 0.95):
        self.reading = Reading(intent, confidence, about_page, 0.02, 0.1, 2.6, 0.0)  # type: ignore[arg-type]
        self.pages: list[dict[str, Any]] = []

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        self.pages.append(page)
        return self.reading


class Pages:
    def __init__(self, result: dict[str, Any] | None = None, error: str | None = None):
        self.result, self.error = result, error
        self.reads: list[tuple[PageContext, str, bool]] = []

    def __call__(
        self, page: PageContext, question: str, logged_in: bool
    ) -> dict[str, Any]:
        self.reads.append((page, question, logged_in))
        if self.error:
            raise PageUnavailable(self.error)
        assert self.result is not None
        return self.result


def _abilities(seen: list[httpx.Request]) -> AbilityClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("check-compatibility/run"):
            return httpx.Response(
                200, json={"verdict": "released", "conditions": [], "documents": []}
            )
        return httpx.Response(200, json={"inquiries": []})

    return AbilityClient(
        "http://site.test", transport=httpx.MockTransport(handle), sleep=lambda s: None
    )


def _request(
    message: str, page: dict[str, Any], logged_in: bool = False, locale: str = "en"
) -> TurnRequest:
    return TurnRequest.model_validate(
        {
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": message}],
            "locale": locale,
            "page_context": page,
            "user": {"logged_in": logged_in},
        }
    )


def test_a_question_about_the_page_reads_it_before_the_model(
    vocabulary: Vocabulary,
) -> None:
    pages = Pages(PAGE_RESULT)
    jev = Jev("other", about_page=0.97)
    understander = Understander(lambda: vocabulary, jev, pages=pages)
    message = "What does this page mean by AC coupling?"
    prepared = understander.prepare(_request(message, BLOG), _abilities([]))
    # Jev reads the message against the page by its title.
    assert jev.pages[0] == {"type": "blog", "title": BLOG["title"]}
    assert [call.ability for call in prepared.route.calls] == ["linker/read-page"]
    assert pages.reads[0][1] == message
    assert prepared.results[0]["result"] == PAGE_RESULT
    assert prepared.facts.facts["page.n1"].value == "5 kW"
    assert prepared.route.no_handoff
    assert "about this page: blog" in prepared.route.reasons
    prompt = _user_prompt(_request(message, BLOG), None, prepared)
    assert "page=blog" in prompt
    assert "page_url=/hybrid-inverter-vs-ac-coupled-storage/" in prompt
    assert '"figures"' not in prompt  # the model reads the tagged text only


def test_a_message_not_about_the_page_does_not_read_it(vocabulary: Vocabulary) -> None:
    pages = Pages(PAGE_RESULT)
    understander = Understander(lambda: vocabulary, Jev("small_talk", 0.1), pages=pages)
    prepared = understander.prepare(_request("Thanks!", BLOG), _abilities([]))
    assert prepared.route.calls == ()
    assert pages.reads == []
    # The prompt still names the page, for the model to read it when it must.
    assert "page_title=How to Choose" in _user_prompt(
        _request("Thanks!", BLOG), None, prepared
    )


def test_this_one_on_a_product_page_is_the_page_product(vocabulary: Vocabulary) -> None:
    pages = Pages({**PAGE_RESULT, "type": "product"})
    understander = Understander(
        lambda: vocabulary, Jev("documents_specs", 0.98), pages=pages
    )
    product = {
        "type": "product",
        "product_id": 6528,
        "post_id": 6528,
        "url": "/product/goodwe-esa-gw10k-eha-g20/",
        "title": "GoodWe ESA GW10K-EHA-G20",
    }
    seen: list[httpx.Request] = []
    prepared = understander.prepare(
        _request("How many MPPTs does this one have?", product), _abilities(seen)
    )
    calls = [(c.ability, c.arguments) for c in prepared.route.calls]
    assert calls[0] == ("linker/read-page", {})
    assert ("linker/get-product", {"product_id": 6528, "lang": "en"}) in calls
    knowledge = next(args for name, args in calls if name == "linker/search-knowledge")
    assert knowledge["product_ids"] == [6528]
    assert len(calls) <= TURN_CALLS == MAX_TOOL_CALLS


def test_a_signed_in_account_page_is_its_inquiries(vocabulary: Vocabulary) -> None:
    pages = Pages(PAGE_RESULT)
    understander = Understander(lambda: vocabulary, Jev("other", 0.9), pages=pages)
    seen: list[httpx.Request] = []
    account = {"type": "account", "url": "/my-account/", "title": "My account"}
    prepared = understander.prepare(
        _request("What do the statuses on this page mean?", account, logged_in=True),
        _abilities(seen),
    )
    assert [c.ability for c in prepared.route.calls] == ["linker/inquiry-status"]
    assert pages.reads == []


def test_checking_the_draft_reads_its_products_and_their_pairings(
    vocabulary: Vocabulary,
) -> None:
    pages = Pages(
        {
            "type": "draft",
            "title": "Solution draft",
            "products": [
                {"product_id": 6528, "title": "GoodWe ESA GW10K-EHA-G20"},
                {"product_id": 6520, "title": "GoodWe GW8.3-BAT-D-G20"},
            ],
        }
    )
    # Jev unsure what "Check my draft" wants, sure that it is about the page.
    understander = Understander(
        lambda: vocabulary, Jev("other", 0.9, confidence=0.6), pages=pages
    )
    seen: list[httpx.Request] = []
    draft = {
        "type": "draft",
        "url": "/cart/",
        "title": "Solution draft",
        "draft_ids": [6528, 6520],
    }
    prepared = understander.prepare(
        _request("Check my draft", draft, logged_in=True), _abilities(seen)
    )
    calls = [(c.ability, c.arguments) for c in prepared.route.calls]
    assert calls == [
        ("linker/read-page", {}),
        ("linker/check-compatibility", {"inverter_id": 6528, "battery_id": 6520}),
    ]
    assert prepared.facts.product_ids >= {6528, 6520}


def test_a_page_that_cannot_be_read_is_logged_and_the_turn_goes_on(
    vocabulary: Vocabulary,
) -> None:
    pages = Pages(error="page /blog/x/ returned 500")
    understander = Understander(lambda: vocabulary, Jev("other", 0.9), pages=pages)
    prepared = understander.prepare(
        _request("What does this page say?", BLOG), _abilities([])
    )
    assert prepared.log["page_error"] == "page /blog/x/ returned 500"
    assert prepared.log["call_failures"] == [
        "linker/read-page: page /blog/x/ returned 500"
    ]
    assert prepared.results == []
    assert "could not be read" in prepared.route.hint


def test_asking_for_a_person_on_a_page_reads_nothing(vocabulary: Vocabulary) -> None:
    pages = Pages(PAGE_RESULT)
    understander = Understander(
        lambda: vocabulary, Jev("talk_to_person", 0.99), pages=pages
    )
    prepared = understander.prepare(
        _request("Can someone call me about this?", BLOG), _abilities([])
    )
    assert prepared.route.name == "person"
    assert pages.reads == []


def test_an_answer_from_the_page_is_grounded_and_hydrated(
    vocabulary: Vocabulary,
) -> None:
    pages = Pages(PAGE_RESULT)
    understander = Understander(lambda: vocabulary, Jev("other", 0.95), pages=pages)
    request = _request("What does this page mean by AC coupling?", BLOG)
    prepared = understander.prepare(request, _abilities([]))

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="The page means a battery inverter added beside an existing {fact:page.n1} PV inverter.",
                        refs=["page"],
                    )
                ],
            ),
            TurnFacts(),
        )

    result = run(request, generate, prepared.route, prepared.facts)
    assert result.grounded, result.failures
    block = result.output.blocks[0]
    assert isinstance(block, TextBlock)
    assert (
        block.text
        == "The page means a battery inverter added beside an existing 5 kW PV inverter."
    )


def test_a_page_figure_that_was_not_read_is_refused(vocabulary: Vocabulary) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("other", 0.95), pages=Pages(PAGE_RESULT)
    )
    request = _request("What does this page mean by AC coupling?", BLOG)
    prepared = understander.prepare(request, _abilities([]))

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text="It adds {fact:page.n9}.", refs=["page"])],
            ),
            TurnFacts(),
        )

    result = run(request, generate, prepared.route, prepared.facts)
    assert result.fallback
    assert any("page.n9" in failure for failure in result.failures)
