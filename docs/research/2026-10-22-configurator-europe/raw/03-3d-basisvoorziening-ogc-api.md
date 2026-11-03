Source: https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections
Retrieved through Apify run vM06HVKbFax03LMUx, 2026-10-22.

# 3D Basisvoorziening (OGC API)

## 3D Basisvoorziening - Collections

De 3D Tiles Gebouwen worden gegenereerd door met behulp van de BAG-geometrie de gebouwen te modelleren in LoD 2.2. Waar geen AHN gegevens beschikbaar zijn, worden de gebouwen weergegeven in LoD 1.3. De hoogte van deze LoD 1.3 gebouwen is gebaseerd op puntenwolken gegenereerd uit luchtfotobeelden. De 3D Tiles Gebouwen zijn beschikbaar in het (OGC) 3D Tiles formaat ten behoeve van visualisatie doeleinden. Deze wordt alleen aangeboden in de meest recent beschikbare jaargang, zie tabel 1 in de…

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/gebouwen?f=json)

- **Keywords**: glTF, glb, cesium, 3D, basisvoorziening, gebouwen (bagpandid), panden, bag, 3Dtiles
- **Last updated**: 2026-07-01
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590

![gebouwen Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_gebouwen.png)

De 3D Tiles Terreinen (inclusief wegen en water) worden gegenereerd op basis van BGT-geometrieën op maaiveld niveau. De hoogte wordt sinds 2025 bepaald uit AHN-gegevens. Daarvoor werd dit gedaan op basis van puntenwolken gegenereerd uit luchtfotobeelden. De 3D Tiles Terreinen zijn beschikbaar in het (OGC) 3D Tiles formaat ten behoeve van visualisatie doeleinden. Deze wordt alleen aangeboden in de meest recent beschikbare jaargang, zie tabel 1 in de…

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/terreinen?f=json)

- **Keywords**: glTF, glb, cesium, 3D, basisvoorziening, gebouwen (bagpandid), terreinen (bgt\_fysiekvoorkomen, bronhouder), bgt, 3Dtiles
- **Last updated**: 2026-09-22
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590

![terreinen Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_terreinen.png)

