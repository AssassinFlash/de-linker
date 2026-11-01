"""Certificate-only model evidence, replayed against the current Woo relations.

A declaration can list exact models or a finite placeholder enumeration. Its
model axis is evidence of the certificate's subject, never of technical ratings.
Only a small certificate-context fragment is returned to the retrieval layer.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

from linker_genie.source_models import model_pattern
from linker_genie.table_projection import cell_at, cells_digest, read_cells

# These labels are document roles, not manufacturer's model families.
_CERTIFICATE = frozenset({"certificate", "zertifikat"})
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]{1,100}(?: [A-Za-z0-9./-]{1,40})?\Z")
_AXIS = re.compile(
    r"\b(?:(?:type\s+designation|bezeichnung\s+designation)"
    r"(?:\s*:\s*|\s+)|(?:model(?:l|le|s)?(?:\s*/\s*type)?|product|produkt)\s*:)",
    re.IGNORECASE,
)
_END_AXIS = re.compile(
    r"\b(?:firmware\s+version|vmax|isc\s+pv|rated\s+output|"
    r"input\s+current|mpp\s+voltage|overvoltage\s+category|serial\s+number|remark)\b",
    re.IGNORECASE,
)
_REJECT = re.compile(
    r"\b(?:not\s+(?:applicable|valid|covered|certified|listed|included)|"
    r"does\s+not\s+(?:apply\s+to|cover|include)|exclud(?:e|ed|es|ing)(?:\s+models?)?|"
    r"except\s+for|nicht\s+(?:gültig|anwendbar|zertifiziert|enthalten|abgedeckt|aufgeführt)|(?:gilt|gelten)\s+nicht\s+für|"
    r"ausgeschlossen\w*|ausgenommen\w*)\b",
    re.IGNORECASE,
)
# The finite list, not an estimated range or another family's rating, supplies
# the substitution. A period is required for decimals; commas separate values.
_FINITE_AXIS = re.compile(
    r"(?<![\w./-])(?P<prefix>[A-Za-z][A-Za-z0-9./-]*?)xx"
    r"(?P<suffix>[A-Za-z0-9./-]+)\s*,?\s*\(\s*xx\s*=\s*"
    r"(?P<values>\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*)\s*\)",
    re.IGNORECASE,
)
_SHARED_TEMPLATE = re.compile(
    r"(?<![\w./-])(?P<prefix>[A-Za-z][A-Za-z0-9./-]*?)"
    r"(?P<variable>xx|yy)(?P<suffix>[A-Za-z0-9./-]+)(?![\w./-])",
    re.IGNORECASE,
)
_SHARED_VALUES = re.compile(
    r"\(\s*(?P<variable>xx|yy)\s*=\s*"
    r"(?P<values>\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*\s*,?)\s*\)",
    re.IGNORECASE,
)
_AXIS_MODEL = re.compile(
    r"(?<![\w./-])[A-Za-z][A-Za-z0-9./-]*\d[A-Za-z0-9./-]*(?![\w/-]|\.(?=\w))"
)
_AXIS_DESCRIPTION = re.compile(
    r"\b(?:hybrid\s+inverter|hybrid-wechselrichter)\b", re.IGNORECASE
)
_CONTEXT = re.compile(
    r"the\s+certificate\s+of\s+conformity\s+refers\s+to\s+the\s+above\s+mentioned\s+product\."
    r"|certificate\s+no\.?\s*:\s*[A-Z]\s*\d+(?:\s+\d+)?"
    r"|declare\s+under\s+our\s+sole\s+responsibility\s+that\s+the\s+products\s+referred\s+to\s+below"
    r"|erklärt\s+hiermit\s+in\s+alleiniger\s+verantwortung,\s+dass\s+die\s+nachstehend\s+genannten\s+produkte",
    re.IGNORECASE,
)
_CONFORMITY = re.compile(
    r"are\s+in\s+conformity\s+with\s+the\s+union\s+harmonisation\s+legislation\."
    r"|die\s+einschlägige\s+harmonisierungsrechtsvorschriften\s+erfüllen\.",
    re.IGNORECASE,
)
_SPECIMEN_CONFORMITY = re.compile(
    r"This is to certify that the specimen is in conformity with the assessment "
    r"requirement mentioned above\.",
    re.IGNORECASE,
)
_PAIRED_DECLARATION = re.compile(
    r"We declare under our own responsibility that the product:", re.IGNORECASE
)
_PAIRED_DIRECTIVES = re.compile(
    r"(?P<intro>observe the following directives and regulations:)\s*\n"
    r"(?P<lines>[\s\S]+?)\nThe following criteria shall be used to assess compliance",
    re.IGNORECASE,
)
_PAIRED_DIRECTIVE_LINE = re.compile(
    r"\s*●?\s*(?:Directive\s+(?:\(EU\)\s*)?"
    r"|Commission\s+Regulation\s+\(EU\)\s*)?"
    r"\d{4}/\d{1,4}(?:/EU)?(?:\s*\([A-Za-z ]+\))?\s*",
    re.IGNORECASE,
)
_PAIRED_MODEL_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]*[A-Za-z0-9]")
_PAIRED_AXIS_LABEL = re.compile(
    r"\b(?:Battery system|Automatic Transfer Switch|Hybrid Solar Inverter|"
    r"Single phase inverter:|Three-phase inverter:|Battery:)(?!\w)",
    re.IGNORECASE,
)
_PAIRED_MODULE_NOTE = re.compile(
    r"\(X\s*=\s*\d+(?:\s*,\s*\d+)+\s*\(Number of Modules\)\)",
    re.IGNORECASE,
)
_GOODWE_DECLARATION = re.compile(
    r"declare under our sole responsibility that the products referred to below\s*,",
    re.IGNORECASE,
)
_GOODWE_CLAIM = re.compile(
    r"are in conformity with the following Union harmonisation legislation and directives:"
    r"|comply with the following directives and regulations,",
    re.IGNORECASE,
)
_GOODWE_DIRECTIVE = re.compile(
    r"\s*[\uf0b7●]?\s*(?:Low\s*Voltage Directive 2014/35/EU \(LVD\)"
    r"|Electrical Apparatus Low Voltage Directive 2014/35/EU \(LVD\)"
    r"|Electromagnetic compatibility Directive 2014/30/EU \(EMC\))\s*",
    re.IGNORECASE,
)
_CB_CLAIM = re.compile(
    r"A sample of the product was tested and found to be in conformity with",
    re.IGNORECASE,
)
_CB_ISSUER = re.compile(
    r"This CB Test Certificate is issued by the National Certification Body",
    re.IGNORECASE,
)
_CB_AXIS = re.compile(
    r"forms part of this Certificate\s*\n(?P<models>[^\n]+)\nSee additional page\(s\)"
    r"|(?m:^N/A\s*\n(?P<plain_models>[^\n]+)\nRe-issue of)",
    re.IGNORECASE,
)
_ATTESTATION_MODELS = re.compile(
    r"(?m)^Models(?:[ \t]+|\nIssued to[ \t]+)(?P<models>[^\n]+)$"
)
_ATTESTATION_CLAIM = re.compile(
    r"The product has been evaluated according to the ETSI TS 103 701 v1\.1\.1 and "
    r"found in conformity to the ETSI EN 303 645 v2\.1\.1 standard\.",
    re.IGNORECASE,
)
_ATTESTATION_ANNEX = re.compile(
    r"See annex for list of models and provisions details\.", re.IGNORECASE
)
_ATTESTATION_LIMIT = re.compile(
    r"Information given in this document, are related to\s+the tested specimen "
    r"of the described electrical sample\.",
    re.IGNORECASE,
)
_UNIT_CLAIM = re.compile(
    r"The power generating unit mentioned above meets the requirements of the application guide listed above\.",
    re.IGNORECASE,
)
_UNIT_LIMIT = re.compile(
    r"The certified product does not provide test terminal\. A connecting terminal plate has to be installed separately, if necessary\.",
    re.IGNORECASE,
)
_UNIT_4110 = re.compile(r"VDE-AR-N 4110:\s*2023-09\+Corr\.1:\s*2024-11", re.IGNORECASE)
_UNIT_4120 = re.compile(
    r"VDE-AR-N 4120:\s*2018-11\+Corr\.1:\s*2020-10\+A1:\s*2024-04", re.IGNORECASE
)
_UNIT_4130 = re.compile(r"VDE-AR-N 4130:\s*2018-11\+Corr\.1:\s*2020-10", re.IGNORECASE)
_UNIT_NUMBER = re.compile(r"No\.\s*\d{6,}RECO\d+-CER", re.IGNORECASE)
_TUV_CERTIFICATE = re.compile(r"Certificate No\.:\s*(R\s*\d{8}\s+\d{4})", re.IGNORECASE)
_TUV_AXIS = re.compile(
    r"Type Designation\s+Berichtsnummer Report No\.:\s*CN[A-Z0-9]+\s+\d+\s*:\s*"
    r"(?P<models>[\s\S]+?)\s*Input Voltage Range",
    re.IGNORECASE,
)
_TUV_CLAIM = re.compile(
    r"This certificate is based on our Testing and Certification Regulation and states the conformity of the product with the standards and testing requirements as indicated above\."
    r"\s*Any additional requirements in countries where the product is going to be marketed have to be considered additionally\."
    r"\s*The manufacturing of the certified product is subject to surveillance\.",
    re.IGNORECASE,
)
_LIMITATION = re.compile(
    r"this\s+certificate\s+does\s+not\s+imply\s+assessment\s+of\s+the\s+(?:series-)?production\s+of\s+the\s+product\s+and\s+does\s+not\s+permit\s+the\s+use\s+of\s+a\s+TÜV\s+Rheinland\s+mark\s+of\s+conformity\.",
    re.IGNORECASE,
)
_CERTIFICATE_NUMBER = re.compile(
    r"\bcertificate\s+(?:number|no\.?)\s*:\s*[A-Z0-9][A-Z0-9./-]{1,40}\b",
    re.IGNORECASE,
)
_REGISTRATION = re.compile(
    r"\bRegistration\s+No\.\s*:\s*"
    r"(?:(?:Product|Identification|Report\s+No\.|Tested\s+according\s+to)\s*:\s*)*"
    r"(?P<number>A[KN]\s+\d{8}\s+\d{4})\b",
    re.IGNORECASE,
)
_LOW_VOLTAGE_CLAIM = re.compile(
    r"This is to certify that the tested sample is in conformity with Annex I of Council Directive "
    r"(?:\(EU\) \d{4}/\d{2}|\d{4}/\d{2}/EU), referred to as the Low Voltage Directive\.",
    re.IGNORECASE,
)
_GENERIC_LVD_HEADING = re.compile(
    r"of\s+conformity\s+low\s+voltage\s+directive\s+\d{4}/\d{2}/EU",
    re.IGNORECASE,
)
_SEE_CERTIFICATE = re.compile(
    r"\bmodel\s+designation\s*:\s*see\s+certificate\b", re.IGNORECASE
)
_REPORT_NUMBER = re.compile(
    r"\breport\s+no\.\s*:\s*(CN[A-Z0-9]{4,12}\s+\d{3})\b", re.IGNORECASE
)
_RED_NUMBER = re.compile(r"\bN°\s*:\s*(RED_\d{1,8})\b", re.IGNORECASE)
_SPLIT_DECLARATION = re.compile(
    r"(?P<declaration>Declare under our own responsibility that the product:"
    r"|Wir erklären in eigener Verantwortung, dass das Produkt:)"
    r"[\s\S]{0,160}(?:Model|Modell):\s*\Z",
    re.IGNORECASE,
)
_LCIE_CLAIM = re.compile(
    r"Le LCIE déclare que le produit susmentionné respecte les exigences essentielles indiquées ci-après"
    r"\s*/\s*LCIE declares that, the listed product complies with the essential requirements listed below:",
    re.IGNORECASE,
)
_LCIE_LIMITATION = re.compile(
    r"The validity of the present certificate is limited to the mentioned product subject of this evaluation"
    r" and will be questioned at the slightest modification of the product concerned\."
    r" Any development of Directive 2014/53/UE of 16 April 2014 is also likely to question its validity",
    re.IGNORECASE,
)
_NARROWING = re.compile(
    r"\b(?:only|solely|exclusively|nur|ausschließlich)\b", re.IGNORECASE
)
_STANDARD_CODE = (
    r"(?:EN(?:\s+IEC)?|IEC|VDE(?:-AR-N)?|DIN(?:\s+VDE(?:\s+V)?)?)"
    r"\s+\d{2,6}(?:-\d{1,3})?(?::\d{4})?(?:/\d{2}\.\d{2})?(?:\+A\d{1,2})?"
)
_STANDARD_LINE = re.compile(
    r"\s*" + _STANDARD_CODE + r"(?:\s+" + _STANDARD_CODE + r")*\s*",
    re.IGNORECASE,
)
_DECLARATION_LANGUAGE = re.compile(
    r"^\s*(?:(EN)\s+English|(DE)\s+Deutsch(?:\s+German)?)\b", re.IGNORECASE
)


def has_explicit_exclusion(text: str) -> bool:
    """An exclusion is a denying boundary, never a positive model scope."""
    return _REJECT.search(text) is not None


def _source_identity(
    sha: str, page: int, chunk_id: str, text: str, kind: str = "text"
) -> bool:
    """Match the source chunker's content-derived ID, including collision suffixes."""
    if kind not in {"text", "table"}:
        return False
    digest = hashlib.sha256(f"{kind}\0{text}".encode()).hexdigest()[:8]
    base = f"{sha[:12]}-p{page}-{digest}"
    return bool(
        re.fullmatch(re.escape(base) + r"(?:-(?:[2-9]|[1-9][0-9]+))?", chunk_id)
    )


