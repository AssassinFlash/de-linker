"""Certificate-only model evidence, replayed against the current Woo relations.

A declaration can list exact models or a finite placeholder enumeration. Its
model axis is evidence of the certificate's subject, never of technical ratings.
Only a small certificate-context fragment is returned to the retrieval layer.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

from linker_genie.source_models import model_pattern

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
            if certificate_text(prior, model) is None:
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


def certificate_text(source_text: str, model: str) -> str | None:
    """Return a subject-only excerpt if this certificate names the exact model."""
    if (
        not _MODEL.fullmatch(model)
        or not any(c.isdigit() for c in model)
        or has_explicit_exclusion(source_text)
    ):
        return None
    marker = _CONTEXT.search(source_text)
    registration = _REGISTRATION.search(source_text)
    if marker is None and registration is None:
        return None
    target = model.casefold()
    axes: list[str] = []
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
            continue
        if _AXIS_MODEL.search(section) or _FINITE_AXIS.search(section):
            axes.append(section)
    # Multiple distinct model axes need an explicit source relationship; do not
    # attach one certificate statement to a second, potentially unrelated list.
    if len(axes) != 1:
        return None
    section = axes[0]
    has_subject = bool(model_pattern(model).search(section))
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
    boundaries = proof.get("author_boundaries")
    if not isinstance(boundaries, list) or any(
        not isinstance(item, dict) for item in boundaries
    ):
        return False
    model = str(product["model"])
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
        )
        and certificate_text(source_text, model) == text
        and chunk_id == certificate_id(sha, page, model, original, did, text)
    )
