"""Publish or restore the reviewed R3 marketing page pairs and registered WebPs."""

from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import reviewed_page_pair as pairs

PAGES = {
    "home": (13, 6913),
    "about": (862, 6865),
    "services-support": (2748, 6700),
    "solution": (746, 6871),
    "residential-storage": (749, 6923),
    "commercial-storage": (792, 6921),
    "utility-storage": (1755, 6917),
    "for-installer": (826, 6869),
    "for-epc": (842, 6867),
}
HERO = "linker-technical-support-and-documents"
STORY = "linker-trusted-on-commercial-bess"
KIT = "linker-the-kit-arrives-together"
PACK = "linker-packed-and-dispatched-as-one"
PHOTOS = (HERO, STORY, KIT, PACK)
WHATSAPP = '[linker_whatsapp style="outline"]'
EMAIL = '<a href="mailto:[linker_team_email]">[linker_team_email]</a>'
OLD_EMAIL = '<a href="mailto:sales@de-linker.com">sales@de-linker.com</a>'
ALT = {
    HERO: (
        "Technical support and documents for battery storage and inverter projects from Linker",
        "Technischer Support und Unterlagen für Batteriespeicher- und Wechselrichterprojekte von Linker",
    ),
    STORY: (
        "Commercial battery storage project",
        "Gewerbliches Batteriespeicherprojekt",
    ),
}


def edited(source: str, old: str, new: str) -> str:
    if new in source:
        return source
    if source.count(old) != 1:
        raise ValueError(f"Expected one reviewed page fragment: {old[:100]}")
    return source.replace(old, new, 1)


def insert_after(source: str, pattern: str, markup: str) -> str:
    match = re.search(pattern, source, re.S)
    if not match:
        raise ValueError(f"Missing page element: {pattern}")
    if source.startswith(markup, match.end()):
        return source
    return source[: match.end()] + markup + source[match.end() :]


def contacts(de: bool) -> str:
    def link(scheme: str, channel: str, display: str) -> str:
        return (
            f"<a href='{scheme}:[linker_contact channel=\"{channel}\"]'>"
            f'[linker_contact channel="{display}"]</a>'
        )

    labels = (
        ("Vertrieb", "Direktkontakt", "Deutschland", "Direkt")
        if de
        else ("Sales", "Direct contact", "Germany", "Direct")
    )
    links = (
        EMAIL,
        link("mailto", "direct_email", "direct_email"),
        link("tel", "germany_tel", "germany_phone"),
        link("tel", "direct_tel", "direct_phone"),
    )
    rows = "".join(
        f"<span><small>{label}</small> {item}</span>"
        for label, item in zip(labels, links, strict=True)
    )
    return f'<div class="lk-desk-channels">{rows}{WHATSAPP}</div>'


def photo_refs(content: str, page: str, de: bool, media: dict[str, Any]) -> str:
    names = {HERO: HERO, STORY: STORY, KIT + "-scaled": KIT, PACK: PACK}
    if page == "solution":
        names["linker-one-linker-for-utility-projects"] = STORY

    def photo(match: re.Match[str]) -> str:
        tag = match.group()
        src = re.search(r'\bsrc="([^"]+)"', tag)
        if not src:
            return tag
        name = names.get(Path(src[1]).stem)
        if not name:
            return tag
        image = media[name]
        attributes = {
            "src": image["src"],
            "srcset": image["srcset"],
            "width": str(image["width"]),
            "height": str(image["height"]),
        }
        if ' sizes="' not in tag:
            attributes["sizes"] = "(max-width: 760px) 90vw, 50vw"
        if name in ALT:
            attributes["alt"] = ALT[name][int(de)]
        for key, value in attributes.items():
            attr = f'{key}="{escape(value, quote=True)}"'
            if re.search(rf'\s{key}="[^"]*"', tag):
                tag = re.sub(rf'\s{key}="[^"]*"', " " + attr, tag, count=1)
            else:
                tag = re.sub(r"\s*/?>$", " " + attr + "/>", tag)
        return tag

    content = re.sub(r"<img\b[^>]*>", photo, content)
    for old, name in names.items():
        if name not in media:
            continue
        old_url = f"/wp-content/uploads/2026/09/{old}.webp"
        # The services photo stack, audience tiles and slideshow use the same media.
        content = content.replace(
            "url('" + old_url + "')", "url('" + media[name]["medium_large"] + "')"
        )
        content = content.replace("'" + old_url + "'", "'" + media[name]["src"] + "'")
    return content