def _declaration_language(text: str) -> str:
    match = _DECLARATION_LANGUAGE.match(text)
    if match is None or _CONTEXT.search(text) is None:
        return ""
    return "en" if match.group(1) else "de"


def certificate_boundaries_allow(
    boundaries: Sequence[Mapping[str, Any]],
    *,
    sha: str,
    page: int,
    original: str,
    source_text: str,
    model: str,
    declaration_text: str = "",
    attestation_text: str = "",
    limitation_text: str = "",
    unit_standard_text: str = "",
    unit_statement_text: str = "",
    appendix: Mapping[str, str] | None = None,
    red: Mapping[str, str] | None = None,
) -> bool:
    """Keep inherited authored limits; separate explicit EN and DE declarations."""
    for boundary in boundaries:
        quote = boundary.get("quote")
        prior = boundary.get("source_text")
        prior_id = boundary.get("source_chunk_id")
        prior_page = boundary.get("source_page")
        kind = boundary.get("kind")
        if (
            not isinstance(kind, str)
            or kind not in {"heading", "declaration"}
            or not isinstance(quote, str)
            or not quote
            or not isinstance(prior, str)
            or not isinstance(prior_id, str)
            or type(prior_page) is not int
            or prior_page <= 0
            or not _source_identity(sha, prior_page, prior_id, prior)
        ):
            return False
        if kind == "declaration":
            if quote != prior:
                return False
        else:
            headings = boundary.get("source_headings")
            if not isinstance(headings, list) or (
                quote not in headings and quote != boundary.get("source_section")
            ):
                return False
        if has_explicit_exclusion(quote):
            return False
        if (
            red
            and kind == "declaration"
            and quote == red.get("header")
            and certificate_text(source_text, model, red=red) is not None
        ):
            continue
        if kind == "heading" and _GENERIC_LVD_HEADING.fullmatch(quote.strip()):
            continue
        cover = _SEE_CERTIFICATE.search(quote) if kind == "declaration" else None
        if (
            cover
            and not _NARROWING.search(quote)
            and not re.search(
                r"\b(?:model(?:s|le)?|type\s+designation|appl(?:y|ies|icable)\s+(?:to|for))\b",
                quote[cover.end() :],
                re.IGNORECASE,
            )
        ):
            cover_report = _REPORT_NUMBER.search(quote)
            source_report = _REPORT_NUMBER.search(source_text)
            if (
                cover_report
                and source_report
                and re.sub(r"\s+", " ", cover_report.group(1)).casefold()
                == re.sub(r"\s+", " ", source_report.group(1)).casefold()
            ):
                continue
        if kind == "declaration" and prior_id == original:
            if (
                certificate_text(
                    prior,
                    model,
                    declaration_text=declaration_text,
                    attestation_text=attestation_text,
                    limitation_text=limitation_text,
                    unit_standard_text=unit_standard_text,
                    unit_statement_text=unit_statement_text,
                    appendix=appendix,
                    red=red,
                )
                is None
            ):
                return False
            continue
        if model_pattern(model).search(quote):
            continue
        # A complete declaration on a later, explicitly labelled language page
        # proves that page independently. It cannot normalize a typo in the
        # earlier language or lend that earlier page the missing model.
        if not (
            kind == "declaration"
            and prior_page < page
            and _declaration_language(prior) in {"en", "de"}
            and _declaration_language(source_text) in {"en", "de"}
            and _declaration_language(prior) != _declaration_language(source_text)
        ):
            return False
    return True


