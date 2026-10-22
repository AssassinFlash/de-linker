# Origin-host read increment — independent Standards review

**PASS for this one-line source increment.** No regression or framework/gate bypass was found. This does not approve unrelated mainline Protection/Admission integration or extend earlier native/visual/deployment evidence.

- Before: 15-source `14cb7f7438fd677721106aa37d0f6ae569e60b469240ec4fb9929feff67395e6`, full31 `eec1822aebf838d41ae5a0b092597a20892a5b5e5de5e9b2d544254e6278b95b` (`source-integrated-files-eec1822a.json`).
- Current: 15-source `ad96563eab36c1f0c73bf410ce61d212eb904393c8c563f1cf04ac69b9a4823a`, full31 `79a7175f15f2c4a9b4d887ee72b2b926612af3b48c6e97562f499e1874621461`.
- Every one of the 31 current hashes matches the manifest. Exactly SelectionContext.php changes; the other 30 artifacts are byte-identical. Replacing this sole home_url() call with its previous home_url('/') spelling reproduces the exact complete earlier file SHA, so no hidden method change is inferred from a short diff.
- Manifest SHA-256: `73206ce87e0fd4d8c8fe4debb4d3db180bb2428105f273b442d6f11a3a53da17`. Independent readback: private `selection-standards-integrated/origin-host-map-readback.json`.

## Source conclusion

SelectionContext::same_origin reads home_url() through wp_parse_url and compares only scheme, hostname and port. It does not use the resulting path or emit a client URL. Removing the redundant slash path argument therefore keeps this origin comparison on the existing host-read primitive. The absolute http/https allowlist, matching scheme/host/port, forbidden userinfo, canonical source-path comparison and current public-object resolution remain byte-identical. Localized page/term destination writers remain native and unchanged.

I read the actual `tools/checks/internal-home-urls.py` contract: the gate rejects plugin path literals, including '/', and expressly permits no-argument home_url() for host reads. The production change follows that contract; it does not weaken the checker, add an ignore, invent a route or bypass native language URL APIs. No additional Standards/Fowler issue was established in this increment.

## Exact file identity and limits

| File | Before SHA-256 | After SHA-256 |
|---|---|---|
| `plugins/linker-commerce/includes/Contact/SelectionContext.php` | `1efc949c963c0fd4eaeb08ae7235020d025dcbc6fae6330aca149143bc594a5b` | `66d0897ff9a636c65956d176c5f648c09f596c9f77255855cb4869c7bb3f7a47` |

Review consisted of source/checker inspection, exact byte hashing and reversible before-file verification. No runtime PHP, tests, npm, DB/native instance, browser, build or production operation was performed. Parent-reported unit/PHPCS/PHPStan results and the pending combined full-check/native run are separate evidence; this source ruling is not their execution or visual acceptance.