def page_changes(page: str, language: str, content: str, media: dict[str, Any]) -> str:
    de = language == "de"
    if page == "home":
        label = "Direktkontakt für Fachpartner" if de else "Direct trade desk"
        return insert_after(
            content,
            r'<div class="hero-capsules" data-linker-planner-entry="home-hero">.*?</div>',
            f'<p class="home-direct-desk">{label}: [linker_whatsapp] · {EMAIL}</p>',
        )
    if page in {"about", "solution", "services-support"}:
        content = photo_refs(content, page, de, media)
    if page in {"solution", "services-support"}:
        head = content.index(OLD_EMAIL) if OLD_EMAIL in content else -1
        if head != -1:
            content = content[:head] + content[head:].replace(
                OLD_EMAIL,
                contacts(de)
                if page == "services-support"
                else EMAIL + " · [linker_whatsapp]",
                1,
            )
    if page == "solution":
        for old, new in (
            (
                ("GROSSSPEICHER-BESS · 2,5 MWH", "GEWERBLICHES BESS · 1,2 MWH"),
                ("Projekt mit 2,5 MWh", "Projekt mit 1,2 MWh"),
                (
                    "die Containerspezifikation",
                    "die Spezifikation des flüssigkeitsgekühlten Speichersystems",
                ),
            )
            if de
            else (
                ("UTILITY BESS · 2.5 MWH", "COMMERCIAL BESS · 1.2 MWH"),
                ("On a 2.5 MWh project", "On a 1.2 MWh project"),
                (
                    "coordinating the container specification",
                    "coordinating the liquid-cooled system specification",
                ),
            )
        ):
            content = edited(content, old, new)
    elif page == "services-support" and de:
        for old, new in (
            (
                "Aus dem Lager liefern wir ab. Bei Lieferungen berechnen wir die Fracht gesondert nach Zielort.",
                "Der Versand erfolgt ab unserem Lager in Deutschland. Die Frachtkosten berechnen wir gesondert nach Zielort.",
            ),
            (
                "<strong>Mit den Geräten</strong> Hinterlegte Handbücher und die für Genehmigung und Installation angeforderten Zertifikate.",
                "<strong>Mit der Lieferung:</strong> Hinterlegte Handbücher sowie die für Netzanschluss und Installation angeforderten Zertifikate.",
            ),
            (
                "koordiniert den Ersatz. <a",
                "koordiniert den Ersatz über unser Kontaktformular für <a",
            ),
            (">Garantie & Ersatzgeräte</a>.", ">Garantie &amp; Ersatzgeräte</a>."),
        ):
            content = edited(content, old, new)
    start = content.rindex("<section")
    end = content.index("</section>", start) + len("</section>")
    closing = content[start:end]
    if page == "about":
        closing = edited(
            closing, "</p></div><aside", "</p>[linker_whatsapp]</div><aside"
        )
        address = "Linker Technology GmbH · Steinfeldstraße 3, 39179 Barleben, "
        legal = (
            "Deutschland · Handelsregister: Amtsgericht Stendal HRB 33824 · USt-IdNr.: DE367367711"
            if de
            else "Germany · Commercial Register: Amtsgericht Stendal HRB 33824 · VAT ID: DE367367711"
        )
        line = f'<p class="lk-about-registration">{address}{legal}</p>'
        if not content.startswith(line, end):
            closing += line
    elif page == "for-epc":
        closing = insert_after(
            closing,
            r'\[linker_contact_invitation surface="epc-intake" compact="1"\]',
            WHATSAPP,
        )
    elif page == "commercial-storage":
        closing = edited(
            closing,
            '</p><a class="cs-cta-primary"',
            '<br>[linker_whatsapp]</p><a class="cs-cta-primary"',
        )
    elif page == "services-support":
        closing = edited(
            closing,
            "</div>\n</div>\n</section>",
            "</div>\n" + contacts(de) + "\n</div>\n</section>",
        )
    else:
        link = {
            "residential-storage": r'<a class="lk-btn lk-btn-secondary"[^>]*>.*?</a>',
            "utility-storage": r'<a class="lk-btn-hero-ghost"[^>]*>.*?</a>',
            "for-installer": r'<a class="lk-btn-outline"[^>]*>.*?</a>',
            "solution": r'<a class="lk-btn-outline"[^>]*>.*?</a>',
        }[page]
        closing = insert_after(closing, link, " " + WHATSAPP)
    return content[:start] + closing + content[end:]