def certificate_document(document: Mapping[str, Any]) -> bool:
    """Use the established explicit-role-first document purpose."""
    purpose = (
        str(document.get("role", "")).strip() or str(document.get("type", "")).strip()
    )
    return purpose.casefold() in _CERTIFICATE


def _shared_finite_models(section: str) -> set[str] | None:
    """Expand an original model axis followed by its own finite value lists.

    Some certificates put several xx/yy model templates before the two lists.
    Every template and list must be accounted for; unrelated text, ranges,
    duplicate or missing definitions cannot establish a model's identity.
    """
    templates = list(_SHARED_TEMPLATE.finditer(section))
    definitions = list(_SHARED_VALUES.finditer(section))
    if (
        not templates
        or not definitions
        or max(t.end() for t in templates) > min(d.start() for d in definitions)
    ):
        return None
    residual = _SHARED_VALUES.sub(" ", _SHARED_TEMPLATE.sub(" ", section))
    if re.search(r"[^\s,]", residual):
        return None
    values: dict[str, list[str]] = {}
    for definition in definitions:
        variable = definition["variable"].casefold()
        numbers = [part.strip() for part in definition["values"].rstrip(",").split(",")]
        if (
            variable in values
            or len(numbers) < 2
            or len(numbers) > 32
            or len(set(numbers)) != len(numbers)
        ):
            return None
        values[variable] = numbers
    if {template["variable"].casefold() for template in templates} != values.keys():
        return None
    return {
        (template["prefix"] + number + template["suffix"]).casefold()
        for template in templates
        for number in values[template["variable"].casefold()]
    }


def _paired_certificate_text(
    source_text: str, model: str, declaration_text: str
) -> str | None:
    """A same-page declaration and its literal model list with actual directives."""
    declaration = _PAIRED_DECLARATION.search(declaration_text)
    directives = _PAIRED_DIRECTIVES.search(source_text)
    axes = list(re.finditer(r"(?im)^\s*Model\s*:\s*", source_text))
    if (
        declaration is None
        or directives is None
        or len(axes) != 1
        or axes[0].end() >= directives.start()
        or has_explicit_exclusion(declaration_text)
        or has_explicit_exclusion(source_text)
    ):
        return None
    original_axis = source_text[axes[0].end() : directives.start()]
    module_note = ""
    if model.upper().endswith("-X"):
        three_phase = re.search(
            r"\bThree-phase inverter:", original_axis, re.IGNORECASE
        )
        if three_phase is None:
            return None
        subsection = original_axis[three_phase.end() :]
        notes = list(_PAIRED_MODULE_NOTE.finditer(subsection))
        if (
            len(notes) != 1
            or model_pattern(model).search(subsection[: notes[0].start()]) is None
        ):
            return None
        module_note = notes[0].group(0)
    axis = _PAIRED_MODULE_NOTE.sub(" ", _PAIRED_AXIS_LABEL.sub(" ", original_axis))
    tokens = _PAIRED_MODEL_TOKEN.findall(axis)
    if (
        not tokens
        or re.search(r"[^\s,]", _PAIRED_MODEL_TOKEN.sub(" ", axis))
        or any(
            not any(c.isalpha() for c in t) or not any(c.isdigit() for c in t)
            for t in tokens
        )
        or model.casefold() not in {token.casefold() for token in tokens}
    ):
        return None
    lines = [line.strip() for line in directives["lines"].splitlines() if line.strip()]
    if not lines or any(
        _PAIRED_DIRECTIVE_LINE.fullmatch(line) is None for line in lines
    ):
        return None
    return "\n".join(
        (
            declaration.group(0),
            f"Model: {model}",
            *([module_note] if module_note else []),
            directives["intro"],
            *lines,
        )
    )


def _goodwe_certificate_text(source_text: str, model: str) -> str | None:
    """Keep exact models and actual directive text from one English declaration."""
    declaration = _GOODWE_DECLARATION.search(source_text)
    claim = _GOODWE_CLAIM.search(source_text)
    if declaration is None or claim is None or declaration.end() >= claim.start():
        return None
    axis = source_text[declaration.end() : claim.start()].strip()
    axis = re.sub(
        r"^Product:\s*Rechargeable Li-ion Battery System\s*[\uf0b7●]\s*"
        r"|^[\uf0b7●]\s*Meter:\s*",
        "",
        axis,
        count=1,
        flags=re.IGNORECASE,
    )
    # One original declaration uses a full stop immediately between complete
    # G10 and GW model labels. Do not split decimal model numbers or variants.
    tokens = [
        value.strip()
        for value in re.split(r"[,，]|(?<=-G10)\.(?=GW\d)", axis, flags=re.IGNORECASE)
    ]
    if (
        not tokens
        or any(_PAIRED_MODEL_TOKEN.fullmatch(token) is None for token in tokens)
        or model.casefold() not in {token.casefold() for token in tokens}
    ):
        return None
    directives = [
        line.strip()
        for line in source_text[claim.end() :].splitlines()
        if _GOODWE_DIRECTIVE.fullmatch(line)
    ]
    if not directives:
        return None
    return "\n".join(
        (declaration.group(0), f"Model: {model}", claim.group(0), *directives)
    )


