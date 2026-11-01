"""Reviewed manufacturer manual declarations and original passage spans.

Each anchor and passage is pinned to the complete cached-source text digest.
They are independently checked against current Woo associations at build and
retrieval. Addition requires source-page and authored-section review.
"""

from typing import Any

RECORDS: list[dict[str, Any]] = [
    {
        "sha256": "a470d6e1be68e843b42a11a2f4ba05c67b9a8d01bdb6abc1f58bce9762701ea6",
        "kind": "series",
        "series": ["H2", "HS2", "HS3"],
        "anchor_id": "a470d6e1be68-p7-b690879d",
        "anchor_sha256": "b9d180fe25219ac405bff30fa5091c4f9293446c4c46ef332128304383fb1741",
        "anchor_quote": "This document provides the guidance on how to configure the SAJ inverters, "
        "mainly covering the required devices, system connections, meter address "
        "settings, and system commissioning using elekeeper App. It is designed for the "
        "following SAJ inverter models:\n"
        "⚫ H2 series\n"
        "⚫ HS2/AS2 series\n"
        "⚫ HS3/AS3 series\n"
        "Note: For the system connection diagrams in this document, the inverters are "
        "connected to the PV array, which is applicable for models like H2/HS2/HS3 "
        "series. However, for the AS series, the inverters are not connected to the PV "
        "array.",
        "source_id": "a470d6e1be68-p34-0abaea56",
        "source_sha256": "2656e7790c57ba7ebc71f5d4e0c6409e4d2e9f82d1182c621324db36f8f83856",
        "source_page": 34,
        "source_section": "6. System commissioning",
        "excerpt": "The elekeeper (used to be called eSAJ Home) App can be used for both nearby and "
        "remote monitoring. It communicates with different devices through Bluetooth or "
        "Ethernet connection.\n"
        "Note: The detailed operations on the App might vary, depending on the version you "
        "are using.",
        "source_picture": "",
        "reviewed_reset": {
            "id": "a470d6e1be68-p34-0abaea56",
            "heading": "6. System commissioning",
            "section": "6. System commissioning",
            "text_sha256": "2656e7790c57ba7ebc71f5d4e0c6409e4d2e9f82d1182c621324db36f8f83856",
            "reason": "The preceding DTSU666 heading is the previous chapter meter table; "
            "chapter 6 starts app commissioning.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "DTSU666",
                        "source_chunk_id": "a470d6e1be68-p33-3b936526",
                        "heading_path": [],
                    },
                    "source_text_sha256": "29f5aff49c470f219285f0bcdf526f2f2a812e6428a8991a714072b89143a330",
                }
            ],
        },
    },
    {
        "sha256": "a470d6e1be68e843b42a11a2f4ba05c67b9a8d01bdb6abc1f58bce9762701ea6",
        "kind": "series",
        "series": ["H2", "HS2", "HS3"],
        "anchor_id": "a470d6e1be68-p7-b690879d",
        "anchor_sha256": "b9d180fe25219ac405bff30fa5091c4f9293446c4c46ef332128304383fb1741",
        "anchor_quote": "This document provides the guidance on how to configure the SAJ inverters, "
        "mainly covering the required devices, system connections, meter address "
        "settings, and system commissioning using elekeeper App. It is designed for the "
        "following SAJ inverter models:\n"
        "⚫ H2 series\n"
        "⚫ HS2/AS2 series\n"
        "⚫ HS3/AS3 series\n"
        "Note: For the system connection diagrams in this document, the inverters are "
        "connected to the PV array, which is applicable for models like H2/HS2/HS3 "
        "series. However, for the AS series, the inverters are not connected to the PV "
        "array.",
        "source_id": "a470d6e1be68-p32-37706f28",
        "source_sha256": "d24ff1abe6069250dcfc63d8c8b34c4037caf738eec7f1bb2241ff14abde4fd7",
        "source_page": 32,
        "source_section": "5. Meter address settings",
        "excerpt": "If two meters are used, the inverter-side meter address must be set to 2. Do NOT "
        "change the default address 1 of the grid-side meter.",
        "source_picture": "",
    },
    {
        "sha256": "26a5052fc8597f7d900ceb6d8aef4d2b75c7fd27efd3658eb55fb2077fbfe682",
        "kind": "models",
        "series": [],
        "anchor_id": "26a5052fc859-p10-8f6f5356",
        "anchor_sha256": "485a89aaffaa2b5b5762e8a89d10e65b5f44141d533633180485a24525fbcb23",
        "anchor_quote": "| Hybrid- Wechselricht er | GW50K-ET-L-G10 GW75K-ET-G10 GW80K-ET-G10 "
        "GW99.99K-ET-G10 GW100K-ET-G10 |  |",
        "source_id": "26a5052fc859-p7-c6eba04e",
        "source_sha256": "b738ae0bb9f15458cb82f9a0b568236165f18b90f3b426b0bb242fd3a3d4756b",
        "source_page": 7,
        "source_section": "1.1 Netzeinspeisungsszenario",
        "excerpt": "Das System ist stets mit dem Netz verbunden und läuft synchron, folgt dem Prinzip "
        '"Eigenverbrauch, Überschuss ins Netz". Die Photovoltaik-Stromerzeugung wird '
        "vorrangig für lokale Lasten genutzt, der Energiespeicher lädt/entlädt je nach "
        "Strompreiszeit oder Betriebsart, um wirtschaftliche Funktionen wie "
        "Peak-ValleyArbitrage und Lastmanagement zu realisieren.",
        "source_picture": "",
    },
    {
        "sha256": "26a5052fc8597f7d900ceb6d8aef4d2b75c7fd27efd3658eb55fb2077fbfe682",
        "kind": "models",
        "series": [],
        "anchor_id": "26a5052fc859-p10-8f6f5356",
        "anchor_sha256": "485a89aaffaa2b5b5762e8a89d10e65b5f44141d533633180485a24525fbcb23",
        "anchor_quote": "| Hybrid- Wechselricht er | GW50K-ET-L-G10 GW75K-ET-G10 GW80K-ET-G10 "
        "GW99.99K-ET-G10 GW100K-ET-G10 |  |",
        "source_id": "26a5052fc859-p7-e09ad72c",
        "source_sha256": "ba674ffc6ba54e35d2a605e9c065d88d70204ab08ffc973255fd5c603a78fcdb",
        "source_page": 7,
        "source_section": "Merkmal",
        "excerpt": "Das System ist auf das Stromnetz angewiesen. ·\n"
        "Bei einem Stromausfall muss der Wechselrichter sofort die Ausgabe einstellen und "
        "kann die Last nicht mit Strom versorgen. ·",
        "source_picture": "",
    },
    {
        "sha256": "f66efb70d0d8927a92355980e0a0bd09359f580664976e082c4e510320e6d5a0",
        "kind": "models",
        "series": [],
        "anchor_id": "f66efb70d0d8-p10-c49f4cbd",
        "anchor_sha256": "f8d15095f803576363090938be259bb165ee996ff1f6e639115766e0deb4638e",
        "anchor_quote": "| Hybrid Inverter | GW50K-ET-L-G10 GW75K-ET-G10 GW80K-ET-G10 GW99.99K-ET-G10 "
        "GW100K-ET-G10 |  |",
        "source_id": "f66efb70d0d8-p7-1bb074fd",
        "source_sha256": "331b3dc7a2e9186a3c7f92bd62ea438484f993710c038703f37526a5d75f69c7",
        "source_page": 7,
        "source_section": "1.1 Grid-Tied Scenario",
        "excerpt": "The system always remains connected to and synchronously operates with the grid, "
        'following the principle of "Self-consumption, with surplus electricity fed into the '
        'grid". PV generation is prioritized for local loads, and the energy storage system '
        "charges/discharges according to tariff periods or Operating Mode to achieve economic "
        "functions such as peak-valley arbitrage and demand management.",
        "source_picture": "",
    },
    {
        "sha256": "f66efb70d0d8927a92355980e0a0bd09359f580664976e082c4e510320e6d5a0",
        "kind": "models",
        "series": [],
        "anchor_id": "f66efb70d0d8-p10-c49f4cbd",
        "anchor_sha256": "f8d15095f803576363090938be259bb165ee996ff1f6e639115766e0deb4638e",
        "anchor_quote": "| Hybrid Inverter | GW50K-ET-L-G10 GW75K-ET-G10 GW80K-ET-G10 GW99.99K-ET-G10 "
        "GW100K-ET-G10 |  |",
        "source_id": "f66efb70d0d8-p7-3fe358be",
        "source_sha256": "7a470e73dbd2b30ce0a97912bbc7626fa64d38a0bbf9f39fb3d0eae9492847ec",
        "source_page": 7,
        "source_section": "Features",
        "excerpt": "The system relies on the grid for operation. ·\n"
        "In the event of a Grid Power Outage, the inverter must immediately stop output and "
        "cannot supply power to the load. ·",
        "source_picture": "",
    },
    {
        "sha256": "f66efb70d0d8927a92355980e0a0bd09359f580664976e082c4e510320e6d5a0",
        "kind": "models",
        "series": [],
        "anchor_id": "f66efb70d0d8-p12-e632ac07",
        "anchor_sha256": "a827a852ef7594cf489de6ff50d320e08fe4f03ddda13755e1b173b61029e769",
        "anchor_quote": "|  | BAT-C series GW208.9-BAT-LC- G10 | The battery system supports up to4 "
        "units in parallel clusters |",
        "source_id": "f66efb70d0d8-p9-dab35264",
        "source_sha256": "8ff1ff34197e07160f2fb952879187dd3e772d750bba68907bff457fdb0ea363",
        "source_page": 9,
        "source_section": "NOTE",
        "excerpt": "BAT-C 92.1-112.6kWh,BAT-C 208.9kWh\n"
        "The battery has a built-in Ezlink module. Each inverter connects to the battery "
        "system via a smart communication stick, and the battery system transmits parallel "
        "operation information to the smart energy control box.",
        "source_picture": "",
    },
    {
        "sha256": "4cc6c9d37afa6f50bd300c152aa759408dce34403b38e6c610c1ba693263c592",
        "kind": "models",
        "series": [],
        "anchor_id": "4cc6c9d37afa-p3-1f84a418",
        "anchor_sha256": "23847da18cfa4a74b6fb71b9e16235a742ae45284bb6fd3fd50417d479522c30",
        "anchor_quote": "DTSU666 three phase Smart meter (Din-rail) (hereinafter referred to as the "
        '"instrument") is designed based on power monitoring and energy metering demands '
        "for electric power system, communication industry, construction industry, etc. "
        "as a new generation of intelligent instrument combining measurement and "
        "communication function, mainly applied into the measurement and display for the "
        "electric parameters in the electric circuit including three voltage, three "
        "current, active power, reactive power, frequency, positive& negative energy, "
        "four-quadrant energy, etc. Adopting the standard DIN35mm din rail mounting and "
        "modular design, it is characterized with small volume, easy installation and "
        "easy networking, widely applied into the internal energy monitoring and "
        "assessment for industrial and mining enterprises, hotels, schools, large public "
        "buildings.\n"
        "Complied standards:\n"
        "IEC 61010-1ɅSafety requirements for electrical equipment for "
        "measurementθcontrol and laboratory use Part1:General requirementsɆ\n"
        "IEC 61326-1ɅElectrical equipment for measurementθcontrol and laboratory use "
        "-EMC requirements Part1:General requirementsɆ\n"
        "MODUS-RTU protocol.",
        "source_id": "4cc6c9d37afa-p3-1f84a418",
        "source_sha256": "23847da18cfa4a74b6fb71b9e16235a742ae45284bb6fd3fd50417d479522c30",
        "source_page": 3,
        "source_section": "Main application & applicable range",
        "excerpt": "DTSU666 three phase Smart meter (Din-rail) (hereinafter referred to as the "
        '"instrument") is designed based on power monitoring and energy metering demands for '
        "electric power system, communication industry, construction industry, etc. as a new "
        "generation of intelligent instrument combining measurement and communication "
        "function, mainly applied into the measurement and display for the electric "
        "parameters in the electric circuit including three voltage, three current, active "
        "power, reactive power, frequency, positive& negative energy, four-quadrant energy, "
        "etc. Adopting the standard DIN35mm din rail mounting and modular design, it is "
        "characterized with small volume, easy installation and easy networking, widely "
        "applied into the internal energy monitoring and assessment for industrial and mining "
        "enterprises, hotels, schools, large public buildings.\n"
        "Complied standards:\n"
        "IEC 61010-1ɅSafety requirements for electrical equipment for measurementθcontrol and "
        "laboratory use Part1:General requirementsɆ\n"
        "IEC 61326-1ɅElectrical equipment for measurementθcontrol and laboratory use -EMC "
        "requirements Part1:General requirementsɆ\n"
        "MODUS-RTU protocol.",
        "source_picture": "",
        "reviewed_reset": {
            "id": "4cc6c9d37afa-p3-1f84a418",
            "heading": "1 Brief Introduction",
            "section": "Main application & applicable range",
            "text_sha256": "23847da18cfa4a74b6fb71b9e16235a742ae45284bb6fd3fd50417d479522c30",
            "reason": "The earlier cover heading is the drawing identifier, followed by "
            "the explicit DTSU666 product introduction.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "ZTW0.464.0104",
                        "source_chunk_id": "4cc6c9d37afa-p1-e99ed2c2",
                        "heading_path": [],
                    },
                    "source_text_sha256": "4a1c8877e5eba3e36d084dabbabf23341f13655f98168c16c68a5123a8f345a2",
                }
            ],
        },
    },
    {
        "sha256": "6fbecc0583033f303bfe27c992401d017b2549d09ab668090559db10fb72bffb",
        "kind": "models",
        "series": [],
        "anchor_id": "6fbecc058303-p1-03936a33",
        "anchor_sha256": "a0ca7a83e3b5618774660735db2956fbc520e38e362d91462cac736aa096ee61",
        "anchor_quote": "GM330 GMK330 GMK360",
        "source_id": "6fbecc058303-p16-c733556f",
        "source_sha256": "0e5fdf3a2740e3d34d6e70d5d2f47fdcada44e8937ca558d5857017e1c24b3c7",
        "source_page": 16,
        "source_section": "4.2 Power ON",
        "excerpt": "Step 1: Connect the smart meter cables.\n"
        "Step 2: Turn on the breaker on the voltage input side. Then the smart meter is "
        "powered on.",
        "source_picture": "",
        "reviewed_reset": {
            "id": "6fbecc058303-p16-922c9466",
            "heading": "4 Device Commission",
            "section": "4.1 Check before Power ON",
            "text_sha256": "24e565f25d445e9e8aa030822ad7b0bfd6c7b4714ecb548ac032d7a1e1b8c772",
            "reason": "The model-specific CT and wiring instructions belong to chapter 3; "
            "chapter 4 states general commissioning.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "GMK330",
                        "source_chunk_id": "6fbecc058303-p6-7ad38e23",
                        "heading_path": [],
                    },
                    "source_text_sha256": "db85758d7caf88ce842c0d306abf9c39fcf4c25d7cca8fdabe8db44a732b4a64",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "GMK360",
                        "source_chunk_id": "6fbecc058303-p6-f8f78d8e",
                        "heading_path": [],
                    },
                    "source_text_sha256": "783d967bd7853f36766dc45d435b5dacd3686f881da8d0d7a446a3bacae9a055",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "GMK330",
                        "source_chunk_id": "6fbecc058303-p10-5f404433",
                        "heading_path": [],
                    },
                    "source_text_sha256": "5f093b43e8de5c5c2e8d3111b1a186a32ef59b790057e5b8bf4f7bb40d8ae9df",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "GMK360",
                        "source_chunk_id": "6fbecc058303-p11-8ff0f926",
                        "heading_path": [],
                    },
                    "source_text_sha256": "27799051c6690cd3ad0155d1c7013a7f121f61b550e07d5611e3bfef93e96433",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "GM330 (three phase four wire)",
                        "source_chunk_id": "6fbecc058303-p12-a08c6520",
                        "heading_path": [],
                    },
                    "source_text_sha256": "7d1ebf1182213026a4154587b0abf6ebd29e193f8053e0615490e864f5f5b135",
                },
                {
                    "boundary": {
                        "kind": "declaration",
                        "quote": "For GM330 only. ·\n"
                        "Prepare the CT or contact the device "
                        "manufacturer for purchasing. ·\n"
                        "Specifications of the CT: ·\n"
                        "on the actual needs. 5A: the output "
                        "current of the secondary current of the "
                        "CT.) current of the CT, n ranges from 200 "
                        "to 5000. Set the current value depending "
                        "Set the current transformation ratio of "
                        "the CT to nA/5A. (nA: For primary\n"
                        "The recommended precision of the CT: "
                        "0.5/0.5s, 0.2/0.2s. Ensure the sampling "
                        "error for the CT current shall be ≤1%. ○\n"
                        "The CT bore diameter shall be bigger than "
                        "the outer diameter of AC power cable, to "
                        "ensure the AC power cable can be inserted "
                        "through CT. ·\n"
                        "To maintain metering accuracy, the total "
                        "length of the extended CT cable must not "
                        "exceed 30m. ·\n"
                        "Do not use network cable as CT cable, as "
                        "excessive current may cause damage to the "
                        "meter. ·\n"
                        "The dimension and appearance of the CT "
                        "differs slightly according to its type "
                        "provided by the device manufacturer. "
                        "However, the installation and wiring "
                        "methods are the same. ·\n"
                        "For specific CT wirings, refer to the "
                        "documents provided by the respective "
                        "manufacturer. ·",
                        "source_chunk_id": "6fbecc058303-p14-31c914d9",
                        "heading_path": [],
                    },
                    "source_text_sha256": "511f2b28edbd602a9c0fa2afa023f8d5dbbf9fb8a4ad61a8b2878f3c7a1ff5fb",
                },
            ],
        },
    },
    {
        "sha256": "29bb252c549a77f14893ae7d8d45164f4906636269cf8b7a863e1109d91c6d20",
        "kind": "models",
        "series": [],
        "anchor_id": "29bb252c549a-p4-b0e65f43",
        "anchor_sha256": "58e1b3c58a384f7ab8510fe071c7b6a9e5717753ac9b5d7b22b9d477e190a314",
        "anchor_quote": "| Wechselr ichter | GW5K-ETA-G20 GW6K-ETA-G20 GW8K-ETA-G20 GW9.999K-ETA- G20 "
        "GW10K-ETA-G20 GW12K-ETA-G20 GW15K-ETA-G20 GW20K-ETA-G20 GW25K-ETA-G20 "
        "GW29.999K-ETA- G20 GW30K-ETA-G20 GW5K-BTA-G20 GW6K-BTA-G20 GW8K-BTA-G20 "
        "GW9.999K-BTA- G20 GW10K-BTA-G20 GW12K-BTA-G20 GW15K-BTA-G20 GW20K-BTA-G20 "
        "GW25K-BTA-G20 GW29.999K-BTA- G20 | Nennausgangsleistung: 5 kW-30 kW |",
        "source_id": "29bb252c549a-p62-8fa27ec4",
        "source_sha256": "4e7c70e9a9cad05825e0e27a8378a58384f64dd1f9d5f798c659f88ec09c37b0",
        "source_page": 62,
        "source_section": "Eigenverbrauch",
        "excerpt": "Basismodus des Systembetriebs. ·\n"
        "Die PV-Erzeugung versorgt zuerst die Last, überschüssige Energie lädt die Batterie, "
        "und die verbleibende Energie wird ins Netz eingespeist. Wenn die PV-Erzeugung den "
        "Lastbedarf nicht deckt, wird die Last von der Batterie versorgt; wenn auch die "
        "Batteriekapazität den Lastbedarf nicht deckt, wird die Last vom Netz versorgt. ·",
        "source_picture": "",
    },
    {
        "sha256": "67a7f715ca9db734edba1b4f15b50d1a29c866b172ffd1909759e0abc66c8d2a",
        "kind": "models",
        "series": [],
        "anchor_id": "67a7f715ca9d-p4-b97f02f3",
        "anchor_sha256": "92294632929e364efebef3439de0bed4221fa78e76bbe8c1bec814fd489faf7b",
        "anchor_quote": "| inverter | GW5K-ETA-G20 GW6K-ETA-G20 GW8K-ETA-G20 GW9.999K-ETA- G20 "
        "GW10K-ETA-G20 GW12K-ETA-G20 GW15K-ETA-G20 GW20K-ETA-G20 GW25K-ETA-G20 "
        "GW29.999K-ETA- G20 GW30K-ETA-G20 GW5K-BTA-G20 GW6K-BTA-G20 GW8K-BTA-G20 "
        "GW9.999K-BTA- G20 GW10K-BTA-G20 GW12K-BTA-G20 GW15K-BTA-G20 GW20K-BTA-G20 "
        "GW25K-BTA-G20 GW29.999K-BTA- G20 | Rated Output Power: 5 kW - 30 kW |",
        "source_id": "67a7f715ca9d-p59-48f66581",
        "source_sha256": "f603b6304f11177953cccb050fe40aa370f794505836969c5ccbc3a594f8781d",
        "source_page": 59,
        "source_section": "Self-consumption",
        "excerpt": "Basic mode of system operation. ·\n"
        "PV generation supplies power to loads first, excess power charges the battery, and "
        "any remaining power is sold to the grid. When PV generation cannot meet load demand, "
        "the battery supplies power to loads; when battery power also cannot meet load "
        "demand, the grid supplies power to loads. ·",
        "source_picture": "",
    },
    {
        "sha256": "50bdd49b7be0ef036cafec286994f33af79dab5fc54dfcebbf4549f7e429acf9",
        "kind": "models",
        "series": [],
        "anchor_id": "50bdd49b7be0-p7-ef31d95d",
        "anchor_sha256": "484cf5af46b460de78e50a40994469b6a8352dc670c8085a8fcddc14ae0b7e05",
        "anchor_quote": "GW50K-ETR-L-G10 • GW75K-ETR-L-G10 • GW75K-ETR-G10 • GW80K-ETR-G10 • "
        "GW99.99K-ETR-G10 • GW100K-ETR-G10 • GW110K-ETR-G10 • GW124.99K-ETR-G10 • "
        "GW125K-ETR-G10 •",
        "source_id": "50bdd49b7be0-p77-92669e02",
        "source_sha256": "26aea2223e07788e0f3d14837304887a754488745822a403cfbd16a202651efb",
        "source_page": 77,
        "source_section": "8.3.1 LCD Overview",
        "excerpt": "Users can perform the following operations through the LCD screen:\n"
        "View device operation data, software version, fault information, etc. ·\n"
        "Set parameters, safety regulation regions, anti-reverse flow, etc. ·",
        "source_picture": "",
    },
    {
        "sha256": "50bdd49b7be0ef036cafec286994f33af79dab5fc54dfcebbf4549f7e429acf9",
        "kind": "models",
        "series": [],
        "anchor_id": "50bdd49b7be0-p7-ef31d95d",
        "anchor_sha256": "484cf5af46b460de78e50a40994469b6a8352dc670c8085a8fcddc14ae0b7e05",
        "anchor_quote": "GW50K-ETR-L-G10 • GW75K-ETR-L-G10 • GW75K-ETR-G10 • GW80K-ETR-G10 • "
        "GW99.99K-ETR-G10 • GW100K-ETR-G10 • GW110K-ETR-G10 • GW124.99K-ETR-G10 • "
        "GW125K-ETR-G10 •",
        "source_id": "50bdd49b7be0-p74-ccd1a179",
        "source_sha256": "302a13879fe7204497b7ecd602cd3d9cbf585605a73ca9fbe509fc19feb9ce01",
        "source_page": 74,
        "source_section": "7.2 Powering On the Device",
        "excerpt": "(Optional) Close the DC circuit breaker between the inverter and the battery system. "
        "1.\n"
        "Power on the battery system. 2.\n"
        'Rotate the DC switch on the inverter to the "ON" position. 3.\n'
        "(Optional) Close the DC circuit breaker between the inverter and the PV. 4.\n"
        "Close the AC circuit breaker connected to the grid. 5.\n"
        "Close the AC circuit breaker connected to the loads. 6.\n"
        "Close the AC circuit breaker connected to the diesel generator. 7.\n"
        "(Optional) Close the AC circuit breaker between the inverter and the STS. 8.",
        "source_picture": "",
    },
    {
        "sha256": "894ef3bd6daca659dfb5b605d7fe52fc13f89262144d80be3387a8cd2efd0a75",
        "kind": "models",
        "series": [],
        "anchor_id": "894ef3bd6dac-p1-b23438aa",
        "anchor_sha256": "bffb78c9256f22ee180299d3d185a374e48f6975b204e48bb624cc1ee24846d1",
        "anchor_quote": "GW5.1-BAT-D-G20 GW8.3-BAT-D-G20 GW5.1-BAT-D-G21 GW8.3-BAT-D-G21 GW6.0-BAT-D-G20 "
        "GW9.0-BAT-D-G20",
        "source_id": "894ef3bd6dac-p51-75762307",
        "source_sha256": "03fffeef9a5836b603c6b36f4082c0b9f0b78257b52d5a8c2add7db732978b8b",
        "source_page": 51,
        "source_section": "Battery System Appearance Description:",
        "excerpt": "The battery system can store and release electricity according to the requirements "
        "of the photovoltaic energy storage system. The input and output ports of this energy "
        "storage system are both high voltage direct current.",
        "source_picture": "",
    },
    {
        "sha256": "d5167d27d5e47d8d61d059862c6812963e0bb65d055dfb65aaecdbd32b87cbd1",
        "kind": "models",
        "series": [],
        "anchor_id": "d5167d27d5e4-p24-74d7d8ce",
        "anchor_sha256": "28732ed6578b6d679a71c147f15d902cbeb8e892bde03aea445f9b487342527d",
        "anchor_quote": "| Energy Storage System | GW100/261-ESA-LCN-G10 • GW100/261-ESA-LCN-G11 • "
        "GW125/261-ESA-LCN-G10 • GW125/261-ESA-LCN-G11 • | Purchase from GoodWe. For the "
        "same project, the model and specifications of the energy storage systems should "
        "remain consistent; mixing products is not recommended. Paired with 500K STS: "
        "n<=5 • Paired with 250K STS: n<=2 • |",
        "source_id": "d5167d27d5e4-p54-bb693b5e",
        "source_sha256": "25546aee0f200dfd54b516ae7e12c807091b296fbb3d4d85f12dc5cddff96bc2",
        "source_page": 54,
        "source_section": "3.1 Self-consumption Mode",
        "excerpt": "Self-consumption is applicable to PV energy storage systems with a high PV ratio, "
        "where PV generation is sufficient to supply loads. Surplus generation power charges "
        "the energy storage. It is mainly suitable for scenarios with low or no Export Tariff "
        "subsidy, improving the system's Self-consumption rate and energy self-sufficiency "
        "rate, and reducing electricity expenses. PV generation supplies loads "
        "preferentially, and surplus generation power charges the energy storage. If the "
        "energy storage is fully charged or charging at full power, the surplus Energy "
        "Generation is exported to the grid. When generation is insufficient or there is no "
        "PV generation at night, the energy storage discharges to supply loads. The grid "
        "cannot charge the energy storage, but can supply power to loads.",
        "source_picture": "",
    },
    {
        "sha256": "6bdd27e577fc5eafa47db8fa0a9bbc8dd6a60aa1013e182350a35f305338a7a7",
        "kind": "models",
        "series": [],
        "anchor_id": "6bdd27e577fc-p22-5b9e9528",
        "anchor_sha256": "7f380d4bbaf46ac0147dc5f4affe72a4a6b7ce23e928c2660b0a10fbfbe7ec10",
        "anchor_quote": "| Energy Storage System | GW125/261-ESA-LCN-G10 • GW125/261-ESA-LCN-G11 • "
        "GW100/261-ESA-LCN-G10 • GW100/261-ESA-LCN-G11 • | Supports up to 8 energy "
        "storage systems in master-slave parallel operation. Ensure that the model and "
        "specifications of energy storage systems in the same system remain consistent; "
        "mixing products is not recommended. Purchase from GoodWe. |",
        "source_id": "6bdd27e577fc-p36-bb693b5e",
        "source_sha256": "25546aee0f200dfd54b516ae7e12c807091b296fbb3d4d85f12dc5cddff96bc2",
        "source_page": 36,
        "source_section": "3.1 Self-consumption Mode",
        "excerpt": "Self-consumption is applicable to PV energy storage systems with a high PV ratio, "
        "where PV generation is sufficient to supply loads. Surplus generation power charges "
        "the energy storage. It is mainly suitable for scenarios with low or no Export Tariff "
        "subsidy, improving the system's Self-consumption rate and energy self-sufficiency "
        "rate, and reducing electricity expenses. PV generation supplies loads "
        "preferentially, and surplus generation power charges the energy storage. If the "
        "energy storage is fully charged or charging at full power, the surplus Energy "
        "Generation is exported to the grid. When generation is insufficient or there is no "
        "PV generation at night, the energy storage discharges to supply loads. The grid "
        "cannot charge the energy storage, but can supply power to loads.",
        "source_picture": "",
    },
    {
        "sha256": "5876178f27d0d899eb0742974b2fd0e7e7885a28638801424d698c9499104c27",
        "kind": "models",
        "series": [],
        "anchor_id": "5876178f27d0-p1-a883e609",
        "anchor_sha256": "c2f0cd31256884b4b677ad2f50a31c186c420b20ca468cfa17123c6ee15c7cea",
        "anchor_quote": "GW125/261-ESA-LCN-G10\nGW125/261-ESA-LCN-G11|",
        "source_id": "5876178f27d0-p75-e0092d5a",
        "source_sha256": "8d0a5d26ae9b7390d390be38f6ec55f774dcc01dd1ad600cfe866913abbd5f33",
        "source_page": 75,
        "source_section": "6.2 Gerät Leistung Einschalten",
        "excerpt": "Schritt 1: QF2 schließen (DC-Leistungsschalter).\n"
        "Schritt 2: QF1 schließen (AC-Formgehäuse-Leistungsschalter).\n"
        "Schritt 3: Q2 schließen (DC-Hilfsschalter).\n"
        "Schritt 4: Q1 schließen (AC-Hilfsschalter).\n"
        "Schritt 5: Die Vordertür schließen. Nachdem die RUN-Anzeige von weiß auf grün "
        "wechselt, schließt das System den Netzanschluss ab.",
        "source_picture": "",
        "reviewed_reset": {
            "id": "5876178f27d0-p75-e0092d5a",
            "heading": "6 System Inbetriebnahme",
            "section": "6.2 Gerät Leistung Einschalten",
            "text_sha256": "8d0a5d26ae9b7390d390be38f6ec55f774dcc01dd1ad600cfe866913abbd5f33",
            "reason": "The variant-specific MSD and battery-power-cable setup is section "
            "5.5; chapter 6 gives system power-on.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "ESA-Serie 125kW/261kW",
                        "source_chunk_id": "5876178f27d0-p1-a883e609",
                        "heading_path": [],
                    },
                    "source_text_sha256": "c2f0cd31256884b4b677ad2f50a31c186c420b20ca468cfa17123c6ee15c7cea",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "Parallelschaltung über SEC3000C ■",
                        "source_chunk_id": "5876178f27d0-p53-9586161d",
                        "heading_path": [],
                    },
                    "source_text_sha256": "5a24f91c02e1332acfdcd7b9cd97bbada42d1c840b771941e6ec845589764b58",
                },
                {
                    "boundary": {
                        "kind": "declaration",
                        "quote": "Nur der GW125/261-ESA-LCN-G10 erfordert "
                        "den Aufbau des MSD-Schalters. ·\n"
                        "Nur der GW125/261-ESA-LCN-G11 erfordert "
                        "den Aufbau des BatterieLeistungskabels. ·",
                        "source_chunk_id": "5876178f27d0-p72-434b1702",
                        "heading_path": [],
                    },
                    "source_text_sha256": "e79bac0ad66fe27c597fe9a9222f55aa4945a5015995a73183e4e822ffae855b",
                },
            ],
        },
    },
    {
        "sha256": "5876178f27d0d899eb0742974b2fd0e7e7885a28638801424d698c9499104c27",
        "kind": "models",
        "series": [],
        "anchor_id": "5876178f27d0-p1-a883e609",
        "anchor_sha256": "c2f0cd31256884b4b677ad2f50a31c186c420b20ca468cfa17123c6ee15c7cea",
        "anchor_quote": "GW125/261-ESA-LCN-G10\nGW125/261-ESA-LCN-G11|",
        "source_id": "5876178f27d0-p76-36f1d94d",
        "source_sha256": "71d994a2a9048da00bf18c5b11b5615371ed6cc7a69d6e722957b2dc830f8f70",
        "source_page": 76,
        "source_section": "7.1 Einstellen der Geräteparameter über die SolarGo APP",
        "excerpt": "SolarGo APP ist eine mobile Anwendung, die über Bluetooth mit dem "
        "Energiespeichersystem kommunizieren kann. Im Folgenden sind die gängigen Funktionen "
        "von SolarGo aufgeführt:\n"
        "Anzeigen von Gerätebetriebsdaten, Softwareversion, Alarminformationen usw. ·\n"
        "Einstellen von Gerätenetzparametern, Kommunikationsparametern, Sicherheitsregion, "
        "Rückflusssperre usw. ·\n"
        "Wartung des Geräts. ·\n"
        'Für detaillierte Funktionen lesen Sie bitte das "SolarGo APP Benutzerhandbuch". Das '
        "Benutzerhandbuch kann von der offiziellen Website heruntergeladen oder durch Scannen "
        "des untenstehenden QR-Codes erhalten werden.",
        "source_picture": "",
        "reviewed_reset": {
            "id": "5876178f27d0-p76-36f1d94d",
            "heading": "7 System Inbetriebnahme",
            "section": "7.1 Einstellen der Geräteparameter über die SolarGo APP",
            "text_sha256": "71d994a2a9048da00bf18c5b11b5615371ed6cc7a69d6e722957b2dc830f8f70",
            "reason": "The variant-specific cable setup is section 5.5; chapter 7 "
            "describes SolarGo functions.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "ESA-Serie 125kW/261kW",
                        "source_chunk_id": "5876178f27d0-p1-a883e609",
                        "heading_path": [],
                    },
                    "source_text_sha256": "c2f0cd31256884b4b677ad2f50a31c186c420b20ca468cfa17123c6ee15c7cea",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "Parallelschaltung über SEC3000C ■",
                        "source_chunk_id": "5876178f27d0-p53-9586161d",
                        "heading_path": [],
                    },
                    "source_text_sha256": "5a24f91c02e1332acfdcd7b9cd97bbada42d1c840b771941e6ec845589764b58",
                },
                {
                    "boundary": {
                        "kind": "declaration",
                        "quote": "Nur der GW125/261-ESA-LCN-G10 erfordert "
                        "den Aufbau des MSD-Schalters. ·\n"
                        "Nur der GW125/261-ESA-LCN-G11 erfordert "
                        "den Aufbau des BatterieLeistungskabels. ·",
                        "source_chunk_id": "5876178f27d0-p72-434b1702",
                        "heading_path": [],
                    },
                    "source_text_sha256": "e79bac0ad66fe27c597fe9a9222f55aa4945a5015995a73183e4e822ffae855b",
                },
            ],
        },
    },
    {
        "sha256": "0adfb3d5e6df42e6dd465c0f6170a7c21fd82452acd64e00956fbd9aba099e43",
        "kind": "models",
        "series": [],
        "anchor_id": "0adfb3d5e6df-p3-e085d8df",
        "anchor_sha256": "d8c81730afeacf8a9e0847a9c9a5faf992430d7e3dc56d93f339ff187a97b7ba",
        "anchor_quote": "| GW125/261-ESA- LCN-G10 | 125kW | 400/380V, 3L/N/PE | 261.25kWh |",
        "source_id": "0adfb3d5e6df-p72-1057df47",
        "source_sha256": "96ada525a7beb34256e7bdf974446ad8f0b7894a3a05a30fb958765c70949162",
        "source_page": 72,
        "source_section": "6.2 Device Power On",
        "excerpt": "Step 1: Close QF2 (DC circuit breaker).\n"
        "Step 2: Close QF1 (AC molded case circuit breaker).\n"
        "Step 3: Close Q2 (DC auxiliary switch).\n"
        "Step 4: Close Q1 (AC auxiliary switch).\n"
        "Step 5: Close the front door. After the RUN indicator changes from white to green, "
        "the system completes grid connection.",
        "source_picture": "",
        "reviewed_reset": {
            "id": "0adfb3d5e6df-p72-1057df47",
            "heading": "6 System Commissioning",
            "section": "6.2 Device Power On",
            "text_sha256": "96ada525a7beb34256e7bdf974446ad8f0b7894a3a05a30fb958765c70949162",
            "reason": "The variant-specific MSD and battery-power-cable setup is section "
            "5.5; chapter 6 gives system power-on.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "ESA Series 125kW/261kWh",
                        "source_chunk_id": "0adfb3d5e6df-p1-8fbc39ae",
                        "heading_path": [],
                    },
                    "source_text_sha256": "cec4ec059ea6a1ca7e67030c6e7f417b25a02585cb70419a77df3bbedacca176",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "· GW125/261-ESA-LCN-G10 · GW125/261-ESA-LCN-G11",
                        "source_chunk_id": "0adfb3d5e6df-p1-8fbc39ae",
                        "heading_path": [],
                    },
                    "source_text_sha256": "cec4ec059ea6a1ca7e67030c6e7f417b25a02585cb70419a77df3bbedacca176",
                },
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "Parallel Connection via SEC3000C ■",
                        "source_chunk_id": "0adfb3d5e6df-p49-1123e857",
                        "heading_path": [],
                    },
                    "source_text_sha256": "0ac888d6d8fc27ddf3514d4dd8f57010a1eeaa2fa7322b518b0c179244e8a937",
                },
                {
                    "boundary": {
                        "kind": "declaration",
                        "quote": "Only the GW125/261-ESA-LCN-G10 requires "
                        "installation of the MSD switch. ·\n"
                        "Only the GW125/261-ESA-LCN-G11 requires "
                        "installation of the battery power cable. "
                        "·",
                        "source_chunk_id": "0adfb3d5e6df-p69-56e3bc9e",
                        "heading_path": [],
                    },
                    "source_text_sha256": "95605d9ab156d5060a80f1eef4a27a2a13917d606b646c2aa7ca1ca7b7ba3474",
                },
            ],
        },
    },
    {
        "sha256": "4b1a5d6dc379032ebc3ca739b933998b895d758df200e74359aadb0d4253fdb2",
        "kind": "models",
        "series": [],
        "anchor_id": "4b1a5d6dc379-p1-4dd5fb0d",
        "anchor_sha256": "8993584fd1b4faf6fc1854917da1913396da6d3bb3c15fd46b4b583a7dfd95d6",
        "anchor_quote": "(GW125/261-ESA-LCN-G10 | GW125/261-ESA-LCN-G11)",
        "source_id": "4b1a5d6dc379-p1-f7dfee4d",
        "source_sha256": "48a647023297682374dff7492ae701e392a3b6edbf97e8a5134109a91a37ad9a",
        "source_page": 1,
        "source_section": "Procedure",
        "excerpt": "*1. When a forklift is transporting the energy storage system or batteries,\n"
        "the reserved space should be ≥ 2500 mm",
        "source_picture": "#/pictures/4",
    },
    {
        "sha256": "0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615",
        "kind": "models",
        "series": [],
        "anchor_id": "0ef4b1ccdcc4-p3-3121863f",
        "anchor_sha256": "93f249ea225196bc535d6ef67269f0b066f9d4f4a8c86daa206361d2c0271d83",
        "anchor_quote": "| Inverter | GW75K-ET-G10 | Hybrid solar-storage inverter. Rated output power: "
        "3kW-10kW |",
        "source_id": "0ef4b1ccdcc4-p27-3fb7ff83",
        "source_sha256": "419227ce6cff92479f0d53767f59e06cb890d9dd4a377b40028787c7cf851bc1",
        "source_page": 27,
        "source_section": "2.1.1 Grid-Tied Scenario",
        "excerpt": "The system remains connected to the grid and operates synchronously, following the "
        'principle of "self-consumption, surplus power to the grid". Photovoltaic power is '
        "prioritized for local loads. The energy storage system charges and discharges "
        "according to electricity price periods or operating modes to achieve economic "
        "functions such as peak-valley arbitrage and demand management.",
        "source_picture": "",
    },
    {
        "sha256": "0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615",
        "kind": "models",
        "series": [],
        "anchor_id": "0ef4b1ccdcc4-p3-3121863f",
        "anchor_sha256": "93f249ea225196bc535d6ef67269f0b066f9d4f4a8c86daa206361d2c0271d83",
        "anchor_quote": "| Inverter | GW75K-ET-G10 | Hybrid solar-storage inverter. Rated output power: "
        "3kW-10kW |",
        "source_id": "0ef4b1ccdcc4-p27-7f139604",
        "source_sha256": "b817c6ae85b0683b7d782869856798ecd6b9dc8fbcdc0a3d9febba18df2bb5a7",
        "source_page": 27,
        "source_section": "Features",
        "excerpt": "The system relies on grid operation. ·\n"
        "When the grid is disconnected, the inverter must stop output immediately and cannot "
        "supply power to loads. ·",
        "source_picture": "",
    },
    {
        "sha256": "363be3f64d741a02f435aeba2ba680b98e3edc73c3a92d61b6b4637def38326b",
        "kind": "models",
        "series": [],
        "anchor_id": "363be3f64d74-p7-b35ed0d1",
        "anchor_sha256": "5f712f1b28c06d67ac0a3b7d997e40b250e8792616b5da0d7164723e1bac9e6a",
        "anchor_quote": "GW50K-ETR-L-G10 • GW75K-ETR-L-G10 • GW75K-ETR-G10 • GW80K-ETR-G10 • "
        "GW99.99K-ETR-G10 • GW100K-ETR-G10 • GW110K-ETR-G10 • GW124.99K-ETR-G10 • "
        "GW125K-ETR-G10 •",
        "source_id": "363be3f64d74-p77-a19e9ac1",
        "source_sha256": "7245bb9b2b350c37c9c3a14c8b028dc4b9bf83a720b6c64245d74bcc686cee65",
        "source_page": 77,
        "source_section": "8.3.1 LCD-Einführung",
        "excerpt": "Über das LCD-Display können Benutzer folgende Aktionen durchführen:\n"
        "Betriebsdaten, Softwareversion, Fehlermeldungen des Geräts usw. anzeigen. ·\n"
        "Parameter, Sicherheitsregion, Rückleistungsschutz usw. einstellen. ·",
        "source_picture": "",
    },
    {
        "sha256": "363be3f64d741a02f435aeba2ba680b98e3edc73c3a92d61b6b4637def38326b",
        "kind": "models",
        "series": [],
        "anchor_id": "363be3f64d74-p7-b35ed0d1",
        "anchor_sha256": "5f712f1b28c06d67ac0a3b7d997e40b250e8792616b5da0d7164723e1bac9e6a",
        "anchor_quote": "GW50K-ETR-L-G10 • GW75K-ETR-L-G10 • GW75K-ETR-G10 • GW80K-ETR-G10 • "
        "GW99.99K-ETR-G10 • GW100K-ETR-G10 • GW110K-ETR-G10 • GW124.99K-ETR-G10 • "
        "GW125K-ETR-G10 •",
        "source_id": "363be3f64d74-p74-82a89f05",
        "source_sha256": "ad5cac4ce95fe49a2a9a19f078426371b1c2f309c7a4f40d259b6189f55aa0f1",
        "source_page": 74,
        "source_section": "7.2 Einschalten des Geräts",
        "excerpt": "(Optional) Schließen Sie den DC-Leistungsschalter zwischen Wechselrichter und "
        "Batteriesystem. 1.\n"
        "Schalten Sie das Batteriesystem ein. 2.\n"
        'Drehen Sie den DC-Schalter am Wechselrichter in die Position "EIN". 3.\n'
        "(Optional) Schließen Sie den DC-Leistungsschalter zwischen Wechselrichter und PV. "
        "4.\n"
        "Schließen Sie den AC-Leistungsschalter, der mit dem Netz verbunden ist. 5.\n"
        "Schließen Sie den AC-Leistungsschalter, der mit der Last verbunden ist. 6.\n"
        "Schließen Sie den AC-Leistungsschalter, der mit dem Dieselgenerator verbunden ist. "
        "7.",
        "source_picture": "",
    },
    {
        "sha256": "5cd104b9e006bd3b8265d0518dabdaaec01058f44ac065544da1d00d8cb4b619",
        "kind": "models",
        "series": [],
        "anchor_id": "5cd104b9e006-p3-865379a5",
        "anchor_sha256": "6da59f3da2fe90ad0ee09470d435669ea9c9f29e443faa7c2c565cb76ee48dc1",
        "anchor_quote": "| inverter | GW3K-EHA-G20 GW3.6K-EHA-G20 GW5K-EHA-G20 GW6K-EHA-G20 GW8K-EHA-G20 "
        "GW9.999K-EHA-G20 GW10K-EHA-G20 GW3K-BHA-G20 GW3.6K-BHA-G20 GW5K-BHA-G20 "
        "GW6K-BHA-G20 GW8K-BHA-G20 GW9.999K-BHA-G20 GW10K-BHA-G20 | Rated output power: "
        "3kW-10kW |",
        "source_id": "5cd104b9e006-p57-c749de81",
        "source_sha256": "13c4ede2142923dd2bc38d0ea155baa28c1830bc9f2069d8a8db330c91ae7a4c",
        "source_page": 57,
        "source_section": "Self-consumption",
        "excerpt": "Basic mode of system operation. ·\n"
        "PV power generation supplies loads first, the n excess power charges the battery, "
        "and any remaining power is sold to the grid. When PV generation cannot meet the load "
        "demand, the battery supplies power to the loads; if the battery power is also "
        "insufficient, the grid supplies power to the loads. ·",
        "source_picture": "",
        "reviewed_reset": {
            "id": "5cd104b9e006-p57-3a05a42c",
            "heading": "2.4 system mode",
            "section": "Note",
            "text_sha256": "e79b863ce8e5a4976414a2b0a7d3a536b3400cf9125147dcb69b469b333a9174",
            "reason": "The earlier copyright heading is not a product limitation; section "
            "2.4 describes system modes.",
            "cleared": [
                {
                    "boundary": {
                        "kind": "heading",
                        "quote": "All rights reserved©GoodWe Technologies "
                        "Co., Ltd. 2026All rights reserved.",
                        "source_chunk_id": "5cd104b9e006-p2-e2f748ca",
                        "heading_path": [],
                    },
                    "source_text_sha256": "ec6cd276bfaf34dd11737c0bc024aca7761bb77bc3fee8167178cda117bd4fc9",
                }
            ],
        },
    },
]

