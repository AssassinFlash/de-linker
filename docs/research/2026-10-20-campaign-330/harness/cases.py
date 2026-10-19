"""The input-boundary battery of #330 (map #329): EN and DE sets per class.

Every case is pinned to the catalogue facts the c330 instance serves (snapshot
20261019-1409, feed of 106 products; ids below are that feed's product ids), so
hits and misses are judged against data, not vibes. `expect` is the machine
triage; the human grading reads every answer's own words before it stands.

Classes (ticket #330): misspelling, emoji, overlong, mixed-language,
case-variants (the 100% deterministic gate), brand-model-conflict, fake-model,
multi-product, units, contradiction, plus the parts-list boundaries the ticket
comment adds (xlsx DoS regression, empty sheet, duplicate rows, overlong rows).
"""

from __future__ import annotations

from typing import Any

# Catalogue facts (feed of snapshot 20261019-1409; see evidence/feed.json).
H2_10K = 4107  # SAJ H2-10K-T3, hybrid, three-phase, ac 10 kW
HS2_10K = 1182  # SAJ HS2-10K-T2-X, three-phase
GW10K_ETA = 3556  # GoodWe GW10K-ETA-G20, ESA, three-phase 10 kW
GW10K_EHA = 6528  # GoodWe GW10K-EHA-G20, ESA, single-phase 10 kW
GW5K_ETA = 6512  # three-phase 5 kW
GW5K_EHA = 6525  # single-phase 5 kW
GW3K_EHA = 6523
GW6K_EHA = 6526
GW8K_EHA = 6527
GW8K_ETA = 3583
GW25K_ETA = 6516
HS3_5K = 2198
HS3_8K = 1187
HS3_12K = 1185
B2_5 = 1832  # SAJ B2-5.0-HV1, usable 4.5 / nominal 5 kWh
B2_10 = 2067  # 9 / 10 kWh
B2_15 = 2068  # 13.5 / 15 kWh
BU3_5 = 2093  # SAJ BU3-5.0-TV2-PRO, 4.8 / 5 kWh
EF_P1_10K = 3579  # EcoFlow OCEAN 2 single-phase 10 kW
EF_P3_10K = 3555  # EcoFlow OCEAN 2 three-phase 10 kW
L260 = 2003  # Pylontech L260-OMNI
CHS2_29 = 1959  # SAJ CHS2-29.9K-T4-X, ac 29.999 kW (datasheet 29 999 W)

# The ESA 10 kW ambiguity of dossier §1.11/#10: EHA single-phase, ETA three-phase.
ESA_BOTH = (GW10K_EHA, GW10K_ETA)


def _long_model_list(count: int, with_quantity: bool = False) -> str:
    """A pasted list of real models, `count` lines, optionally with quantities."""
    models = [
        "GW3K-EHA-G20",
        "GW5K-EHA-G20",
        "GW6K-EHA-G20",
        "GW8K-EHA-G20",
        "GW10K-EHA-G20",
        "GW5K-ETA-G20",
        "GW8K-ETA-G20",
        "GW10K-ETA-G20",
        "H2-10K-T3",
        "H2-12K-T3",
        "HS2-5K-T2-X",
        "HS2-8K-T2-X",
        "B2-5.0-HV1",
        "B2-10.0-HV1",
        "BU3-5.0-TV2-PRO",
        "GM330",
    ]
    lines = []
    for index in range(count):
        model = models[index % len(models)]
        lines.append(f"{index + 1}. {model} x 2" if with_quantity else model)
    return "\n".join(lines)