def _cb_certificate_text(source_text: str, model: str) -> str | None:
    """Bind an exact CB model list to its tested-sample standard on one page."""
    claim = _CB_CLAIM.search(source_text)
    issuer = _CB_ISSUER.search(source_text)
    axis = list(_CB_AXIS.finditer(source_text))
    if (
        claim is None
        or issuer is None
        or "Model / Type Ref." not in source_text
        or len(axis) != 1
    ):
        return None
    listed = axis[0]["models"] or axis[0]["plain_models"]
    listed = re.sub(r"\b\d+\)\s*", " ", listed)
    models = [token for token in re.split(r"[\s,]+", listed.strip()) if token]
    standards = [
        line.strip()
        for line in source_text.splitlines()
        if _STANDARD_LINE.fullmatch(line) and line.strip().upper().startswith("IEC ")
    ]
    if (
        not models
        or any(_PAIRED_MODEL_TOKEN.fullmatch(token) is None for token in models)
        or model.casefold() not in {token.casefold() for token in models}
        or len(standards) != 1
    ):
        return None
    return "\n".join((issuer.group(0), f"Model: {model}", claim.group(0), standards[0]))


def _attestation_text(
    source_text: str, model: str, statement: str, limitation: str
) -> str | None:
    axis = _ATTESTATION_MODELS.search(source_text)
    claim = _ATTESTATION_CLAIM.search(statement)
    annex = _ATTESTATION_ANNEX.search(statement)
    limit = _ATTESTATION_LIMIT.search(limitation)
    if (
        axis is None
        or claim is None
        or annex is None
        or limit is None
        or "Attestation No.:" not in source_text
        or has_explicit_exclusion(source_text)
        or has_explicit_exclusion(statement)
        or has_explicit_exclusion(limitation)
    ):
        return None
    models = [item.strip() for item in axis["models"].split(",")]
    if (
        not models
        or any(_PAIRED_MODEL_TOKEN.fullmatch(item) is None for item in models)
        or model.casefold() not in {item.casefold() for item in models}
    ):
        return None
    return "\n".join(
        (f"Model: {model}", claim.group(0), annex.group(0), limit.group(0))
    )


def _unit_certificate_text(
    source: str, model: str, standard: str, statement: str
) -> str | None:
    axis = re.search(r"Models / Modelle(?P<models>[\s\S]+?)Rated Voltage /", source)
    first, second = _UNIT_4110.search(source), _UNIT_4120.search(standard)
    number, claim, limit = (
        _UNIT_NUMBER.search(standard),
        _UNIT_CLAIM.search(statement),
        _UNIT_LIMIT.search(statement),
    )
    if (
        axis is None
        or model_pattern(model).search(axis["models"]) is None
        or first is None
        or second is None
        or number is None
        or claim is None
        or limit is None
        or "SGS" not in statement
        or has_explicit_exclusion(source)
        or has_explicit_exclusion(standard)
        or has_explicit_exclusion(statement)
    ):
        return None
    return "\n".join(
        (
            number.group(0),
            f"Model: {model}",
            first.group(0),
            second.group(0),
            claim.group(0),
            limit.group(0),
        )
    )


def _appendix_certificate_text(
    source: str, model: str, evidence: Mapping[str, str]
) -> str | None:
    first = _TUV_CERTIFICATE.search(evidence.get("identity", ""))
    second = _TUV_CERTIFICATE.search(source)
    axis = _TUV_AXIS.search(source)
    claim = _TUV_CLAIM.search(evidence.get("claim", ""))
    standards = [
        line.strip()
        for line in evidence.get("standards", "").splitlines()
        if line.strip() == "IEC 61010-1:2010+A1"
    ]
    if (
        first is None
        or second is None
        or re.sub(r"\s+", "", first.group(1)).casefold()
        != re.sub(r"\s+", "", second.group(1)).casefold()
        or axis is None
        or claim is None
        or len(standards) != 1
        or any(has_explicit_exclusion(value) for value in evidence.values())
    ):
        return None
    listed = re.sub(r"\b\d+\)\s*", " ", axis["models"])
    models = [item for item in re.split(r"[\s,]+", listed.strip()) if item]
    if (
        not models
        or any(_PAIRED_MODEL_TOKEN.fullmatch(item) is None for item in models)
        or model.casefold() not in {item.casefold() for item in models}
    ):
        return None
    return "\n".join((first.group(0), f"Model: {model}", standards[0], claim.group(0)))


def _red_certificate_text(
    source: str, model: str, evidence: Mapping[str, str]
) -> str | None:
    header, statement, limitation = (
        evidence.get(k, "") for k in ("header", "statement", "limitation")
    )
    number = certificate_registration(header)
    claim, limit = _LCIE_CLAIM.search(statement), _LCIE_LIMITATION.search(limitation)
    lines = source.splitlines()
    if (
        not number.startswith("red_")
        or "Modèle / Model" not in header
        or len(lines) < 3
        or "Composition du (of) document" not in source
        or re.search(r"Composition du \(of\) document\s*\n2 pages\b", source) is None
        or claim is None
        or limit is None
        or any(
            has_explicit_exclusion(item)
            for item in (source, header, statement, limitation)
        )
    ):
        return None
    names = [item.strip() for item in lines[0].split(",")]
    if not names or model.casefold() not in {item.casefold() for item in names}:
        return None
    return "\n".join(
        (
            number.upper(),
            f"Model: {model}",
            claim.group(0),
            "✓ Art. 3.3 d) Protection du reseau / Protection of Network | EN 18031-1:2024 | Conform(e)",
            limit.group(0),
        )
    )


