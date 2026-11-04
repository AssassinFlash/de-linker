"""Explicit document-label to Woo-model aliases (#900 §9.6).

Every entry names the same physical product under the manufacturer's other
writing. An alias never widens permission: it only lets a label that a
published document physically proves resolve to the one current Woo product
it names, and compile time still requires that product to be published and
associated with the document. Anything not listed stays unresolved (fail
closed); a regex or prefix rule is deliberately not used (#900 §9.6).

Evidence per family:
- SAJ HS3 5-12K DE datasheet (blob e00f9645d187, p.2): the German table heads
  its five columns 'HS3-5-12K-T2-W/G-P1..P5' while the English twin
  (b4a653fd2c0b) writes the same physical table with one model per column in
  ascending rated power (Rated AC Power 5000/6000/8000/10000/12000 W), and
  exactly those five models are the current Woo products.
- SAJ CHS2 datasheets (2e4e566cf46d EN BEU, 6f3b2db569cc DE, bd64908d87dd EN):
  the documents are titled CHS2 and Woo carries CHS2-*-T4/T6-X with identical
  ratings; the tables' own header row writes the family without the S and the
  X suffix.
- SAJ HS3 user manual (2c1dd5c1e2f7, report-only doc_type): the manual's table
  header drops the /G and the X of the model the EN datasheet proves.
"""

from __future__ import annotations

MODEL_ALIASES: dict[str, str] = {
    # SAJ HS3 5-12K DE datasheet column labels (P1..P5, ascending power).
    "hs3-5-12k-t2-w/g-p1": "hs3-5k-t2-w/g-px",
    "hs3-5-12k-t2-w/g-p2": "hs3-6k-t2-w/g-px",
    "hs3-5-12k-t2-w/g-p3": "hs3-8k-t2-w/g-px",
    "hs3-5-12k-t2-w/g-p4": "hs3-10k-t2-w/g-px",
    "hs3-5-12k-t2-w/g-p5": "hs3-12k-t2-w/g-px",
    # SAJ CHS2 datasheet table headers.
    "ch2-29.9k-t4": "chs2-29.9k-t4-x",
    "ch2-30k-t4": "chs2-30k-t4-x",
    "ch2-50k-t6": "chs2-50k-t6-x",
    # SAJ HS3 user manual table header.
    "hs3-12k-t2-w-p": "hs3-12k-t2-w/g-px",
}


def woo_model(label: str) -> str:
    """The current Woo model a document label names, or the label itself."""
    return MODEL_ALIASES.get(label.casefold(), label.casefold())