CASES: list[dict[str, Any]] = [
    # -- A. Misspelling / fuzzy spelling ------------------------------------
    # Pass: the real product still surfaces (model-driven search) or Genie asks
    # one decisive question; Defect: silence about the product, wrong product
    # presented as the answer, or specs/availability stated for the misspelled
    # form.
    {
        "id": "A1-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "Do you have the SAJ H2-1OK-T3? Letter O, I never know.",
        "expect": {"any_ids": [H2_10K], "intended": "H2-10K-T3"},
    },
    {
        "id": "A2-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "Is the Goodwe GW1OK-ETA-G20 three-phase?",
        "expect": {"any_ids": [GW10K_ETA], "intended": "GW10K-ETA-G20"},
    },
    {
        "id": "A3-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "Looking for Ecoflow Ocean two batteries, the BD-8 one.",
        "expect": {"any_ids": [3582], "intended": "EF BD-8-S2"},
    },
    {
        "id": "A4-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "what is the output of the GooodWe GW5K-ETA-G2O?",
        "expect": {"any_ids": [GW5K_ETA], "intended": "GW5K-ETA-G20"},
    },
    {
        "id": "A5-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "hybrid inverter SAJJ HS3 1OK T2 W/G PX - do you carry it?",
        "expect": {
            "any_ids": [HS3_5K, HS3_8K, HS3_12K, 1186, 2199],
            "intended": "HS3-10K-T2-W/G-PX",
        },
    },
    {
        "id": "A1-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Haben Sie den SAJ H2-1OK-T3? Ich meine das Buchstaben-O.",
        "expect": {"any_ids": [H2_10K], "intended": "H2-10K-T3"},
    },
    {
        "id": "A2-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Ist der Goodwe GW1OK-ETA-G20 dreiphasig?",
        "expect": {"any_ids": [GW10K_ETA], "intended": "GW10K-ETA-G20"},
    },
    {
        "id": "A3-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Ich suche die Pylontech L26O-OMNI, mit Buchstabe O geschrieben.",
        "expect": {"any_ids": [L260], "intended": "L260-OMNI"},
    },
    {
        "id": "A4-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Welche Kapazität hat die Bu3-5.0-TV2-Pro Batterie?",
        "expect": {"any_ids": [BU3_5], "intended": "BU3-5.0-TV2-PRO"},
    },
    {
        "id": "A5-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Gibt es den Hybridwechselrichter H2 15 K T3 von Saj?",
        "expect": {"any_ids": [2063], "intended": "H2-15K-T3"},
    },
    # SKU-tail and category-word misspellings. The graded 2026-10-19 run did
    # not include these; they are in the battery for the next run. The fake
    # model further down uses an NEX- prefix so an invented code is not a
    # shop-prefixed SKU (the old-regime scan).
    {
        "id": "A6-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "The carton is printed GW5KETAG2O. Do you have that sku?",
        "expect": {"any_ids": [GW5K_ETA], "intended": "GW5KETAG20"},
    },
    {
        "id": "A6-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Auf dem Karton steht GW5KETAG2O. Führen Sie diese Nummer?",
        "expect": {"any_ids": [GW5K_ETA], "intended": "GW5KETAG20"},
    },
    {
        "id": "A7-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "Show me your hybird inverers around 10 kW.",
        "expect": {
            "any_ids": [H2_10K, GW10K_ETA, GW10K_EHA, HS2_10K],
            "intended": "hybrid inverters",
        },
    },
    {
        "id": "A7-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Zeigen Sie mir Hybridwechselrichterr um die 10 kW.",
        "expect": {
            "any_ids": [H2_10K, GW10K_ETA, GW10K_EHA, HS2_10K],
            "intended": "Hybridwechselrichter",
        },
    },
    # Series misspelling. ESA written as EZA. A real 5 kW hybrid from that
    # series still found, or one decisive follow-up, is a pass. Treating
    # "EZA" as its own series with invented specs is a defect.
    {
        "id": "A8-EN",
        "class": "misspelling",
        "lang": "en",
        "request": "Do you stock the GoodWe EZA series, the 5 kW hybrid?",
        "expect": {"any_ids": [GW5K_ETA], "intended": "ESA"},
    },
    {
        "id": "A8-DE",
        "class": "misspelling",
        "lang": "de",
        "request": "Führen Sie die GoodWe-Serie EZA, den 5-kW-Hybrid?",
        "expect": {"any_ids": [GW5K_ETA], "intended": "ESA"},
    },
    # -- B. Emoji ------------------------------------------------------------
    # Pure emoji: a short, in-language answer that asks what is needed. Emoji
    # mixed into a real question: the question is still answered (product hit).
    {
        "id": "B1-EN",
        "class": "emoji",
        "lang": "en",
        "request": "\U0001f50b⚡?",
        "expect": {"note": "battery emoji carries storage semantics; judge the shape"},
    },
    {
        "id": "B2-EN",
        "class": "emoji",
        "lang": "en",
        "request": "\U0001f525\U0001f525\U0001f525\U0001f44d",
        "expect": {"no_products": True},
    },
    {
        "id": "B3-EN",
        "class": "emoji",
        "lang": "en",
        "request": "Is the H2-10K-T3 in stock? \U0001f64f\U0001f64f",
        "expect": {"any_ids": [H2_10K]},
    },
    {
        "id": "B4-EN",
        "class": "emoji",
        "lang": "en",
        "request": "⚡ what is the AC output of the GW5K-ETA-G20? \U0001f4c1",
        "expect": {"any_ids": [GW5K_ETA]},
    },
    {
        "id": "B5-EN",
        "class": "emoji",
        "lang": "en",
        "request": "\U0001f50d ESA inverters \U0001f50d which ones do you have?",
        "expect": {"any_ids": list(ESA_BOTH)},
    },
    {
        "id": "B1-DE",
        "class": "emoji",
        "lang": "de",
        "request": "\U0001f50b⚡?",
        "expect": {"note": "battery emoji carries storage semantics; judge the shape"},
    },
    {
        "id": "B2-DE",
        "class": "emoji",
        "lang": "de",
        "request": "\U0001f44d\U0001f44d\U0001f605",
        "expect": {"no_products": True},
    },
    {
        "id": "B3-DE",
        "class": "emoji",
        "lang": "de",
        "request": "Ist der H2-10K-T3 auf Lager? \U0001f64f\U0001f64f",
        "expect": {"any_ids": [H2_10K]},
    },
    {
        "id": "B4-DE",
        "class": "emoji",
        "lang": "de",
        "request": "\U0001f527 Welche Nennleistung hat der HS2-10K-T2-X? \U0001f527",
        "expect": {"any_ids": [HS2_10K]},
    },
    {
        "id": "B5-DE",
        "class": "emoji",
        "lang": "de",
        "request": "\U0001f30a OCEAN 2 \U0001f30a dreiphasig 10 kW - welche Variante?",
        "expect": {"any_ids": [EF_P3_10K]},
    },
    # -- C. Overlong input (>4k characters) ----------------------------------
    # Pass: the turn completes without error, the answer addresses the list or
    # question actually asked; duration recorded. Defect: 4xx/5xx, cut-off or
    # ignored content, fabricated rows.
    {
        "id": "C1-EN",
        "class": "overlong",
        "lang": "en",
        "request": "Here is my equipment list:\n"
        + _long_model_list(220, True)
        + "\n\nWhich of these are single-phase inverters?",
        "expect": {"min_chars": 4000},
    },
    {
        "id": "C2-EN",
        "class": "overlong",
        "lang": "en",
        "request": ("What about the GW10K-ETA-G20? " * 160) + " Is it three-phase?",
        "expect": {"min_chars": 4000, "any_ids": [GW10K_ETA]},
    },
    {
        "id": "C3-EN",
        "class": "overlong",
        "lang": "en",
        "request": "H2-10K-T3 " + ("specifications" * 900),
        "expect": {"min_chars": 4000, "any_ids": [H2_10K]},
    },
    {
        "id": "C4-EN",
        "class": "overlong",
        "lang": "en",
        "request": ("Sorry for the long message. " * 300)
        + "Anyway: do you carry the B2-15.0-HV1?",
        "expect": {"min_chars": 4000, "any_ids": [B2_15]},
    },
    {
        "id": "C5-EN",
        "class": "overlong",
        "lang": "en",
        "request": "Parts list:\n" + _long_model_list(200, True) + "\n??? nonsense row",
        "expect": {"min_chars": 4000},
    },
    {
        "id": "C1-DE",
        "class": "overlong",
        "lang": "de",
        "request": "Meine Liste:\n"
        + _long_model_list(220, True)
        + "\n\nWelche davon sind einphasige Wechselrichter?",
        "expect": {"min_chars": 4000},
    },
    {
        "id": "C2-DE",
        "class": "overlong",
        "lang": "de",
        "request": ("Wie ist das beim GW10K-ETA-G20? " * 150) + " Ist er dreiphasig?",
        "expect": {"min_chars": 4000, "any_ids": [GW10K_ETA]},
    },
    {
        "id": "C3-DE",
        "class": "overlong",
        "lang": "de",
        "request": "Donaudampfschifffahrtsgesellschaftskapitän" * 110,
        "expect": {"min_chars": 4000},
    },
    {
        "id": "C4-DE",
        "class": "overlong",
        "lang": "de",
        "request": ("Entschuldigen Sie die lange Nachricht. " * 240)
        + "Haben Sie den B2-15.0-HV1?",
        "expect": {"min_chars": 4000, "any_ids": [B2_15]},
    },
    {
        "id": "C5-DE",
        "class": "overlong",
        "lang": "de",
        "request": "Stückliste:\n" + _long_model_list(200, True),
        "expect": {"min_chars": 4000},
    },
    # -- D. Mixed language ----------------------------------------------------
    # The contract is locale-driven (EN site answers English, DE site German);
    # pass = single-language answer in the locale's language, product facts
    # correct. Scrambled bilingual output or fact loss is the defect; the
    # locale-only language choice itself is logged as an observation.
    {
        "id": "D1-EN",
        "class": "mixed",
        "lang": "en",
        "request": "What is the Wirkungsgrad of the GW5K-ETA-G20 please?",
        "expect": {"any_ids": [GW5K_ETA]},
    },
    {
        "id": "D2-EN",
        "class": "mixed",
        "lang": "en",
        "request": "Do you have Wechselrichter from SAJ in the h2 series?",
        "expect": {"any_ids": [H2_10K, 4108, 2063, 2064, 1179, 1181]},
    },
    {
        "id": "D3-EN",
        "class": "mixed",
        "lang": "en",
        "request": "Welche Batterien sind mit dem H2-10K-T3 kompatibel?",
        "expect": {"any_ids": [B2_5, B2_10, B2_15]},
    },
    {
        "id": "D4-EN",
        "class": "mixed",
        "lang": "en",
        "request": "I need a Speicher for my 10 kWp roof, maybe Goodwe?",
        "expect": {},
    },
    {
        "id": "D5-EN",
        "class": "mixed",
        "lang": "en",
        "request": "Ich brauche an inverter that is dreiphasig, around 10 kW.",
        "expect": {},
    },
    {
        "id": "D1-DE",
        "class": "mixed",
        "lang": "de",
        "request": "Welche battery passt zum H2-10K-T3?",
        "expect": {"any_ids": [B2_5, B2_10, B2_15]},
    },
    {
        "id": "D2-DE",
        "class": "mixed",
        "lang": "de",
        "request": "Gibt es die GW5.1-BAT-D-G20 als single-phase Variante?",
        "expect": {"any_ids": [6519]},
    },
    {
        "id": "D3-DE",
        "class": "mixed",
        "lang": "de",
        "request": "Which batteries are compatible with the H2-10K-T3?",
        "expect": {"any_ids": [B2_5, B2_10, B2_15]},
    },
    {
        "id": "D4-DE",
        "class": "mixed",
        "lang": "de",
        "request": "Ich suche a hybrid inverter with 10 kW, dreiphasig.",
        "expect": {},
    },
    {
        "id": "D5-DE",
        "class": "mixed",
        "lang": "de",
        "request": "Was ist der efficiency vom HS2-10K-T2-X?",
        "expect": {"any_ids": [HS2_10K]},
    },
    # -- E. Case / hyphen / space variants (the 100% gate) --------------------
    # Correct product words in any casing, spacing or hyphenation MUST hit the
    # deterministic layer (lexicon normalize: lower case, alphanumerics only)
    # and show the product. Any miss is a defect against the map's gate.
    {
        "id": "E1-EN",
        "class": "case-variants",
        "lang": "en",
        "request": "is the gw10k eta g20 single-phase?",
        "expect": {"expect_ids": [GW10K_ETA]},
    },
    {
        "id": "E2-EN",
        "class": "case-variants",
        "lang": "en",
        "request": "Do you have Gw10k-Eta-G20 in stock?",
        "expect": {"expect_ids": [GW10K_ETA]},
    },
    {
        "id": "E3-EN",
        "class": "case-variants",
        "lang": "en",
        "request": "H210KT3 - what is the AC output?",
        "expect": {"expect_ids": [H2_10K]},
    },
    {
        "id": "E4-EN",
        "class": "case-variants",
        "lang": "en",
        "request": "h2 10k t3 availability please",
        "expect": {"expect_ids": [H2_10K]},
    },
    {
        "id": "E5-EN",
        "class": "case-variants",
        "lang": "en",
        "request": "Tell me about gw 5.1 bat d g20",
        "expect": {"expect_ids": [6519]},
    },
    {
        "id": "E6-EN",
        "class": "case-variants",
        "lang": "en",
        "request": "GOODWE inverters - which GOODWE models do you carry?",
        "expect": {},
    },
    {
        "id": "E1-DE",
        "class": "case-variants",
        "lang": "de",
        "request": "ist der gw10k eta g20 dreiphasig?",
        "expect": {"expect_ids": [GW10K_ETA]},
    },
    {
        "id": "E2-DE",
        "class": "case-variants",
        "lang": "de",
        "request": "H210KT3 - welche Nennleistung?",
        "expect": {"expect_ids": [H2_10K]},
    },
    {
        "id": "E3-DE",
        "class": "case-variants",
        "lang": "de",
        "request": "Haben Sie GW5,1-BAT-D-G20 auf Lager?",
        "expect": {"expect_ids": [6519]},
    },
    {
        "id": "E4-DE",
        "class": "case-variants",
        "lang": "de",
        "request": "saj hs2 5k t2 x verfügbar?",
        "expect": {"expect_ids": [4109]},
    },
    {
        "id": "E5-DE",
        "class": "case-variants",
        "lang": "de",
        "request": "Zeigen Sie mir GOODWE GW25K-ETA-G20",
        "expect": {"expect_ids": [GW25K_ETA]},
    },
    # -- F. Brand + model conflict --------------------------------------------
    # Pass: the mismatch is named and the right reading offered (the model under
    # its real brand, or the named brand's line); Defect: a hybrid product is
    # presented, or the wrong brand's product shown without a word about it.
    {
        "id": "F1-EN",
        "class": "brand-conflict",
        "lang": "en",
        "request": "Is the SAJ GW10K-ETA-G20 in stock?",
        "expect": {"any_ids": [GW10K_ETA]},
    },
    {
        "id": "F2-EN",
        "class": "brand-conflict",
        "lang": "en",
        "request": "Do you have the Trina Solar H2-10K-T3?",
        "expect": {"any_ids": [H2_10K]},
    },
    {
        "id": "F3-EN",
        "class": "brand-conflict",
        "lang": "en",
        "request": "GoodWe H2-15K-T3 - is that one of yours?",
        "expect": {"any_ids": [2063]},
    },
    {
        "id": "F4-EN",
        "class": "brand-conflict",
        "lang": "en",
        "request": "EcoFlow GW5K-ETA-G20 availability?",
        "expect": {"any_ids": [GW5K_ETA]},
    },
    {
        "id": "F5-EN",
        "class": "brand-conflict",
        "lang": "en",
        "request": "Does the SAJ B2-5.0-HV1 battery work with the GoodWe GW5K-ETA-G20 inverter?",
        "expect": {"any_ids": [B2_5, GW5K_ETA]},
    },
    {
        "id": "F1-DE",
        "class": "brand-conflict",
        "lang": "de",
        "request": "Haben Sie den SAJ GW10K-ETA-G20?",
        "expect": {"any_ids": [GW10K_ETA]},
    },
    {
        "id": "F2-DE",
        "class": "brand-conflict",
        "lang": "de",
        "request": "Gibt es den Trina Solar H2-10K-T3 bei Ihnen?",
        "expect": {"any_ids": [H2_10K]},
    },
    {
        "id": "F3-DE",
        "class": "brand-conflict",
        "lang": "de",
        "request": "Ist der GoodWe H2-15K-T3 von euch?",
        "expect": {"any_ids": [2063]},
    },
    {
        "id": "F4-DE",
        "class": "brand-conflict",
        "lang": "de",
        "request": "EcoFlow GW5K-ETA-G20 - lieferbar?",
        "expect": {"any_ids": [GW5K_ETA]},
    },
    {
        "id": "F5-DE",
        "class": "brand-conflict",
        "lang": "de",
        "request": "Passt die SAJ B2-5.0-HV1 Batterie zum GoodWe GW5K-ETA-G20 Wechselrichter?",
        "expect": {"any_ids": [B2_5, GW5K_ETA]},
    },
    # -- G. Plausible but non-existent models ---------------------------------
    # Pass: plainly not carried (no availability/specs for the fake code), best
    # with the nearest real alternative or a question; Defect: the fake product
    # is presented, or numbers are invented for it.
    {
        "id": "G1-EN",
        "class": "fake-model",
        "lang": "en",
        "request": "Do you have the GW50K-ETA-G20 in stock?",
        "expect": {"fake": "GW50K-ETA-G20"},
    },
    {
        "id": "G2-EN",
        "class": "fake-model",
        "lang": "en",
        "request": "Is the SAJ H2-35K-T3 available?",
        "expect": {"fake": "H2-35K-T3"},
    },
    {
        "id": "G3-EN",
        "class": "fake-model",
        "lang": "en",
        "request": "I need the SAJ R5-8K-T3 hybrid inverter, 8 kW.",
        "expect": {"fake": "R5-8K-T3"},
    },
    {
        "id": "G4-EN",
        "class": "fake-model",
        "lang": "en",
        "request": "Can you quote 20 pieces of NEX-SAJ-CHS2-75K-T8-X?",
        "expect": {"fake": "CHS2-75K-T8-X"},
    },
    {
        "id": "G5-EN",
        "class": "fake-model",
        "lang": "en",
        "request": "Do you carry the EcoFlow OCEAN 3 HD-P3-20K0-S2?",
        "expect": {"fake": "HD-P3-20K0-S2"},
    },
    {
        "id": "G1-DE",
        "class": "fake-model",
        "lang": "de",
        "request": "Haben Sie den GW50K-ETA-G20 auf Lager?",
        "expect": {"fake": "GW50K-ETA-G20"},
    },
    {
        "id": "G2-DE",
        "class": "fake-model",
        "lang": "de",
        "request": "Ist der SAJ H2-35K-T3 verfügbar?",
        "expect": {"fake": "H2-35K-T3"},
    },
    {
        "id": "G3-DE",
        "class": "fake-model",
        "lang": "de",
        "request": "Ich brauche den SAJ R5-8K-T3 Hybridwechselrichter mit 8 kW.",
        "expect": {"fake": "R5-8K-T3"},
    },
    {
        "id": "G4-DE",
        "class": "fake-model",
        "lang": "de",
        "request": "Können Sie 20 Stück NEX-SAJ-CHS2-75K-T8-X anbieten?",
        "expect": {"fake": "CHS2-75K-T8-X"},
    },
    {
        "id": "G5-DE",
        "class": "fake-model",
        "lang": "de",
        "request": "Führen Sie den EcoFlow OCEAN 3 HD-P3-20K0-S2?",
        "expect": {"fake": "HD-P3-20K0-S2"},
    },
    # -- H. Several products in one sentence (3+) ------------------------------
    # Pass: every named product is identified (cards cover them all, or the
    # answer says which ones it shows); Defect: products silently dropped.
    {
        "id": "H1-EN",
        "class": "multi-product",
        "lang": "en",
        "request": "Compare the H2-10K-T3, HS2-10K-T2-X and GW10K-ETA-G20 for me.",
        "expect": {"expect_ids": [H2_10K, HS2_10K, GW10K_ETA]},
    },
    {
        "id": "H2-EN",
        "class": "multi-product",
        "lang": "en",
        "request": "Are the GW5K-ETA-G20, GW6K-ETA-G20 and GW8K-ETA-G20 all three-phase?",
        "expect": {"expect_ids": [GW5K_ETA, 6513, GW8K_ETA]},
    },
    {
        "id": "H3-EN",
        "class": "multi-product",
        "lang": "en",
        "request": "Which of B2-5.0-HV1, B2-10.0-HV1 and B2-15.0-HV1 has the most usable kWh?",
        "expect": {"expect_ids": [B2_5, B2_10, B2_15]},
    },
    {
        "id": "H4-EN",
        "class": "multi-product",
        "lang": "en",
        "request": "Do you have HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX and HS3-12K-T2-W/G-PX in stock?",
        "expect": {"expect_ids": [HS3_5K, HS3_8K, HS3_12K]},
    },
    {
        "id": "H5-EN",
        "class": "multi-product",
        "lang": "en",
        "request": "Show me GW3K-EHA-G20, GW5K-EHA-G20, GW8K-EHA-G20, GW10K-EHA-G20 and GW8K-ETA-G20.",
        "expect": {"expect_ids": [GW3K_EHA, GW5K_EHA, GW8K_EHA, GW10K_EHA, GW8K_ETA]},
    },
    {
        "id": "H1-DE",
        "class": "multi-product",
        "lang": "de",
        "request": "Vergleichen Sie H2-10K-T3, HS2-10K-T2-X und GW10K-ETA-G20.",
        "expect": {"expect_ids": [H2_10K, HS2_10K, GW10K_ETA]},
    },
    {
        "id": "H2-DE",
        "class": "multi-product",
        "lang": "de",
        "request": "Sind GW5K-ETA-G20, GW6K-ETA-G20 und GW8K-ETA-G20 alle dreiphasig?",
        "expect": {"expect_ids": [GW5K_ETA, 6513, GW8K_ETA]},
    },
    {
        "id": "H3-DE",
        "class": "multi-product",
        "lang": "de",
        "request": "Welche von B2-5.0-HV1, B2-10.0-HV1 und B2-15.0-HV1 hat die meisten nutzbaren kWh?",
        "expect": {"expect_ids": [B2_5, B2_10, B2_15]},
    },
    {
        "id": "H4-DE",
        "class": "multi-product",
        "lang": "de",
        "request": "Haben Sie HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX und HS3-12K-T2-W/G-PX auf Lager?",
        "expect": {"expect_ids": [HS3_5K, HS3_8K, HS3_12K]},
    },
    {
        "id": "H5-DE",
        "class": "multi-product",
        "lang": "de",
        "request": "Zeigen Sie mir GW3K-EHA-G20, GW5K-EHA-G20, GW8K-EHA-G20, GW10K-EHA-G20 und GW8K-ETA-G20.",
        "expect": {"expect_ids": [GW3K_EHA, GW5K_EHA, GW8K_EHA, GW10K_EHA, GW8K_ETA]},
    },
    # -- I. Quantity / unit confusion (kW, kWh, kWp; phases; voltage) ----------
    # The unit-correct reading decides: an inverter's power is kW, a battery's
    # capacity kWh, PV arrays are kWp, annual consumption kWh/a. The sizing
    # prefill contract (dossier §1.12) is checked on open_configurator args.
    {
        "id": "I1-EN",
        "class": "units",
        "lang": "en",
        "request": "I need a 10 kWh inverter.",
        "expect": {},
    },
    {
        "id": "I2-EN",
        "class": "units",
        "lang": "en",
        "request": "Which battery gives me 10 kW of storage?",
        "expect": {},
    },
    {
        "id": "I3-EN",
        "class": "units",
        "lang": "en",
        "request": "I have 8 kWp on the roof and use 4000 kWh a year, three-phase.",
        "expect": {"sizing": {"pv_kwp": 8.0, "annual_load_kwh": 4000.0, "phase": 3}},
    },
    {
        "id": "I4-EN",
        "class": "units",
        "lang": "en",
        "request": "I need a single-phase 10 kW hybrid inverter.",
        "expect": {"any_ids": [GW10K_EHA, EF_P1_10K], "forbidden_ids": [H2_10K]},
    },
    {
        "id": "I5-EN",
        "class": "units",
        "lang": "en",
        "request": "My PV is 12 kWp and I want 15 kWh of battery storage.",
        "expect": {"sizing": {"pv_kwp": 12.0, "no_annual": True}},
    },
    {
        "id": "I6-EN",
        "class": "units",
        "lang": "en",
        "request": "Does the CHS2-29.9K-T4-X output 29.9 kW or 29.999 kW?",
        "expect": {"any_ids": [CHS2_29]},
    },
    {
        "id": "I1-DE",
        "class": "units",
        "lang": "de",
        "request": "Ich brauche einen 10-kWh-Wechselrichter.",
        "expect": {},
    },
    {
        "id": "I2-DE",
        "class": "units",
        "lang": "de",
        "request": "Welche Batterie liefert mir 10 kW Speicher?",
        "expect": {},
    },
    {
        "id": "I3-DE",
        "class": "units",
        "lang": "de",
        "request": "Ich habe 8 kWp auf dem Dach und verbrauche 4.000 kWh pro Jahr, dreiphasig.",
        "expect": {"sizing": {"pv_kwp": 8.0, "annual_load_kwh": 4000.0, "phase": 3}},
    },
    {
        "id": "I4-DE",
        "class": "units",
        "lang": "de",
        "request": "Ich brauche einen einphasigen 10-kW-Hybridwechselrichter.",
        "expect": {"any_ids": [GW10K_EHA, EF_P1_10K], "forbidden_ids": [H2_10K]},
    },
    {
        "id": "I5-DE",
        "class": "units",
        "lang": "de",
        "request": "Meine PV-Anlage hat 12 kWp und ich möchte 15 kWh Batteriespeicher.",
        "expect": {"sizing": {"pv_kwp": 12.0, "no_annual": True}},
    },
    {
        "id": "I6-DE",
        "class": "units",
        "lang": "de",
        "request": "Gibt der CHS2-29.9K-T4-X 29,9 kW oder 29,999 kW ab?",
        "expect": {"any_ids": [CHS2_29]},
    },
    # Voltage was named in the class and had no case. The pass rule is the
    # certificate figure (IEC 62109, ESA 5–30 kW, page 2: 3L/N/PE, 220/380,
    # 230/400 V), not a current-row index read as volts. Ungraded until the
    # next run; A4-EN is the recorded failure of this reading.
    {
        "id": "I7-EN",
        "class": "units",
        "lang": "en",
        "request": "What is the rated AC output voltage of the GW5K-ETA-G20?",
        "expect": {"any_ids": [GW5K_ETA]},
    },
    {
        "id": "I7-DE",
        "class": "units",
        "lang": "de",
        "request": "Welche AC-Nennspannung hat der GW5K-ETA-G20?",
        "expect": {"any_ids": [GW5K_ETA]},
    },
    # -- J. Contradictory conditions -------------------------------------------
    # Pass: the contradiction is named and one decisive question asked (or both
    # readings offered); Defect: one side silently ignored, or an impossible
    # product presented as the answer.
    {
        "id": "J1-EN",
        "class": "contradiction",
        "lang": "en",
        "request": "I need a single-phase and three-phase 10 kW inverter at the same time.",
        "expect": {},
    },
    {
        "id": "J2-EN",
        "class": "contradiction",
        "lang": "en",
        "request": "I want a 10 kW system but my roof only fits 1 kW of PV.",
        "expect": {},
    },
    {
        "id": "J3-EN",
        "class": "contradiction",
        "lang": "en",
        "request": "I want the GW10K-EHA-G20 but three-phase.",
        "expect": {},
    },
    {
        "id": "J4-EN",
        "class": "contradiction",
        "lang": "en",
        "request": "Please quote the three-phase GW5K-EHA-G20.",
        "expect": {},
    },
    {
        "id": "J5-EN",
        "class": "contradiction",
        "lang": "en",
        "request": "What is your smallest inverter with at least 30 kW?",
        "expect": {},
    },
    {
        "id": "J1-DE",
        "class": "contradiction",
        "lang": "de",
        "request": "Ich brauche einen einphasigen und dreiphasigen 10-kW-Wechselrichter gleichzeitig.",
        "expect": {},
    },
    {
        "id": "J2-DE",
        "class": "contradiction",
        "lang": "de",
        "request": "Ich möchte eine 10-kW-Anlage, aber auf mein Dach passen nur 1 kW PV.",
        "expect": {},
    },
    {
        "id": "J3-DE",
        "class": "contradiction",
        "lang": "de",
        "request": "Ich möchte den GW10K-EHA-G20, aber dreiphasig.",
        "expect": {},
    },
    {
        "id": "J4-DE",
        "class": "contradiction",
        "lang": "de",
        "request": "Bitte bieten Sie den dreiphasigen GW5K-EHA-G20 an.",
        "expect": {},
    },
    {
        "id": "J5-DE",
        "class": "contradiction",
        "lang": "de",
        "request": "Was ist Ihr kleinster Wechselrichter mit mindestens 30 kW?",
        "expect": {},
    },
]