def media_call(wp: str, **payload: Any) -> dict[str, Any]:
    source = (
        Path(__file__).with_name("batch-r3-media.php").read_text().removeprefix("<?php")
    )
    payload64 = base64.b64encode(json.dumps(payload).encode()).decode()
    args = shlex.split(wp)
    tail = ["eval", "eval(stream_get_contents(STDIN));"]
    cmd = args + ([shlex.join(tail)] if Path(args[0]).name == "ssh" else tail)
    result = subprocess.run(
        cmd,
        input=source.replace("__R3_MEDIA__", payload64),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:])
    return json.loads(result.stdout.split("@@r3-media@@")[-1])  # type: ignore[no-any-return]


def save(path: Path, value: dict[str, Any]) -> None:
    if not path.exists():
        with path.open("x") as out:
            json.dump(value, out, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument(
        "--assets", type=Path, help="Directory containing the four supplied R3 WebPs"
    )
    parser.add_argument("action", choices=("backup", "apply", "read", "restore"))
    args = parser.parse_args()
    folder = args.backup_dir
    folder.mkdir(parents=True, exist_ok=True)
    inventory = media_call(args.wp, mode="inventory", names=PHOTOS)
    path = folder / "media-before.json"
    if not path.exists() and args.action == "restore":
        raise ValueError("Missing media recovery point")
    save(path, inventory)
    baseline = json.loads(path.read_text())
    if baseline["site"] != inventory["site"]:
        raise ValueError("The recovery point belongs to a different site")
    before = {}
    for page, ids in PAGES.items():
        before[page] = pairs.read(args.wp, *ids)
        save(folder / f"{page}-before.json", before[page])
    if args.action == "backup":
        print(
            f"{inventory['site']}: 9 page pairs, {len(inventory['covers'])} PNG covers, footer and photo registrations"
        )
        return
    if args.action == "apply":
        if not args.assets:
            raise ValueError("--assets is required")
        for name in PHOTOS:
            image = (args.assets / f"{name}-r3.webp").read_bytes()
            media_call(
                args.wp, mode="photo", name=name, data=base64.b64encode(image).decode()
            )
        media_call(args.wp, mode="logo")
        for item in baseline["covers"]:
            media_call(args.wp, mode="cover", item=item)
        inventory = media_call(args.wp, mode="inventory", names=PHOTOS)
    if args.action in {"apply", "read"}:
        report = media_call(
            args.wp,
            mode="readback",
            ids=[item["id"] for item in baseline["covers"]],
            names=PHOTOS,
        )
        if (
            inventory["covers"]
            or not report["logo"]
            or not all(report["photos"].values())
        ):
            raise ValueError(
                "Media readback is missing a converted or registered image"
            )
    for page, ids in PAGES.items():
        current = before[page]
        backup = json.loads((folder / f"{page}-before.json").read_text())
        if current["home"] != backup["home"]:
            raise ValueError("Mismatched page recovery point")
        published = folder / f"{page}-published.json"
        if args.action == "restore":
            if current == backup:
                continue
            if not published.exists() or current != json.loads(published.read_text()):
                raise ValueError(f"{page} changed since publication")
            pairs.write(args.wp, ids, current, backup["pages"], backup["metadata"])
            continue
        after = {
            str(pid): page_changes(
                page, lang, current["pages"][str(pid)], report["photos"]
            )
            for lang, pid in zip(("en", "de"), ids, strict=True)
        }
        if after == current["pages"]:
            print(f"{page}: current")
            continue
        if args.action == "read" or current != backup:
            raise ValueError(f"{page} differs from its expected state")
        metadata = current["metadata"]
        if current["current"]:
            preview = pairs.invoke(
                args.wp,
                {
                    "mode": "preview_page_adoption",
                    "changes": pairs.changes(ids, current["pages"], after),
                },
            )
            metadata = preview["expected_metadata"]
        expected = current | {"pages": after, "metadata": metadata}
        save(published, expected)
        pairs.write(args.wp, ids, current, after, metadata, adopt=current["current"])
        print(f"{page}: published and read back", flush=True)
    if args.action == "restore":
        for item in baseline["covers"]:
            media_call(args.wp, mode="restore_cover", item=item)
        media_call(args.wp, mode="restore_registrations", before=baseline, names=PHOTOS)
    else:
        (folder / "media-readback.json").write_text(json.dumps(report, indent=2))
        print(
            f"{urlsplit(inventory['site']).netloc}: {len(report['covers'])} covers, 4 photos and footer read back"
        )


if __name__ == "__main__":
    main()
