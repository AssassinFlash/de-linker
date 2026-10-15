# #175 evidence: the four blog faces' absorption

Material behind `docs/specs/175-blog-legacy-templates.md`. The shots are the
self-check pairs; the scripts produced them and re-measure the numbers the spec
quotes. Nothing here is part of the plugin.

## What is here

| Path | What it is |
|---|---|
| `dt-574.html` … `dt-6879.html` | The six old templates' `post_content`, read off the instance with WP-CLI (`post get <id> --field=post_content`) — the old implementation as evidence, kept so the before state survives the takeover |
| `generate.py` | The extraction: dump → repository file (the four mechanical transforms of the spec's §1, the `-webkit-` pair order of §4, the instance-host normalization of §5), `--apply` copies into the plugin tree |
| `shots.mjs` | Six faces × 1440/390 full-page shots, one browser, one settle protocol (animations off, lazy images scrolled through, fonts ready, images decoded) |
| `shots-pair.mjs` | The same protocol against two bases (the live site and the instance), for the live\|local pair of the six faces |
| `pixel-diff.py` | Before/after pixel diff: differing-pixel counts, bounding boxes, a red diff bitmap |
| `why.py` | Why two shots differ: the first differing pixels with both colours, the row runs, the max/mean channel delta |
| `diff-regions.py` | Clusters the differing pixels into boxes with colour samples — what named the Compose trap in §4 |
| `style-dump.mjs` | Every element under a face's root with every computed property and its box, as JSON — the 290-element dump whose old/new comparison had **exactly one** difference (`backdrop-filter: blur(18px)` → `none`) |
| `shots-before-final2/`, `shots-after-final2/` | The committed pair of the final state: **0 differing pixels on all 12 shots**, page heights equal grid by grid |
| `pair-de/`, `pair-en/` | The live\|local pair of the same protocol (German and English faces) |

## The live|local numbers (2026-10-16)

1440: all six faces **0 differing pixels**.

390: four shots carry a small residual — `blog-de` 227 px, `blog-en` 154 px,
`search-de` 65-134 px, `search-en` 134 px, all ≤ 3/255, on thumbnail edges and
text pixels. They are **not from this change**: with the repository templates
replaced by the old ones and the faces re-shot, the same numbers come back at
the same coordinates. They are also not a local-only artefact: **the live page
does not match itself** between two runs of the same protocol (measured on
`/de/?s=wechselrichter` at 390: 69 px, ≤ 3/255, same row band) — the 390
residual is run-to-run rasterisation on text and scaled images, for the pixel
gate's mask ledger.

## Re-run

```sh
# the instance, with the old templates back in place:
for id in 574 619 607 6881 6875 6879; do
  just wp blogs post update $id .scratch/175/dt-$id.html --user=1
done
node .scratch/175/shots.mjs .scratch/175/shots-before

just present blogs && just windpress-compile blogs && just present blogs
node .scratch/175/shots.mjs .scratch/175/shots-after

uv run --with numpy --with pillow python .scratch/175/pixel-diff.py \
  .scratch/175/shots-before .scratch/175/shots-after .scratch/175/diff
```