def certificate_text(
    source_text: str,
    model: str,
    *,
    declaration_text: str = "",
    attestation_text: str = "",
    limitation_text: str = "",
    unit_standard_text: str = "",
    unit_statement_text: str = "",
    appendix: Mapping[str, str] | None = None,
    red: Mapping[str, str] | None = None,
) -> str | None:
    """Return a subject-only excerpt if this certificate names the exact model."""
    if (
        not _MODEL.fullmatch(model)
        or not any(c.isdigit() for c in model)
        or has_explicit_exclusion(source_text)
    ):
        return None
    if declaration_text:
        return _paired_certificate_text(source_text, model, declaration_text)
    if attestation_text:
        return _attestation_text(source_text, model, attestation_text, limitation_text)
    if unit_statement_text:
        return _unit_certificate_text(
            source_text, model, unit_standard_text, unit_statement_text
        )
    if appendix:
        return _appendix_certificate_text(source_text, model, appendix)
    if red:
        return _red_certificate_text(source_text, model, red)
    goodwe = _goodwe_certificate_text(source_text, model)
    if goodwe is not None:
        return goodwe
    cb = _cb_certificate_text(source_text, model)
    if cb is not None:
        return cb
    marker = _CONTEXT.search(source_text)
    registration = _REGISTRATION.search(source_text)
    if marker is None and registration is None:
        return None
    target = model.casefold()
    axes: list[tuple[str, set[str] | None]] = []
    for axis in _AXIS.finditer(source_text):
        # Localize the model axis so ratings later in the same extracted chunk
        # cannot be mistaken for additional model names or be emitted as facts.
        next_axis = _AXIS.search(source_text, axis.end())
        axis_end = min(
            axis.end() + 1200, next_axis.start() if next_axis else len(source_text)
        )
        section = source_text[axis.end() : axis_end]
        end = _END_AXIS.search(section)
        conformity = _CONFORMITY.search(section)
        ends = [item.start() for item in (end, conformity) if item is not None]
        if ends:
            section = section[: min(ends)]
        # The axis may contain other models, but no unexplained prose. Otherwise
        # a model mentioned in an adjacent example could acquire certificate scope.
        residual = _FINITE_AXIS.sub(" ", section)
        residual = _AXIS_DESCRIPTION.sub(" ", residual)
        residual = _AXIS_MODEL.sub(" ", residual)
        if re.sub(r"[\d\s\W_]+", "", residual):
            expanded = _shared_finite_models(section)
            # A model axis alone is not an independently useful passage. The
            # new shared-list form must also contain the original test claim.
            if expanded is not None and _SPECIMEN_CONFORMITY.search(source_text):
                axes.append((section, expanded))
        elif _AXIS_MODEL.search(section) or _FINITE_AXIS.search(section):
            axes.append((section, None))
    # Multiple distinct model axes need an explicit source relationship; do not
    # attach one certificate statement to a second, potentially unrelated list.
    if len(axes) != 1:
        return None
    section, expanded = axes[0]
    has_subject = (
        target in expanded
        if expanded is not None
        else bool(model_pattern(model).search(section))
    )
    for finite in _FINITE_AXIS.finditer(section):
        values = [value.strip() for value in finite["values"].split(",")]
        if len(values) < 2 or len(values) > 32 or len(set(values)) != len(values):
            continue
        candidates = {
            (finite["prefix"] + value + finite["suffix"]).casefold() for value in values
        }
        if target in candidates:
            has_subject = True
            break
    if not has_subject:
        return None
    # The named model is a deterministic expansion of the original finite axis
    # (or a literal source model). Do not expose the whole input chunk: an IEC
    # certificate can put model names next to Vmax/current/rated-power values.
    if marker is not None:
        label = marker.group(0)
    else:
        assert registration is not None
        label = f"Registration No.: {registration['number']}"
    output = [label, model]
    standard = next(
        (
            line.strip()
            for line in source_text.splitlines()
            if 0 < len(line.strip()) <= 160 and _STANDARD_LINE.fullmatch(line)
        ),
        "",
    )
    if standard:
        output.append(standard)
    claim = _CONFORMITY.search(source_text)
    if claim is not None:
        output.append(claim.group(0))
    specimen = _SPECIMEN_CONFORMITY.search(source_text)
    if expanded is not None and specimen is not None:
        output.append(specimen.group(0))
    low_voltage = _LOW_VOLTAGE_CLAIM.search(source_text)
    if low_voltage is not None:
        output.append(low_voltage.group(0))
    limitation = _LIMITATION.search(source_text)
    if limitation is not None:
        output.append(limitation.group(0))
    return "\n".join(output)


def certificate_id(
    sha: str, page: int, model: str, original: str, document_id: str, text: str
) -> str:
    digest = hashlib.sha256(
        f"{model}\0{original}\0{document_id}\0{text}".encode()
    ).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-certificate-{digest}"


def certificate_fragment_text(
    source_text: str, model: str, *, subject_text: str = "", limitation_text: str = ""
) -> str | None:
    """Select only positive certificate statements and complete standard IDs."""
    if (
        not _MODEL.fullmatch(model)
        or not any(c.isdigit() for c in model)
        or has_explicit_exclusion(source_text)
    ):
        return None
    declaration = _SPLIT_DECLARATION.search(source_text)
    if declaration:
        german = declaration["declaration"].casefold().startswith("wir")
        expected_following = (
            "Beachten Sie die folgenden Richtlinien und Vorschriften:"
            if german
            else "Comply with the following directives and regulations:"
        )
        directive = re.search(
            r"(?m)^[ \t]*RED Directive 2014/53/EU[ \t]*(?:●)?[ \t]*$",
            subject_text,
        )
        if (
            not re.match(
                r"\A\s*SMART COMMUNICATION BOX\s*\n\s*" + re.escape(model) + r"\s*\n",
                subject_text,
                re.IGNORECASE,
            )
            or expected_following not in subject_text
            or directive is None
        ):
            return None
        label = "Modell" if german else "Model"
        return "\n".join(
            (
                declaration["declaration"],
                f"{label}: {model}",
                expected_following,
                directive.group(0).strip(),
            )
        )
    lcie = _LCIE_CLAIM.search(source_text)
    if lcie:
        limitation = _LCIE_LIMITATION.search(limitation_text)
        if limitation is None:
            return None
        return "\n".join((model, lcie.group(0), limitation.group(0)))
    marker = next(
        (
            match.group(0)
            for pattern in (
                _CONTEXT,
                _CERTIFICATE_NUMBER,
                _LOW_VOLTAGE_CLAIM,
            )
            if (match := pattern.search(source_text)) is not None
        ),
        "",
    )
    if not marker:
        return None
    output = [marker, model]
    for pattern in (_CONFORMITY, _LIMITATION, _LOW_VOLTAGE_CLAIM):
        match = pattern.search(source_text)
        if match is not None and match.group(0) not in output:
            output.append(match.group(0))
    for line in source_text.splitlines():
        if 0 < len(line.strip()) <= 160 and _STANDARD_LINE.fullmatch(line):
            output.append(line.strip())
            break
    return "\n".join(output)


def certificate_fragment_id(
    sha: str, page: int, model: str, original: str, document_id: str, text: str
) -> str:
    digest = hashlib.sha256(
        f"{model}\0{original}\0{document_id}\0{text}".encode()
    ).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-certificate-fragment-{digest}"


def certificate_registration(source_text: str) -> str:
    match = _REGISTRATION.search(source_text)
    if match:
        return re.sub(r"\s+", " ", match["number"]).casefold()
    red = _RED_NUMBER.search(source_text)
    return red.group(1).casefold() if red else ""


def split_declaration(source_text: str) -> bool:
    return _SPLIT_DECLARATION.search(source_text) is not None


def lcie_declaration(source_text: str) -> bool:
    return _LCIE_CLAIM.search(source_text) is not None


def lcie_limitation(source_text: str) -> bool:
    return _LCIE_LIMITATION.search(source_text) is not None


def _valid_source_anchor(anchor: Any, sha: str) -> TypeGuard[dict[str, Any]]:
    if not isinstance(anchor, dict):
        return False
    page, original, text, kind = (
        anchor.get("page"),
        anchor.get("chunk_id"),
        anchor.get("text"),
        anchor.get("kind"),
    )
    return (
        type(page) is int
        and page > 0
        and isinstance(original, str)
        and isinstance(text, str)
        and isinstance(kind, str)
        and _source_identity(sha, page, original, text, kind)
    )


def attestation_table_valid(anchor: Any, sha: str, page: int) -> bool:
    """Verify the complete native two-row attestation table and its cell provenance."""
    if (
        not _valid_source_anchor(anchor, sha)
        or anchor["kind"] != "table"
        or anchor["page"] != page
        or anchor.get("source_rows") != [0, 1]
        or not isinstance(anchor.get("source_table"), str)
        or re.fullmatch(rf"docling:p{page}:#/tables/\d+", anchor["source_table"])
        is None
    ):
        return False
    cells = read_cells(anchor.get("source_cells"))
    if (
        cells is None
        or len(cells) != 6
        or cells_digest(cells) != anchor.get("cells_sha256")
    ):
        return False
    selected = [[cell_at(cells, row, col) for col in range(3)] for row in range(2)]
    if any(cell is None for row in selected for cell in row):
        return False
    matrix = [[cell["text"] for cell in row if cell is not None] for row in selected]
    if (
        matrix[0] != ["Standards", "Report number", "Report date"]
        or matrix[1][0] != "ETSI EN 303 645 V2.1.1 (2020-06)"
        or re.fullmatch(r"ASBJ-WDG-P\d+", matrix[1][1]) is None
        or re.fullmatch(r"\d{4}/\d{2}/\d{2}", matrix[1][2]) is None
    ):
        return False
    rendered = "\n".join("| " + " | ".join(row) + " |" for row in matrix)
    return rendered == str(anchor["text"])


