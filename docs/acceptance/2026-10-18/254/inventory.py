"""Rebuild the reviewed discovery and segment inventory from saved live responses."""
import json
import pathlib
import urllib.parse
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
rows = json.loads((ROOT / 'plugins/linker-i18n/tests/fixtures/german-routes.json').read_text())
crawl = json.loads((HERE / 'live-crawl.json').read_text())
sitemaps = json.loads((HERE / 'live-sitemaps.json').read_text())
source = {}
for entry in crawl:
    path = urllib.parse.urlsplit(entry['url']).path
    source.setdefault(path, set()).add('crawl')
for entry in sitemaps:
    for loc in ET.fromstring(entry['xml']).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
        path = urllib.parse.urlsplit(loc.text).path
        if path.startswith('/de/'):
            source.setdefault(path, set()).add('sitemap')
reviewed = {r['old'] for r in rows}
assert set(source) <= reviewed, sorted(set(source) - reviewed)
report = ['# Live discovery and English segments', '',
          'Read-only Apify evidence, 2026-10-18. Sitemap run `7h540xcedbJaZbP1t`, dataset `QfBRrNIaDX8wp97dE`; crawl run `lmsSlRuDxc2Kc8uTa`, dataset `RNBfC286NwNzP0ZEn`. All five XML responses and all 165 crawl responses returned 200. Query strings were excluded from crawl deduplication.', '',
          f"Sitemap: {sum('sitemap' in v for v in source.values())} German URLs; crawl: {len(crawl)}; union: {len(source)}. Supplementary entries cover native account functions, reset, paging and historical category aliases. Confirmation and inquiry detail use owned ephemeral records in integration tests rather than publishing a real customer record.", '',
          'Descriptive English segments found: `category`, `applications-blog`, `battery-storage-blog`, `installation-commissioning`, `monitoring-energy-management`, `system-design`, `compare-products`, `faq-download`, `gateway`, `cloud`, `register`, `lost-password`, `service-support`, `ems-monitoring`, `all-in-one-systeme`, `page`; product phrases `battery`, `battery-module`, `battery-stack-bridge`, `lfp-battery-base`, `single-phase-hybrid`, `three-phase-hybrid`, `hybrid-inverter`, `power-module`, `all-in-one`, `flagship`, `ev-charger`, `smart-energy-controller`, `residential-energy-manager`, `data-collector`. Supplementary functional segments: `inquiries`, `inquiry`, `saved-solutions`, `documents`, `company`, `billing`, `shipping`, `edit-account`, `customer-logout`, `inquiry-received`.', '',
          'The German old draft word is prohibited customer vocabulary and is replaced by `loesungsentwurf`. Proper names EcoFlow, Ocean, GoodWe, SAJ, eManager, eSolar, EZManager and model/SKU tokens remain; technical abbreviations LFP, EMS, HEMS, EV, WiFi, LAN, Bluetooth, NFC, CT, AC/DC, kW/kWh, V and HV remain. `Blog`, `FAQ`, `Hybrid`, `Manager` and `Monitoring` in German copy are established loanwords, but descriptive English URL phrases above receive the explicit German forms in the table. No remaining segment is silently exempted as a product description.', '',
          '| Previous German URL | Discovery | New canonical URL |', '|---|---|---|']
for row in rows:
    report.append(f"| `{row['old']}` | {', '.join(sorted(source.get(row['old'], {'supplement'})))} | `{row['new']}` |")
(HERE / 'inventory.md').write_text('\n'.join(report) + '\n')
print({'sitemap': sum('sitemap' in v for v in source.values()), 'crawl': len(crawl), 'union': len(source), 'reviewed': len(rows)})
