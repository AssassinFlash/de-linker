# Map display: primary sources and implemented boundary

2026-10-23. This extends IMPLEMENTATION.md with current first-party material,
the installed pinned dependency combination and the read-only projection seam.
It does not claim a map renderer, drawing workflow or production provider is
already accepted. Source bytes were obtained through Apify, never ordinary
search or a substitute crawler.

## Acquisition

- Run `gZvgOKAc6aed91wUd`, dataset `mCbZgPj0qf9jeH4SG`, SUCCEEDED: five of five
  requested URLs returned HTTP200. Cheerio, depth0, concurrency2, robots respected,
  Apify proxy enabled. `map-display-primary/` retains input, run, original dataset
  and SHA manifest. This includes the actual Map class documentation and the
  Terra Draw repository, not screenshots of an assumed API.
- Earlier run `YdE5Kuw8xQrO8Q36h`, dataset `Mv4Va4EWgNGR2Ptxp`, SUCCEEDED:
  OpenFreeMap home, quick start, privacy and terms. Raw records were moved from
  temporary artifacts to `provider-openfreemap/`, not duplicated.
- Actual installed versions are MapLibre GL 5.24.0 (BSD-3-Clause), Terra Draw
  1.35.0 (MIT), MapLibre adapter 1.4.1 (MIT). Adapter peers are terra-draw ^1.0.0
  and maplibre-gl >=4. The isolated app lock now pins this checked combination;
  installation alone is not runtime, GPU or newest-version acceptance.

## Engineering/display separation

The installed [MapLibre coordinate implementation](https://maplibre.org/maplibre-gl-js/docs/API/classes/MercatorCoordinate/)
defines its world-size units separately from physical metres. The new
`mapGeometry.ts` therefore reads the accepted metric document and uses the
existing complete GeographicBridge inverse. It never measures a camera pixel,
Mercator world coordinate or latitude factor. Original roof holes, opaque
object identities, included/excluded modules, actual module cuboid faces and
obstacle extrusion are preserved in a fresh display copy. No view operation can
change input history or silently quantize metric vertices.

Pinned MapLibre source `src/util/util.ts` defines its Mercator latitude limit as
85.051129°. An unsupported display latitude fails explicitly rather than being
clamped to another location. Longitude world translation is relative to the
anchor solely for contiguous display near the dateline. The map does not confer
survey accuracy, datum certainty, roof fit, fire clearance or structural release.

## Candidate public reference service

[OpenFreeMap quick start](https://openfreemap.org/quick_start/) supplies the
MapLibre style URL `https://tiles.openfreemap.org/styles/liberty`. Its software
licence, public service conditions and underlying data licence are different
contracts. The service's own attribution claim must still be checked in the
actual rendered interface, including mobile and keyboard expansion.

[OpenStreetMap copyright](https://www.openstreetmap.org/copyright) identifies
ODbL data and attribution requirements. [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
separately addresses databases, produced works and public uses of adapted data.
Displaying a reference basemap does not license Google imagery or establish a
right to relabel traced provider content as a privately owned survey. Acquisition,
derivation, retention, export and report attribution need their actual source
contract before entering the permanent project path.

[Service terms](https://openfreemap.org/tos/) are as-is, do not supply accuracy or
availability guarantees, and bound offline downloads (3000 tiles or 50 MB,
four parallel requests and an identifying User-Agent). This work performs no
offline/bulk tile download. [Privacy](https://openfreemap.org/privacy/) covers
the embedded public tile service and its delivery infrastructure. A real
integration must disclose browser requests and follow this site's consent
contract before requests occur; no provider call or consent is inferred merely
from a package install.

Google remains the separately specified renderer/Places/Solar path. No Cloud
project, billing fact, key or permission has been obtained in this increment.
Source/contract boundaries and real account evidence in IMPLEMENTATION.md still
apply. Public-map display and owned-source drawing do not replace that work.

## Actual style and local refusal investigation

The first native external load failed with AJAX status0. Actual local HTTP
headers established that the owned isolation CSP lacked the delivery origin;
this was not evidence of missing provider data. Apify acquisition was repaired
by actor selection: Cheerio Scraper requested unapproved full-account access,
which was not granted; the already usable Website Content Crawler downloaded
the official JSON using its `saveContentTypes` input. Run `NSqHjlAOTWtoGRcrB`
returned a retained HTTP200 file, 43,079 bytes, SHA
`6010998863b4876911ac9a2d62c9a28d97c8877f6d20cd158b74808572257b60`.
Its page summary counts the download as one failed page; the actual dataset
HTTP metadata, retained file and parsed version8 style are the acquisition
proof. A temporary file-download signature is removed from the stored URL.

The actual style identifies one origin for Natural Earth raster tiles,
OpenMapTiles vector TileJSON, fonts and sprites. The scoped local CSP correction
permits that origin only for images/connections. A fresh native document then
loaded the provider with no runtime failure and displayed the provider's own
OpenFreeMap, OpenMapTiles and OpenStreetMap links. Main-target network records
show HTTP200 style/TileJSON/sprite/glyph requests. Child-target attachment is
unavailable through IAB CDP; those records alone do not prove every worker
request or its absence. Native framing, final site-font readback and the full
EN/DE responsive matrix are tracked separately in the acceptance folder.