def _physical_fragment(fragment: Any, size: Any) -> bool:
    if (
        not isinstance(fragment, dict)
        or not isinstance(size, (list, tuple))
        or len(size) != 2
    ):
        return False
    start, end, text, box = (
        fragment.get(k) for k in ("char_start", "char_end", "text", "bbox")
    )
    return bool(
        type(start) is int
        and type(end) is int
        and isinstance(text, str)
        and start >= 0
        and end - start == len(text)
        and text
        and isinstance(box, (list, tuple))
        and len(box) == 4
        and all(type(n) in (int, float) and math.isfinite(n) for n in [*size, *box])
        and 0 <= box[0] < box[2] <= size[0]
        and 0 <= box[1] < box[3] <= size[1]
    )


def certificate_page_marker(evidence: Any, sha: str, number: str) -> bool:
    if not isinstance(evidence, dict):
        return False
    marker = evidence.get("marker")
    return bool(
        evidence.get("kind") == "certificate_page_marker"
        and evidence.get("source_sha256") == sha
        and evidence.get("source_page") == 2
        and evidence.get("page_count") == 2
        and isinstance(marker, dict)
        and _physical_fragment(marker, evidence.get("page_size"))
        and certificate_registration(marker["text"]) == number
    )


def certificate_model_wrap(
    evidence: Any, sha: str, model: str, cell: Mapping[str, Any]
) -> bool:
    if not isinstance(evidence, dict):
        return False
    parts, size, gap = (
        evidence.get(k) for k in ("fragments", "page_size", "line_break")
    )
    cell_box = cell.get("bbox")
    if (
        evidence.get("kind") != "certificate_model_wrap"
        or evidence.get("source_sha256") != sha
        or evidence.get("source_page") != 1
        or evidence.get("model") != model
        or gap not in ("\n", "\r\n")
        or not isinstance(parts, list)
        or len(parts) != 2
        or not all(_physical_fragment(part, size) for part in parts)
        or cell.get("bbox_origin") != "TOPLEFT"
        or not isinstance(cell_box, (list, tuple))
        or len(cell_box) != 4
    ):
        return False
    a, b = parts
    if (
        not a["text"].endswith("-")
        or a["text"] + b["text"] != model
        or cell.get("text") != a["text"] + " " + b["text"]
        or a["char_end"] + len(gap) != b["char_start"]
    ):
        return False
    first, second = a["bbox"], b["bbox"]
    return bool(
        all(
            cell_box[0] <= part[0] < part[2] <= cell_box[2]
            and cell_box[1] <= part[1] < part[3] <= cell_box[3]
            for part in (first, second)
        )
        and max(first[0], second[0]) < min(first[2], second[2])
        and 0 <= second[1] - first[3] <= min(first[3] - first[1], second[3] - second[1])
    )


def red_table_valid(anchor: Any, sha: str) -> bool:
    if (
        not _valid_source_anchor(anchor, sha)
        or anchor["kind"] != "table"
        or anchor["page"] != 2
        or anchor.get("source_rows") != [0, 1]
        or not isinstance(anchor.get("source_table"), str)
        or re.fullmatch(r"docling:p2:#/tables/\d+", anchor["source_table"]) is None
    ):
        return False
    cells = read_cells(anchor.get("source_cells"))
    if (
        cells is None
        or len(cells) != 6
        or cells_digest(cells) != anchor.get("cells_sha256")
    ):
        return False
    selected = [[cell_at(cells, row, col) for col in range(3)] for row in range(2)]
    if any(cell is None for row in selected for cell in row):
        return False
    matrix = [[cell["text"] for cell in row if cell is not None] for row in selected]
    return bool(
        matrix[0]
        == ["Domaine couvert / Scope", "Normes / Standards", "Résultat / Result"]
        and matrix[1]
        == [
            "✓ Art. 3.3 d) Protection du reseau / Protection of Network",
            "EN 18031-1:2024",
            "Conform(e)",
        ]
        and "\n".join("| " + " | ".join(row) + " |" for row in matrix)
        == str(anchor["text"])
    )


def report_table_text(
    cells: Any, model: str
) -> tuple[str, list[tuple[int, str, str]]] | None:
    """Read the model and tested-sample conclusion from one native report table."""
    native = read_cells(cells)
    if native is None or _MODEL.fullmatch(model) is None:
        return None
    required = ("Report ID", "Model/Type", "Standard Specification", "Conclusion")
    fields: list[tuple[int, str, str]] = []
    for label in required:
        candidates = [
            cell
            for cell in native
            if cell["col_start"] == 0 and label.casefold() in cell["text"].casefold()
        ]
        if len(candidates) != 1:
            return None
        row = candidates[0]["row_start"]
        value = cell_at(native, row, 1)
        if value is None:
            return None
        fields.append((row, candidates[0]["text"], value["text"]))
    identifier, subject, standard, conclusion = (item[2] for item in fields)
    sample = re.search(
        r'The sample has passed the items of UN "Manual of Tests and Criteria" '
        r"ST/SG/AC\.10/11/Rev\.8/Section 38\.3\.",
        conclusion,
    )
    if (
        re.fullmatch(r"\d{8}J\d{5}", identifier) is None
        or re.fullmatch(
            re.escape(model) + r"\s+(?:\d+(?:\.\d+)?\s*(?:V|Ah|kWh)\s*)+",
            subject,
            re.IGNORECASE,
        )
        is None
        or "ST/SG/AC.10/11/Rev.8/Section 38.3" not in standard
        or sample is None
    ):
        return None
    return f"Report ID: {identifier}\nModel/Type: {model}\n{sample.group(0)}", fields


def _valid_report_table(
    evidence: Any,
    *,
    sha: str,
    page: int,
    model: str,
    text: str,
    source_ids: Sequence[str],
) -> bool:
    if not isinstance(evidence, dict):
        return False
    table = evidence.get("source_table")
    cells = read_cells(evidence.get("source_cells"))
    fragments = evidence.get("fragments")
    if (
        not isinstance(table, str)
        or re.fullmatch(rf"docling:p{page}:#/tables/\d+", table) is None
        or cells is None
        or cells_digest(cells) != evidence.get("cells_sha256")
        or not isinstance(fragments, list)
        or not fragments
    ):
        return False
    found = report_table_text(cells, model)
    if found is None or found[0] != text:
        return False
    for row, label, value in found[1]:
        if not any(
            _valid_source_anchor(fragment, sha)
            and fragment["kind"] == "table"
            and fragment["page"] == page
            and fragment["chunk_id"] in source_ids
            and fragment.get("source_table") == table
            and isinstance(fragment.get("source_rows"), list)
            and row in fragment["source_rows"]
            and label in fragment["text"]
            and value in fragment["text"]
            for fragment in fragments
        ):
            return False
    return True


