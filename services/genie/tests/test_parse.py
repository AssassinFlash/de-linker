"""Detection of unreadable text layers (index.parse.garbled_pages)."""

from index.parse import garbled_pages

# The text layer of the OCEAN 2 single-phase datasheet, p.2 (PDFium, 2026-10-09).
GARBLED = (
    'EcoFlow OCEAN 2 Hybrid Inverter Single-Phase\r\n!"\r\n!"#$%&#\'()*\'+\',"-"+.\r\n'
    "!\"#$%&#'()/'+',\"-\"+. 01)234*54\r\n67489\r\n01)234*54\r\n67:;489\r\n3?)@%/A￾B*CD\r\n"
    "!\"#$%&%'()'(*+,-'./0 1222 1342 52322 55222 55222 56222"
)
# Readable pages with the most punctuation in the corpus: a table of contents with dot
# leaders and a harmonics table of numbers.
CONTENTS = (
    "Contents\r\n1. Safety instructions"
    + "." * 120
    + " 3\r\n2. Installation"
    + "." * 120
    + " 9"
)
NUMBERS = "Seite 5 von 7\r\n16 0,008 0,006 0,006 0,007 0,004 0,004\r\n17 0,072 0,041 0,132 0,193 (A) [%]"


def test_a_garbled_text_layer_is_detected_by_page_number() -> None:
    assert garbled_pages([CONTENTS, GARBLED, NUMBERS]) == [2]


def test_readable_and_empty_pages_are_not_flagged() -> None:
    assert garbled_pages([CONTENTS, NUMBERS, "", "   "]) == []