# Headings omitted from emitted body chunks remain in cached source_headings.
RECORDS.extend(
    [
        {
            "sha256": "af395be79aee46f30b2beb9938f9b454c5080bd179fcb9f8404cf75a345ce038",
            "kind": "models",
            "series": [],
            "anchor_id": "af395be79aee-p1-06343fbb",
            "anchor_field": "headings",
            "anchor_sha256": "19997ae79578b7f6a732ed0d0273f9ec2b9a3ee8da7a3a761f71af3b11fce2db",
            "anchor_quote": "Quick Installation Guide of eSolar AIO3 Module",
            "source_id": "af395be79aee-p1-39ae8a5a",
            "source_sha256": "5887d0ba53237104783c2f74fe0731ae6ab9e40aa6c516711e8126641abeedcf",
            "source_page": 1,
            "source_section": "2. Installation & Connection",
            "excerpt": "Step 1. Turn the module hexagon nut position to a horizontal position.",
            "source_picture": "",
        },
        {
            "sha256": "af395be79aee46f30b2beb9938f9b454c5080bd179fcb9f8404cf75a345ce038",
            "kind": "models",
            "series": [],
            "anchor_id": "af395be79aee-p1-06343fbb",
            "anchor_field": "headings",
            "anchor_sha256": "19997ae79578b7f6a732ed0d0273f9ec2b9a3ee8da7a3a761f71af3b11fce2db",
            "anchor_quote": "Quick Installation Guide of eSolar AIO3 Module",
            "source_id": "af395be79aee-p1-e90e863f",
            "source_sha256": "74222baed7dfb02dc188c551b095b939b3275538a0d70e70eaf391faeab70fcf",
            "source_page": 1,
            "source_section": "2. Installation & Connection",
            "excerpt": "Step 2. Insert the module into the inverter USB interface and fasten the hexagon nut "
            "in clockwise direction. Step 3. Connect RJ45 connector to router.",
            "source_picture": "",
        },
        {
            "sha256": "af395be79aee46f30b2beb9938f9b454c5080bd179fcb9f8404cf75a345ce038",
            "kind": "models",
            "series": [],
            "anchor_id": "af395be79aee-p1-06343fbb",
            "anchor_field": "headings",
            "anchor_sha256": "19997ae79578b7f6a732ed0d0273f9ec2b9a3ee8da7a3a761f71af3b11fce2db",
            "anchor_quote": "Quick Installation Guide of eSolar AIO3 Module",
            "source_id": "af395be79aee-p1-91cad11c",
            "source_sha256": "9f23979b2050fb567a051565977ece6151a4b8068346689f99c3c034d4ddca47",
            "source_page": 1,
            "source_section": "OLED Operation",
            "excerpt": "Screen will return to home interface if no further operation for 40 seconds. OLED "
            "monitor will turn off if no further operation for 50 seconds.",
            "source_picture": "",
        },
        {
            "sha256": "f4d53810d74c55c8acd508f8afe6529f54ce0269b47ad64944ae4af4b5125d17",
            "kind": "models",
            "series": [],
            "anchor_id": "f4d53810d74c-p2-c0136c0d",
            "anchor_field": "headings",
            "anchor_sha256": "8b4f0424657f21736507d15a4daa5a7db80cec2855ba2f77b922a309ee254ef9",
            "anchor_quote": "GW125/261-ESA-LCN-G10 GW125/261-ESA-LCN-G11",
            "source_id": "f4d53810d74c-p16-a3417a6e",
            "source_sha256": "a2b1c6cd04a2771fccd466963a5bd4fe058fb0c35115f3ef63bea2f722b6f153",
            "source_page": 16,
            "source_section": "2.5 Fault Localization Method",
            "excerpt": "Step 1：Log in to the Solargo or SEMS+ / WE 3.0 platform to view alarm information.\n"
            "Step 2：Locate the fault position based on the alarm information.\n"
            "Step 3：Perform troubleshooting with reference to the corresponding fault handling "
            "suggestions in the alarm list.",
            "source_picture": "",
            "reviewed_reset": {
                "id": "f4d53810d74c-p16-a3417a6e",
                "heading": "2.5 Fault Localization Method",
                "section": "2.5 Fault Localization Method",
                "text_sha256": "a2b1c6cd04a2771fccd466963a5bd4fe058fb0c35115f3ef63bea2f722b6f153",
                "reason": "The generic manufacturer cover names the equipment family; the "
                "next cover line explicitly declares the applicable G10 and G11 "
                "models. Section 2.5 gives the fault-location procedure.",
                "cleared": [
                    {
                        "boundary": {
                            "kind": "heading",
                            "quote": "ESA Series 125kW/261kWh C&I Energy "
                            "Storage System",
                            "source_chunk_id": "f4d53810d74c-p2-c0136c0d",
                            "heading_path": [],
                        },
                        "source_text_sha256": "d92c0a3955bbbd5a8824bf7e94a44f40f46ced403a6fd46505a418bb98a06464",
                    }
                ],
            },
        },
    ]
)