def unit_table_text(
    cells: Any, model: str, wrap: Any, sha: str, statement: str
) -> tuple[str, list[tuple[int, str]]] | None:
    """Prove an SGS unit model from the physically wrapped native model cell."""
    native = read_cells(cells)
    if native is None:
        return None
    labels = [cell for cell in native if cell["text"] == "Model / Modell"]
    models = [cell for cell in native if certificate_model_wrap(wrap, sha, model, cell)]
    numbers = [
        (cell, number)
        for cell in native
        if (number := _UNIT_NUMBER.search(cell["text"]))
    ]
    standards = [
        cell
        for cell in native
        if all(
            pattern.search(cell["text"])
            for pattern in (_UNIT_4110, _UNIT_4120, _UNIT_4130)
        )
    ]
    claim, limit = _UNIT_CLAIM.search(statement), _UNIT_LIMIT.search(statement)
    if (
        len(labels) != 1
        or len(models) != 1
        or len(numbers) != 1
        or len(standards) != 1
        or labels[0]["row_start"] != models[0]["row_start"]
        or claim is None
        or limit is None
        or "SGS" not in statement
        or has_explicit_exclusion(statement)
    ):
        return None
    first, second, third = (
        _UNIT_4110.search(standards[0]["text"]),
        _UNIT_4120.search(standards[0]["text"]),
        _UNIT_4130.search(standards[0]["text"]),
    )
    assert first and second and third
    number_text = numbers[0][1].group(0)
    text = "\n".join(
        (
            number_text,
            f"Model: {model}",
            first.group(0),
            second.group(0),
            third.group(0),
            claim.group(0),
            limit.group(0),
        )
    )
    fields = [
        (numbers[0][0]["row_start"], number_text),
        (models[0]["row_start"], models[0]["text"]),
        *(
            (standards[0]["row_start"], item.group(0))
            for item in (first, second, third)
        ),
    ]
    return text, fields


def _valid_unit_table(
    evidence: Any,
    *,
    sha: str,
    page: int,
    model: str,
    text: str,
    source_ids: Sequence[str],
) -> bool:
    if not isinstance(evidence, dict) or page != 1:
        return False
    table, cells, fragments, statement = (
        evidence.get(k)
        for k in ("source_table", "source_cells", "fragments", "statement_anchor")
    )
    native = read_cells(cells)
    if (
        not isinstance(table, str)
        or re.fullmatch(r"docling:p1:#/tables/\d+", table) is None
        or native is None
        or cells_digest(native) != evidence.get("cells_sha256")
        or not isinstance(fragments, list)
        or not _valid_source_anchor(statement, sha)
        or statement["kind"] != "text"
        or statement["page"] != page
        or statement["chunk_id"] not in source_ids
    ):
        return False
    found = unit_table_text(
        native, model, evidence.get("model_wrap"), sha, statement["text"]
    )
    if found is None or found[0] != text:
        return False
    return all(
        any(
            _valid_source_anchor(fragment, sha)
            and fragment["kind"] == "table"
            and fragment["page"] == page
            and fragment["chunk_id"] in source_ids
            and fragment.get("source_table") == table
            and isinstance(fragment.get("source_rows"), list)
            and row in fragment["source_rows"]
            and value in fragment["text"]
            for fragment in fragments
        )
        for row, value in found[1]
    )


def valid_certificate_fragment(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
) -> bool:
    """Check a safe excerpt before replaying its original proof separately."""
    proof = scope.get("certificate_fragment")
    if scope.get("basis") != "certificate_fragment" or not isinstance(proof, dict):
        return False
    pid, did = proof.get("product_id"), proof.get("document_id")
    page, original = proof.get("source_page"), proof.get("source_chunk_id")
    source_text, kind, origin = (
        proof.get("source_text"),
        proof.get("source_kind"),
        proof.get("origin_scope"),
    )
    product = products.get(pid) if type(pid) is int else None
    document = documents.get(did) if isinstance(did, str) else None
    if (
        product is None
        or document is None
        or not isinstance(did, str)
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or scope.get("document_ids") != [did]
        or not certificate_document(document)
        or document.get("blob_sha256") != sha
        or pid not in document.get("product_ids", [])
        or did not in product.get("documents", [])
        or proof.get("source_sha256") != sha
        or proof.get("model") != product.get("model")
        or type(page) is not int
        or page <= 0
        or not isinstance(original, str)
        or not isinstance(source_text, str)
        or not isinstance(kind, str)
        or not isinstance(origin, dict)
        or origin.get("basis")
        not in {"passage", "section", "section_model", "document_model", "common_terms"}
        or original not in scope.get("source_chunk_ids", [])
        or pid not in origin.get("product_ids", [])
        or did not in origin.get("document_ids", [])
        or proof.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
    ):
        return False
    model = str(product["model"])
    anchor = proof.get("subject_anchor")
    if (
        not _valid_source_anchor(anchor, sha)
        or anchor["chunk_id"] not in origin.get("source_chunk_ids", [])
        or not model_pattern(model).search(anchor["text"])
        or has_explicit_exclusion(anchor["text"])
    ):
        return False
    if anchor["page"] != page:
        registration = proof.get("registration_anchor")
        if (
            not _valid_source_anchor(registration, sha)
            or registration["page"] != page
            or registration["chunk_id"] not in scope.get("source_chunk_ids", [])
            or not certificate_registration(anchor["text"])
            or certificate_registration(registration["text"])
            != certificate_registration(anchor["text"])
        ):
            return False
    if split_declaration(source_text):
        between = proof.get("between_anchors")
        if (
            anchor["page"] != page
            or anchor.get("lang") != proof.get("source_lang")
            or not isinstance(between, list)
            or len(between) > 1
            or any(
                not _valid_source_anchor(item, sha)
                or item["page"] != page
                or item["chunk_id"] not in scope.get("source_chunk_ids", [])
                or not re.fullmatch(r"[A-Za-z]{1,8}", item["text"].strip())
                for item in between
            )
        ):
            return False
    limitation = proof.get("limitation_anchor")
    if lcie_declaration(source_text) and (
        not _valid_source_anchor(limitation, sha)
        or limitation["page"] != page
        or limitation["chunk_id"] not in scope.get("source_chunk_ids", [])
        or anchor["page"] == page
    ):
        return False
    return (
        _source_identity(sha, page, original, source_text, kind)
        and certificate_fragment_text(
            source_text,
            model,
            subject_text=anchor["text"],
            limitation_text=limitation["text"] if isinstance(limitation, dict) else "",
        )
        == text
        and chunk_id == certificate_fragment_id(sha, page, model, original, did, text)
    )


