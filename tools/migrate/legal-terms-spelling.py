"""Plan two reviewed spelling repairs in the German Terms of Sale.

Pass the resulting pair to the existing reviewed-page writer with its current
content and translation-metadata preimages. The English page is unchanged.
"""

REPAIRS = (
    (
        "Bei B2Bäufen geht die Gefahr auf den Käufer über, wenn die Ware dem Frachtführer übergeben wird.",
        "Bei B2B-Käufen geht die Gefahr auf den Käufer über, wenn die Ware dem Frachtführer übergeben wird.",
    ),
    (
        "Es gelten die gesetzlichen B2Bährleistungsrechte.",
        "Es gelten die gesetzlichen B2B-Gewährleistungsrechte.",
    ),
)


def plan_pair(english: str, german: str) -> tuple[str, str]:
    """Repair the exact pair of sentences, or refuse partial or drifted text."""
    counts = [(german.count(old), german.count(new)) for old, new in REPAIRS]
    if counts == [(0, 1)] * len(REPAIRS):
        return english, german
    if counts != [(1, 0)] * len(REPAIRS):
        raise ValueError(
            "The reviewed German Terms sentences changed or are incomplete"
        )
    for old, new in REPAIRS:
        german = german.replace(old, new, 1)
    return english, german
