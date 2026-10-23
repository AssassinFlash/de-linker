# Standards: bc80334b

Fixedbc80334b7b29553f24e0c75de3c2e6781493066e; complete base8791c933; thin fixd7deddf7. Standards PASS: no remaining documented correctness blocker or heuristic smell finding in this first service increment. Previous FAIL reports and unchanged independent probes are retained separately.

Original derived-resolution probe now reports actual0.125m obstacle sweep spacing and1.862645149230957e-9m cuboid-corner spacing, both explicitly incomplete/numerical_limit. Original UV-extent probe remains incomplete instead of false clear. Original large ENU translation continues to detect1cm overlap. Original large angle Python/JS centre, axes and new shared footprint agree.

Independent execution:151 Python geometry/privateHTTP and11 Node geometry tests passed. Added separate checker4 reference probe:48 exact-rational rectangular interval cases across tilt,rotation,gap and excluded slots, plus16 rotated cross-array positive-overlap/separation cases, all passed. Expected same-array pairs use independent exact interval intersections, not the checker helper or its separation inequality. Ordinary zero-gap contact remains permitted; actual thickness/tilt row overlap and nonadjacent row pairs are preserved. Numeric support scanning includes full corners, shared footprints, obstacle top/sweep endpoints and clearance search extents. Candidate limits retain incomplete status.

HTTP ownership-before-work/no-save/no-blob fixtures passed. Geometry reply now includes frozen runtime hash; its source snapshot covers planning .py files and lock, with checker/Shapely/GEOS versions separately explicit. New source legacy-identifier hits0. This is not a native browser/GPU/editor or completeB acceptance. No p548,production or parent WIP interaction.

Reproduction: restore fixed source listed in archive-manifest.json, symlink installed engine.venv and appnode_modules, setPYTHONPATH to restoredengine/src, run retained probes; exact commands/results recorded inresults.json. Reconstructible snapshot is hash-verified and reclaimed at review completion; independent probes/results/manifest/report remain.
