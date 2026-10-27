# Authoritative roof-plane layout review

2026-10-23. This supplements the existing mature-software capability map, not
another search for a product direction. Official Shapely pages were acquired
through Apify website-content-crawler run `fJIqiXQXnpwBT79d8`, dataset
`Lc1EoMvEweAVqWDrA`, SUCCEEDED, five nonempty primary pages. URLs, text hashes
and acquisition time are in PRIMARY-PROVENANCE.json. No credentials are stored.
Installed lock/runtime actually reports Shapely2.2.0 / GEOS3.14.1.

The implementation deliberately uses each roof's local orthonormal metre
plane. Shapely analyses XY and ignores Z; passing three coordinates would not
provide a solid-collision or shading calculation. Full cuboid corners are
explicitly projected into the roof basis. Concave obstacle extrusions are a
union of base, translated top and swept edges; a convex hull would falsely
fill recesses. These are our model choices, not claims of CAD qualification.
[Official manual](https://shapely.readthedocs.io/en/stable/manual.html).

`covers` includes boundary contact. Zero declared clearance therefore permits
contact with the given roof edge, while an explicit positive clearance compares
the actual distance to the whole roof boundary, including holes. No default
fire/wind setback, shape repair or tolerance expansion is inserted.
[Official covers](https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html).

STRtree supplies candidate indices from bounding boxes; it does not itself
prove overlap. We check positive intersection area and actual Euclidean
distance, with explicit candidate/diagnostic bounds. Query results are sorted
for deterministic partial diagnostics. No precision grid is introduced.
[Official STRtree](https://shapely.readthedocs.io/en/stable/strtree.html),
[official intersection](https://shapely.readthedocs.io/en/stable/reference/shapely.intersection.html).

Invalid polygons remain diagnosed original inputs rather than being silently
repaired. Source precision and missing layout rules remain explicit unknowns.
The checker version/library identities and canonical geometry hash accompany
its response. A conflict-free projection does not evaluate structural, fire,
wind, mounting, electrical or shading requirements.
[Official validity API](https://shapely.readthedocs.io/en/stable/reference/shapely.is_valid_reason.html).

Actual server/browser integration and independent acceptance are recorded in
the existing execution record and the design-geometry contract. Library/API
verification does not count as native UI or production acceptance.
