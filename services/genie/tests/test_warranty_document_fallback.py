from __future__ import annotations

import pytest

from linker_genie.facts import Document, collect
from linker_genie.route import NamedModel, Route
from linker_genie.schema import DocumentBlock, Locale, TextBlock
from linker_genie.template import fallback, seal

MODEL = "GW50K-ET-10"


@pytest.mark.parametrize(
    ("lang", "question"),
    [
        (
            "en",
            f"How long is the standard European GoodWe manufacturer warranty on the {MODEL}, and when does that period begin?",
        ),
        (
            "de",
            f"Wie lange gilt die europäische Herstellergarantie für {MODEL}, und wann beginnt sie?",
        ),
    ],
)
@pytest.mark.parametrize("linked", [True, False])
def test_period_fallback_uses_only_the_named_models_current_policy(
    lang: Locale,
    question: str,
    linked: bool,
) -> None:
    pid = 1945
    documents = [
        {
            "type": "certificate",
            "lang": lang,
            "product_ids": [pid],
            "url": "https://site.test/iec.pdf",
        },
        *[
            {
                "type": "warranty",
                "lang": locale,
                "product_ids": [pid] if linked else [8978],
                "title": "GoodWe Limited Warranty"
                if locale == "en"
                else "GoodWe Garantie",
                "url": f"https://site.test/policy-{locale}.pdf",
                "document_id": f"policy-{locale}",
                "document_revision": "3.9",
            }
            for locale in ("en", "de")
        ],
    ]
    payload = {"product_id": pid, "model": MODEL, "documents": documents}
    facts = collect("linker/get-product", payload, lang, evidence_owner=pid)
    facts.tool_calls.append(
        {"name": "linker/get-product", "ok": True, "result": payload}
    )
    facts.documents["iec"] = Document("https://site.test/iec.pdf", "IEC", 1)
    facts.chunk_ids.add("iec")
    facts.technical_chunks.add("iec")
    route = Route("documents", named_models=(NamedModel(MODEL, (pid,)),))
    response = fallback(facts, lang, route, question=question)
    shipped = seal(response, facts, route, question, "other")
    blocks = [b for b in shipped.blocks if isinstance(b, DocumentBlock)]
    assert [b.url for b in blocks] == (
        [f"https://site.test/policy-{lang}.pdf"] if linked else []
    )
    if linked:
        evidence = facts.documents[blocks[0].ref].evidence
        assert evidence and (evidence.product_id, evidence.document_id) == (
            pid,
            f"policy-{lang}",
        )
    answer = " ".join(b.text for b in shipped.blocks if isinstance(b, TextBlock))
    assert MODEL in answer and ("period" if lang == "en" else "Garantiedauer") in answer
    assert all(s not in answer for s in ("5-year", "5 Jahre", "12", "IEC"))