def valid_certificate_scope(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
) -> bool:
    """Recheck subject, original chunk, current document purpose and relation."""
    proof = scope.get("certificate_scope")
    if scope.get("basis") != "certificate_subject" or not isinstance(proof, dict):
        return False
    pid, did = proof.get("product_id"), proof.get("document_id")
    page, original, source_text = (
        proof.get("source_page"),
        proof.get("source_chunk_id"),
        proof.get("source_text"),
    )
    product = products.get(pid) if type(pid) is int else None
    document = documents.get(did) if isinstance(did, str) else None
    if (
        product is None
        or document is None
        or not isinstance(did, str)
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or scope.get("document_ids") != [did]
        or not certificate_document(document)
        or document.get("blob_sha256") != sha
        or pid not in document.get("product_ids", [])
        or did not in product.get("documents", [])
        or proof.get("source_sha256") != sha
        or proof.get("model") != product.get("model")
        or type(page) is not int
        or page <= 0
        or not isinstance(original, str)
        or original not in scope.get("source_chunk_ids", [])
        or not isinstance(source_text, str)
        or proof.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
    ):
        return False
    report = proof.get("report_table")
    if report is not None:
        report_boundaries = proof.get("author_boundaries")
        return (
            proof.get("source_kind") == "table"
            and _source_identity(sha, page, original, source_text, "table")
            and isinstance(report_boundaries, list)
            and all(
                isinstance(item, dict)
                and item.get("source_chunk_id") in scope.get("source_chunk_ids", [])
                for item in report_boundaries
            )
            and certificate_boundaries_allow(
                report_boundaries,
                sha=sha,
                page=page,
                original=original,
                source_text=source_text,
                model=str(product["model"]),
            )
            and _valid_report_table(
                report,
                sha=sha,
                page=page,
                model=str(product["model"]),
                text=text,
                source_ids=scope.get("source_chunk_ids", []),
            )
            and chunk_id
            == certificate_id(sha, page, str(product["model"]), original, did, text)
        )
    unit_table = proof.get("unit_table")
    if unit_table is not None:
        unit_boundaries = proof.get("author_boundaries")
        return (
            proof.get("source_kind") == "table"
            and _source_identity(sha, page, original, source_text, "table")
            and isinstance(unit_boundaries, list)
            and all(
                isinstance(item, dict)
                and item.get("source_chunk_id") in scope.get("source_chunk_ids", [])
                for item in unit_boundaries
            )
            and certificate_boundaries_allow(
                unit_boundaries,
                sha=sha,
                page=page,
                original=original,
                source_text=source_text,
                model=str(product["model"]),
            )
            and _valid_unit_table(
                unit_table,
                sha=sha,
                page=page,
                model=str(product["model"]),
                text=text,
                source_ids=scope.get("source_chunk_ids", []),
            )
            and chunk_id
            == certificate_id(sha, page, str(product["model"]), original, did, text)
        )
    boundaries = proof.get("author_boundaries")
    if not isinstance(boundaries, list) or any(
        not isinstance(item, dict) for item in boundaries
    ):
        return False
    model = str(product["model"])
    declaration_text = ""
    declaration = proof.get("declaration_anchor")
    attestation_text = ""
    limitation_text = ""
    unit_standard_text = ""
    unit_statement_text = ""
    appendix: dict[str, str] = {}
    red: dict[str, str] = {}
    if declaration is not None:
        between = proof.get("between_anchors")
        section, lang = proof.get("source_section"), proof.get("source_lang")
        if (
            not _valid_source_anchor(declaration, sha)
            or declaration["kind"] != "text"
            or declaration["page"] != page
            or declaration["chunk_id"] not in scope.get("source_chunk_ids", [])
            or not isinstance(section, str)
            or not section
            or declaration.get("section") != section
            or not isinstance(lang, str)
            or not lang
            or declaration.get("lang") != lang
            or not isinstance(between, list)
            or len(between) > 1
            or any(
                not _valid_source_anchor(item, sha)
                or item["kind"] != "text"
                or item["page"] != page
                or item.get("section") != section
                or not isinstance(item.get("source_picture"), str)
                or not item["source_picture"]
                or item["chunk_id"] not in scope.get("source_chunk_ids", [])
                or not re.fullmatch(r"[A-Za-z]{1,8}", item["text"].strip())
                or item["text"].strip().casefold() in {"only", "nur", "not", "no"}
                for item in between
            )
        ):
            return False
        declaration_text = declaration["text"]
    statement = proof.get("statement_anchor")
    if statement is not None:
        table = proof.get("statement_table")
        limitation = proof.get("limitation_anchor")
        lang = proof.get("source_lang")
        if (
            declaration is not None
            or not isinstance(lang, str)
            or not lang
            or not _valid_source_anchor(statement, sha)
            or statement["kind"] != "text"
            or statement["page"] != page
            or statement.get("lang") != lang
            or statement["chunk_id"] not in scope.get("source_chunk_ids", [])
            or not isinstance(table, dict)
            or not attestation_table_valid(table, sha, page)
            or table["chunk_id"] not in scope.get("source_chunk_ids", [])
            or not _valid_source_anchor(limitation, sha)
            or limitation["kind"] != "text"
            or limitation["page"] != page
            or limitation.get("lang") != lang
            or limitation["chunk_id"] not in scope.get("source_chunk_ids", [])
        ):
            return False
        attestation_text = statement["text"]
        limitation_text = limitation["text"]
    unit_statement = proof.get("unit_statement_anchor")
    if unit_statement is not None:
        unit_standard = proof.get("unit_standard_anchor")
        if (
            declaration is not None
            or statement is not None
            or not _valid_source_anchor(unit_statement, sha)
            or unit_statement["kind"] != "text"
            or unit_statement["page"] != page
            or unit_statement["chunk_id"] not in scope.get("source_chunk_ids", [])
            or not _valid_source_anchor(unit_standard, sha)
            or unit_standard["kind"] != "text"
            or unit_standard["page"] != page
            or unit_standard["chunk_id"] not in scope.get("source_chunk_ids", [])
        ):
            return False
        unit_standard_text = unit_standard["text"]
        unit_statement_text = unit_statement["text"]
    appendix_anchors = proof.get("appendix_anchors")
    if appendix_anchors is not None:
        if (
            declaration is not None
            or statement is not None
            or unit_statement is not None
            or not isinstance(appendix_anchors, dict)
            or set(appendix_anchors) != {"identity", "standards", "claim"}
        ):
            return False
        for role, anchor in appendix_anchors.items():
            if (
                not _valid_source_anchor(anchor, sha)
                or anchor["kind"] != "text"
                or anchor["page"] != page - 1
                or anchor["chunk_id"] not in scope.get("source_chunk_ids", [])
            ):
                return False
            appendix[role] = anchor["text"]
    red_anchors = proof.get("red_anchors")
    if red_anchors is not None:
        if (
            declaration is not None
            or statement is not None
            or unit_statement is not None
            or appendix_anchors is not None
            or not isinstance(red_anchors, dict)
            or set(red_anchors)
            != {"header", "statement", "limitation", "table", "page_marker"}
            or page != 1
        ):
            return False
        for role in ("header", "statement", "limitation"):
            anchor = red_anchors[role]
            if (
                not _valid_source_anchor(anchor, sha)
                or anchor["kind"] != "text"
                or anchor["page"] != (1 if role == "header" else 2)
                or anchor["chunk_id"] not in scope.get("source_chunk_ids", [])
            ):
                return False
            red[role] = anchor["text"]
        table = red_anchors["table"]
        if (
            not isinstance(table, dict)
            or not red_table_valid(table, sha)
            or table["chunk_id"] not in scope.get("source_chunk_ids", [])
            or not certificate_page_marker(
                red_anchors["page_marker"], sha, certificate_registration(red["header"])
            )
        ):
            return False
    return (
        _source_identity(sha, page, original, source_text)
        and all(
            item.get("source_chunk_id") in scope.get("source_chunk_ids", [])
            for item in boundaries
        )
        and certificate_boundaries_allow(
            boundaries,
            sha=sha,
            page=page,
            original=original,
            source_text=source_text,
            model=model,
            declaration_text=declaration_text,
            attestation_text=attestation_text,
            limitation_text=limitation_text,
            unit_standard_text=unit_standard_text,
            unit_statement_text=unit_statement_text,
            appendix=appendix,
            red=red,
        )
        and certificate_text(
            source_text,
            model,
            declaration_text=declaration_text,
            attestation_text=attestation_text,
            limitation_text=limitation_text,
            unit_standard_text=unit_standard_text,
            unit_statement_text=unit_statement_text,
            appendix=appendix,
            red=red,
        )
        == text
        and chunk_id == certificate_id(sha, page, model, original, did, text)
    )
