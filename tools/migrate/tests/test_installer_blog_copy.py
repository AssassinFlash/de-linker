"""Reviewed copy changes the native bilingual article, including its public excerpt."""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "blog_copy", HERE / "installer-blog-copy.py"
)
assert spec and spec.loader
copy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(copy)
sys.path.pop(0)

PAIR = (553, 6887)


def backup_snapshot() -> dict[str, Any]:
    return {
        "pages": {
            "553": (
                "<h2>Start with your backup loads</h2>\r\n"
                "List every circuit you want to power during a grid outage: refrigerator, lights, router, security system, garage door opener. Sum their continuous watts and estimate daily kWh consumption by multiplying watts by hours of use.\r\n"
                "<h2>Apply the autonomy factor</h2>\r\n"
                "How many hours of backup without solar recharge? A typical European residential backup target is 8-24 hours for essential loads. Multiply daily kWh by autonomy hours divided by 24 to get the target usable capacity.\r\n"
                "<h2>Depth of discharge and usable capacity</h2>\r\n"
                "LFP batteries are typically rated at 90% depth of discharge. A 5 kWh LFP battery provides approximately 4.5 kWh of usable energy. Always size around usable, not nameplate, capacity.\r\n"
                "<h2>Plan for expansion</h2>\r\n"
                "Stackable battery systems let you start with one or two modules and add more later. Leave space in your rack and ensure your inverter can handle the expanded DC input range.\r\n"
                '<a href="/contact/">Request a project quote</a>'
            ),
            "6887": (
                "<h2>Beginnen Sie mit Ihren Backup-Lasten</h2>\r\n"
                "Listen Sie jeden Stromkreis auf, den Sie bei einem Netzausfall mit Strom versorgen möchten: Kühlschrank, Beleuchtung, Router, Sicherheitssystem, Garagentoröffner. Summieren Sie deren kontinuierliche Watt und schätzen Sie den täglichen kWh-Verbrauch, indem Sie die Watt mit den Nutzungsstunden multiplizieren.\r\n"
                "<h2>Wenden Sie den Autonomiefaktor an</h2>\r\n"
                "Wie viele Stunden Backup ohne Solaraufladung? Ein typisches europäisches Wohn-Backup-Ziel liegt bei 8-24 Stunden für wesentliche Lasten. Multiplizieren Sie die täglichen kWh mit den Autonomiestunden geteilt durch 24, um die Ziel-Nutzungskapazität zu erhalten.\r\n"
                "<h2>Entladetiefe und Nutzungskapazität</h2>\r\n"
                "LFP-Batterien sind typischerweise mit 90 % Entladetiefe bewertet. Eine 5-kWh-LFP-Batterie liefert ungefähr 4,5 kWh nutzbare Energie. Dimensionieren Sie immer um die nutzbare, nicht die Nennkapazität.\r\n"
                "<h2>Planen Sie für Erweiterungen</h2>\r\n"
                "Stapelbare Batteriespeichersysteme ermöglichen es Ihnen, mit einem oder zwei Modulen zu starten und später weitere hinzuzufügen. Lassen Sie Platz in Ihrem Rack und stellen Sie sicher, dass Ihr Wechselrichter den erweiterten DC-Eingangsbereich bewältigen kann.\r\n"
                '<a href="/de/kontakt/">Projektangebot anfordern</a>'
            ),
        },
        "excerpts": {
            "553": "A step-by-step method for calculating battery storage capacity based on daily load curves, backup duration targets, and depth-of-discharge constraints.",
            "6887": "Eine Schritt-für-Schritt-Methode zur Berechnung der Batteriespeicherkapazität basierend auf täglichen Lastkurven, Backup-Dauerzielen und Entladetiefe-Beschränkungen.",
        },
        "metadata": {"553": {}, "6887": {}},
        "current": True,
    }


def test_backup_example_shapes_both_articles_and_excerpts() -> None:
    before = backup_snapshot()
    payload = copy.plan_pair(PAIR, before)

    assert payload is not None
    assert payload["post_type"] == "post"
    assert payload["metadata_before"] == before["metadata"]
    english, german = payload["changes"]
    assert "1.2 kWh" in english["after"]
    assert "1,2 kWh" in german["after"]
    assert "4.5 kWh" in english["after"] and "SAJ" in english["after"]
    assert "4,5 kWh" in german["after"] and "SAJ" in german["after"]
    for item, link in ((english, "/contact/"), (german, "/de/kontakt/")):
        key = str(item["id"])
        assert item["before"] == before["pages"][key]
        assert item["before_excerpt"] == before["excerpts"][key]
        assert item["after_excerpt"] != item["before_excerpt"]
        assert f'href="{link}"' in item["after"]
        assert "8-24" not in item["after"]
    final = {
        **before,
        "pages": {str(item["id"]): item["after"] for item in (english, german)},
        "excerpts": {
            str(item["id"]): item["after_excerpt"] for item in (english, german)
        },
    }
    assert copy.plan_pair(PAIR, final) is None
    with pytest.raises(ValueError, match="translation baseline"):
        copy.plan_pair(PAIR, {**final, "current": False})
    with pytest.raises(ValueError, match="partial"):
        copy.plan_pair(PAIR, {**final, "excerpts": before["excerpts"]})


def test_changed_excerpt_blocks_the_pair() -> None:
    before = backup_snapshot()
    before["excerpts"]["6887"] = "Nach der Prüfung redaktionell geändert."
    with pytest.raises(ValueError, match="6887.*excerpt"):
        copy.plan_pair(PAIR, before)