# -- K. Parts-list boundaries (ticket comment: xlsx DoS regression, empty
# sheet, duplicate rows, overlong rows). Files are built by xlsxgen at run
# time; `file` names the builder. EN list message carries the file.
PARTS_CASES: list[dict[str, Any]] = [
    {
        "id": "K1-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Here is my parts list.",
        "file": "normal",
        "expect": {"parts_rows": 3, "parts_matched": 3},
    },
    {
        "id": "K2-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Please match this list.",
        "file": "empty",
        "expect": {"note": "no rows: graceful, no crash"},
    },
    {
        "id": "K3-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Here is my parts list.",
        "file": "duplicates",
        "expect": {"parts_rows": 3, "note": "duplicate rows handled"},
    },
    {
        "id": "K4-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Please match this list.",
        "file": "long_rows",
        "expect": {"note": "overlong row text truncated, no crash"},
    },
    {
        "id": "K5-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Here is my parts list.",
        "file": "many_rows",
        "expect": {"parts_truncated": True, "note": "250 rows cut at 200, declared"},
    },
    {
        "id": "K6-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Please match this list.",
        "file": "zip_bomb",
        "expect": {"note": "sheet entry over the 8 MiB ceiling refused gracefully"},
    },
    {
        "id": "K7-EN",
        "class": "parts-boundary",
        "lang": "en",
        "request": "Please match this list.",
        "file": "billion_laughs",
        "expect": {"note": "DOCTYPE/ENTITY refused gracefully"},
    },
    {
        "id": "K8-DE",
        "class": "parts-boundary",
        "lang": "de",
        "request": "Hier meine Stückliste.",
        "file": "normal_de",
        "expect": {"parts_rows": 3, "parts_matched": 3},
    },
]