Deze collectie bevat 3D objecten voor gebouwen in LoD 2.2. Waar geen AHN gegevens beschikbaar zijn, worden de gebouwen weergegeven in LoD 1.3. De hoogte van deze LoD 1.3 gebouwen is gebaseerd op puntenwolken gegenereerd uit luchtfotobeelden. Het geleverde formaat ([CityJSON](https://www.cityjson.org/)) is geschikt voor analyse doeleinden in GIS programmatuur. Voor BIM software is een [IFC converter](https://github.com/3DGI/cityjson2ifc) beschikbaar. Deze bestanden worden jaarlijks…

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/basisbestand_gebouwen?f=json)

- **Keywords**: Attributen gebouwen: bagpandid, bouwjaar, objectid
- **Schema**: [View schema](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/basisbestand_gebouwen/schema)
- **Last updated**: 2026-09-23
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590
- **Temporal extent** ([ISO-8601](http://www.opengis.net/def/uom/ISO-8601/0/Gregorian)): 2018-01-01 / 2025-12-31

![basisbestand\_gebouwen Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_kaartbladen_geb_voll.png)

Deze collectie bevat 3D objecten voor gebouwen (met attribuut informatie), terreinen, water en wegen. Het geleverde formaat ([CityJSON](https://www.cityjson.org/)) is geschikt voor analyse doeleinden in GIS programmatuur. Voor BIM software is een [IFC converter](https://github.com/3DGI/cityjson2ifc) beschikbaar. Deze bestanden worden jaarlijks geactualiseerd.

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/basisbestand_gebouwen_terreinen?f=json)

- **Keywords**: Attributen gebouwen: bagpandid, bouwjaar, objectid, Attributen terreinen: bgt\_fysiekvoorkomen, bronhouder, objectid
- **Schema**: [View schema](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/basisbestand_gebouwen_terreinen/schema)
- **Last updated**: 2026-09-23
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590
- **Temporal extent** ([ISO-8601](http://www.opengis.net/def/uom/ISO-8601/0/Gregorian)): 2018-01-01 / 2025-12-31

![basisbestand\_gebouwen\_terreinen Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_kaartbladen_geb_voll.png)

Deze collectie bevat 2D geometrieën van gebouwen met uitgebreide attribuut gegevens over pandhoogte in [GeoPackage](https://docs.geostandaarden.nl/3dbv/basis-al-prod-20211222/#geopackage) formaat, via bagpandid te koppelen met 3D Objecten Gebouwen. Deze bestanden worden jaarlijks geactualiseerd.

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/hoogtestatistieken_gebouwen?f=json)

- ### Downloads
  - [Full download 2018 (2.3GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2018/hoogtestatistieken/2018_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2019 (1.9GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2019/hoogtestatistieken/2019_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2020 (2.5GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2020/hoogtestatistieken/2020_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2021 (1.83GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2021/hoogtestatistieken/2021_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2022 (2.23GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2022/hoogtestatistieken/2022_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2023 (2.25GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2023/hoogtestatistieken/2023_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2024 (2.3GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2024/hoogtestatistieken/2024_3d_hoogtestatistieken_gebouwen.zip)
  - [Full download 2025 (2.3GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2025/hoogtestatistieken/2025_3d_hoogtestatistieken_gebouwen.zip)

- **Keywords**: 2D, gebouwen, geopackage, Attributen o.a: bagpandid, pandstatus, bouwjaar, lod, hoogte maaiveld, dakhoogten, daktype
- **Schema**: [View schema](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/hoogtestatistieken_gebouwen/schema)
- **Last updated**: 2026-09-23
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590
- **Temporal extent** ([ISO-8601](http://www.opengis.net/def/uom/ISO-8601/0/Gregorian)): 2018-01-01 / 2025-12-31

![hoogtestatistieken\_gebouwen Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_kaartbladen_geb_voll.png)

Het DTM wordt gegenereerd op basis van [AHN](https://www.pdok.nl/introductie/-/article/actueel-hoogtebestand-nederland-ahn). Dit is een terreinmodel van heel Nederland, waarbij de maaiveld terreinhoogte ter plaatse van gebouwen en water wordt geïnterpoleerd. Het 3D DTM is beschikbaar in het [Quantized Mesh](https://github.com/CesiumGS/quantized-mesh/) formaat voor gebruik in Cesium clients. Het bevat geen attribuut informatie. . Deze wordt alleen aangeboden in de meest recent beschikbare…

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaalterreinmodel?f=json)

- ### Downloads
  - [Full download (12.23GB)](https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/dtm/ahn6/ahn6.zip)

- **Keywords**: 3D, 3D Basisvoorziening, terreinen, DTM, quantized mesh, cesium
- **Last updated**: 2026-02-09
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590

![digitaalterreinmodel Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_dtm.png)

Het Digital Surface Model (DSM) representeert het aardoppervlak van Nederland inclusief objecten en vegetatie, gemaakt op basis van regelmatige puntenwolken aan de hand van luchtfoto’s, in [LASZip](https://laszip.org/) formaat. Dit DSM bevat een afstand tussen punten van minimaal 20 cm. Deze wordt alleen aangeboden in de meest recent beschikbare jaargang, zie tabel 1 in de [productbeschrijving](https://3d.kadaster.nl/productbeschrijving/#3d-basisvoorziening).

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_20cm?f=json)

- **Keywords**: 3D, 3D Basisvoorziening, DSM, laszip, puntenwolk
- **Schema**: [View schema](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_20cm/schema)
- **Last updated**: 2026-09-23
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590
- **Temporal extent** ([ISO-8601](http://www.opengis.net/def/uom/ISO-8601/0/Gregorian)): 2025-01-01 / 2025-12-31

![digitaaloppervlaktemodel\_20cm Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_kaartbladen_dsm.png)

Het Digital Surface Model (DSM) representeert het aardoppervlak van Nederland inclusief objecten en vegetatie, gemaakt op basis van regelmatige puntenwolken aan de hand van luchtfoto’s, in [LASZip](https://laszip.org/) formaat. Dit DSM bevat een afstand tussen punten van minimaal 8 cm. Deze wordt alleen aangeboden in de meest recent beschikbare jaargang, zie tabel 1 in de [productbeschrijving](https://3d.kadaster.nl/productbeschrijving/#3d-basisvoorziening).

View collection as [JSON](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_8cm?f=json)

- **Keywords**: 3D, 3D Basisvoorziening, DSM, laszip, puntenwolk
- **Schema**: [View schema](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_8cm/schema)
- **Last updated**: 2026-09-23
- **Geographic extent** ([CRS84](http://www.opengis.net/def/crs/OGC/1.3/CRS84)): -1.657292, 48.040502, 12.431727, 56.110590
- **Temporal extent** ([ISO-8601](http://www.opengis.net/def/uom/ISO-8601/0/Gregorian)): 2025-01-01 / 2025-12-31

![digitaaloppervlaktemodel\_8cm Thumbnail](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/resources/3d_kaartbladen_dsm.png)
