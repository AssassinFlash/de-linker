"""Certificate-only model evidence, replayed against the current Woo relations.

A declaration can list exact models or a finite placeholder enumeration. Its
model axis is evidence of the certificate's subject, never of technical ratings.
Only a small certificate-context fragment is returned to the retrieval layer.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from linker_genie.source_models import model_pattern

# These labels are document roles, not manufacturer's model families.
_CERTIFICATE = frozenset({"certificate", "zertifikat"})
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]{1,100}\Z")
_AXIS = re.compile(
    r"\b(?:type\s+designation|bezeichnung\s+designation|"
    r"model(?:l|le|s)?(?:\s*/\s*type)?|product|produkt)\s*:",
    re.IGNORECASE,
)
_END_AXIS = re.compile(
    r"\b(?:firmware\s+version|vmax|isc\s+pv|rated\s+output|"
    r"input\s+current|mpp\s+voltage|overvoltage\s+category)\b",
    re.IGNORECASE,
)
_REJECT = re.compile(
    r"\b(?:not\s+(?:applicable|valid|covered|certified|listed|included)|"
    r"does\s+not\s+(?:apply\s+to|cover|include)|exclud(?:ed|es|ing)(?:\s+models?)?|"
    r"except\s+for|nicht\s+(?:gültig|anwendbar)|ausgeschlossen\w*)\b",
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
    r"this\s+certificate\s+does\s+not\s+imply\s+assessment\s+of\s+the\s+production\s+of\s+the\s+product\s+and\s+does\s+not\s+permit\s+the\s+use\s+of\s+a\s+TÜV\s+Rheinland\s+mark\s+of\s+conformity\.",
    re.IGNORECASE,
)
_STANDARD_LINE = re.compile(r"\b(?:EN|IEC|VDE|DIN)\s*[-A-Z0-9./: ]*\d", re.IGNORECASE)
_UNSAFE_STANDARD = re.compile(
    r"\b(?:rated|nominal|power|voltage|current|capacity|efficiency|"
    r"leistung|spannung|strom|kapazität|\d+(?:\.\d+)?\s*(?:kW|kWh|Vdc|Vac|A|V))\b",
    re.IGNORECASE,
)
_DECLARATION_LANGUAGE = re.compile(
    r"^\s*(?:(EN)\s+English|(DE)\s+Deutsch(?:\s+German)?)\b", re.IGNORECASE
)


def _source_identity(sha: str, page: int, chunk_id: str, text: str) -> bool:
    """Match the source chunker's content-derived ID, including collision suffixes."""
    digest = hashlib.sha256(f"text\0{text}".encode()).hexdigest()[:8]
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
        if _REJECT.search(quote):
            return False
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
        or _REJECT.search(source_text)
    ):
        return None
    marker = _CONTEXT.search(source_text)
    if marker is None:
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
    output = [marker.group(0), model]
    standard = next(
        (
            line.strip()
            for line in source_text.splitlines()
            if 0 < len(line.strip()) <= 160
            and _STANDARD_LINE.search(line)
            and not _UNSAFE_STANDARD.search(line)
        ),
        "",
    )
    if standard:
        output.append(standard)
    claim = _CONFORMITY.search(source_text)
    if claim is not None:
        output.append(claim.group(0))
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
