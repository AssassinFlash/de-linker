"""Narrow roles stated in original text, independent of product permission."""

from __future__ import annotations

import re

METER = re.compile(
    r"\bmeter\s+(?:[A-Z][\w.-]*['’]s\s+)?"
    r"(?P<model>[A-Za-z][A-Za-z0-9./-]*\d[A-Za-z0-9./-]*)\b",
    re.IGNORECASE,
)
# The positive declaration in the original CHS2 manual, followed by a literal
# model list. A generic mention of 'manual' or 'following' is insufficient.
MANUAL_SCOPE = re.compile(
    r"\bThis\s+User\s+Manual\s+describes\s+instructions\s+and\s+detailed\s+"
    r"procedures\s+for\s+installing,\s+operating,\s+maintaining,\s+and\s+"
    r"troubleshooting\s+of\s+the\s+following\s+[^:]+:",
    re.IGNORECASE,
)


def manual_scope_models(text: str) -> set[str]:
    """Exact members of that positive original list, without further prose."""
    declaration = MANUAL_SCOPE.search(text)
    if declaration is None:
        return set()
    tail = text[declaration.end() :]
    token = r"[A-Za-z0-9][A-Za-z0-9./-]*"
    labels = re.findall(token, tail)
    remainder = re.sub(token, "", tail)
    if (
        not labels
        or any(
            not any(c.isalpha() for c in label) or not any(c.isdigit() for c in label)
            for label in labels
        )
        or any(c not in " \n\t,;•⚫" for c in remainder)
    ):
        return set()
    return {label.casefold() for label in labels}


def meter_references(text: str) -> list[tuple[str, str]]:
    """(literal model, role quote); a bare model or product category is no role."""
    return [(m["model"], m[0]) for m in METER.finditer(text)]


# The authored BAT-C component row, EN 'Pack Type / model' and DE 'Batteriepack-Typ /
# Modell' (BAT-C datasheet DE blob 2a76fb0815a2, p.2; the EN twin isolates the same
# row through the chunker). Only full-cell matches; a prefix or partial label is
# never a component-role declaration.
PACK_MODEL_LABEL = re.compile(
    r"Pack\s+(?:Type\s*/\s*model|model(?:\s*/\s*type)?)"
    r"|Batteriepack-(?:Typ|Modell)\s*/\s*(?:Modell|Typ)"
    r"|Pack-(?:Typ|Modell)\s*/\s*(?:Modell|Typ)",
    re.IGNORECASE,
)


def pack_model_row(text: str) -> bool:
    """One native property row, distinct from the system's model-column axis.

    The authored BAT-C table uses 'Pack Type / model' / 'Batteriepack-Typ /
    Modell' for a component. This only isolates that row; its model and facts
    still need their own permission.
    """
    lines = text.splitlines()
    if len(lines) != 1 or not text.startswith("|") or not text.endswith("|"):
        return False
    cells = [cell.strip() for cell in text.split("|")[1:-1]]
    return len(cells) >= 3 and PACK_MODEL_LABEL.fullmatch(cells[0]) is not None
