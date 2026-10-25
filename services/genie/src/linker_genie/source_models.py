"""Literal model references and family names; these classify, never grant access."""

from __future__ import annotations

import re
from collections.abc import Iterable

CODE = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9./-]*\b")
MODEL_FIELD = re.compile(
    r"\b(?:models?|product\s+model|model/type|type\s+designation|modell(?:e)?|typ)\b"
    r"|型号(?:规格)?",
    re.IGNORECASE,
)
ENGINEERING = re.compile(
    r"(?:IP\d{2}[A-Z]?|(?:IEC|ISO|IEEE|VDE|EN|DIN|UN|UL)\d[\dA-Z./-]*"
    r"|(?:RS|MPPT|PV|COM|DI|DO|AI|AO)\d+"
    r"|[\d./-]+(?:[kmunMGT]?(?:Hz|Wh|W|VA|V|Ah|A|Ohm)|Vac|Vdc|Vd\.c|Ad\.c)"
    r"|\d+(?:-\d+)?K)",
    re.IGNORECASE,
)


def codes(text: str) -> list[str]:
    return sorted(
        {
            token
            for token in CODE.findall(text)
            if any(c.isalpha() for c in token) and any(c.isdigit() for c in token)
        }
    )


def model_pattern(label: str) -> re.Pattern[str]:
    """A shorter model must not match a suffix variant's facts."""
    written = r"\s+".join(re.escape(part) for part in label.split())
    return re.compile(r"(?<![\w./-])" + written + r"(?![\w/-]|\.(?=\w))", re.IGNORECASE)


def family_labels(labels: set[str]) -> set[str]:
    """A strict model prefix is a family unless Woo knows that exact identity."""
    return {
        first
        for label in labels
        if "-" in label
        for first in [label.split("-", 1)[0]]
        if len(first) >= 2
        and any(c.isalpha() for c in first)
        and any(c.isdigit() for c in first)
        and first not in labels
    }


def family_mentions(text: str, families: set[str]) -> dict[str, str]:
    """Literal family titles include the manufacturer's EN/DE role nouns."""
    output = {}
    for family in families:
        role = re.search(
            r"(?<![\w./-])"
            + re.escape(family)
            + r"[-\s]+(?:series?|serie|inverters?|wechselrichter[\wäöüß]*|systems?|systeme?)\b",
            text,
            re.IGNORECASE,
        )
        plain = model_pattern(family).search(text)
        if role is not None or plain is not None:
            match = role if role is not None else plain
            assert match is not None
            output[family] = match[0]
    return output


def model_shapes(labels: Iterable[str]) -> set[str]:
    shapes = set()
    for label in labels:
        leading = re.match(r"[A-Za-z]+", label)
        if leading is not None and len(leading[0]) >= 2:
            shapes.add(leading[0].casefold())
        else:
            first = re.split(r"[\s./-]", label)[0]
            if len(first) >= 2:
                shapes.add(first.casefold())
    return shapes


def unknown_models(
    text: str,
    labels: set[str],
    shapes: set[str],
    *,
    section: bool = False,
    families: set[str] | None = None,
) -> bool:
    """Reject unresolved model references, preserving ordinary engineering tokens.

    The authored model/type axis, neighbours of an explicit model and known Woo
    model shapes supply context. ``section`` also treats unresolved mixed codes
    as candidates. A bare strict family heading grants no variant's parameters.
    """
    known_tokens = {token.casefold() for label in labels for token in codes(label)}
    family_tokens = {
        token.casefold()
        for quote in family_mentions(text, families or set()).values()
        for token in codes(quote)
    }
    declared = {
        token.casefold()
        for line in text.splitlines()
        if MODEL_FIELD.search(line)
        for token in codes(line)
    }
    residual = text
    for label in sorted(labels, key=len, reverse=True):
        residual = re.sub(re.escape(label), " @MODEL@ ", residual, flags=re.IGNORECASE)
    coupled = {
        token.casefold()
        for token in re.findall(
            r"@MODEL@\s*(?:[,/&|]|and\b|or\b|und\b|oder\b)\s*([A-Za-z0-9][A-Za-z0-9./-]*)",
            residual,
            re.IGNORECASE,
        )
    }
    for line in text.splitlines():
        amendments = {s.casefold() for s in re.findall(r"\+\s*([A-Z]\d+)\b", line)}
        for token in codes(line):
            if (
                token.casefold() in known_tokens
                or token.casefold() in (families or set())
                or token.casefold() in family_tokens
                or token.casefold() in amendments
                or ENGINEERING.fullmatch(token)
            ):
                continue
            prefix = re.match(r"[A-Za-z]+", token)
            if (
                (prefix is not None and prefix[0].casefold() in shapes)
                or any(
                    token.casefold() == shape
                    or token.casefold().startswith(shape + "-")
                    for shape in shapes
                    if any(c.isdigit() for c in shape)
                )
                or token.casefold() in declared
                or token.casefold() in coupled
                or section
            ):
                return True
    return False
