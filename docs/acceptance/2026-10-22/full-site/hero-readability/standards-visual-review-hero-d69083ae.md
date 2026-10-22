# Hero backdrop local visual comparison — d69083ae

Verdict: **bounded local visual PASS for the twelve supplied after views, each actually compared with its matching before view.** The targeted EPC, Residential and Application white-text/photo weaknesses visibly improve, while useful equipment/scene detail and original block geometry are retained. No new backdrop-induced occlusion, clipping or German overflow was identified. This verdict covers the photographic backdrop and visible text/control separation only; it is not a whole-hero interaction, all-text accessibility or production acceptance.

## Fixed version and actual method

The reviewed after captures are bound to three-source aggregate:
`d69083aefc946cc4884e17d2774d9b503661f5e39cb151388649423791748661`.

The new hero source SHA is `034942b7178f8bc986b90441baa61cc738cb6bd1a80646b0f01510f47d312654`; the two d1 stylesheets remain the previously reviewed bytes. The independent source Standards report is `standards-review-hero-d69083ae.md`.

Before reviewing I copied all twelve before and twelve after JPEG/JSON pairs into a fixed private directory:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/hero-d690-standards-visual-20261022T080942248428Z/`.

I then opened **all 24 original JPEGs individually**, in before/after pairs through `view_image`, and compared titles, eyebrows, small explanations, photograph detail, image framing, visible CTAs/composer, spacing, German wrapping and occlusion. I independently checked all paired JSON and exact JPEG/JSON hashes. I did not control a browser, alter the instance, compile, deploy or test a live click.

The viewports match within every pair: EPC desktop 1440×844; Residential/Application desktop 1440×1000; all phones 390×844. The EPC desktop images must not be compared geometrically to the earlier 1440×1000 header audit frames.

All twelve after records declare d690 and load `tailwind.css?ver=1792655451`; they report fonts loaded, zero overflow, and complete nonzero-width hero images. Root reports the compiled cache is 709681 bytes with SHA256 `3bc1c482a26fd4a39ab6573d1a9bd312f6f18e2173b66e723882326355cdaafd`. My independent read-only evidence here is the saved CSS URI, actual pictures and winning computed pseudo-element gradient, not a new response-body fetch.

The working tree subsequently received a separate marketing CTA transition-property delta. These after images predate it and remain d690 evidence. I used the fixed d690 sources/private picture copy, not the later mutable stylesheet or its new aggregate. The new CTA transition work and its diagnostic/after states are outside this verdict.

## Independent DOM/readback comparison

For every before/after pair, I compared the complete values of `url`, `viewport`, `scrollY`, `bodyClasses`, `heading` (including text/color/font size/line height/rect), `actions` (including text/font size/href/rect), `fontStatus`, and `overflow`. All were **exactly unchanged**, as were cover class and cover rect. This supports the observed unchanged wrapping, native destinations and composition; it is not a click test or a whole-page pixel comparison.

Actual after backgrounds agree with the new file in all twelve records:

- EPC/Application: `linear-gradient(rgba(7,29,52,.64), rgba(7,29,52,.64) 62%, rgba(3,19,34,.82))`;
- Residential: `linear-gradient(rgba(13,29,25,.64), rgba(13,29,25,.64) 60%, rgba(13,29,25,.72))`.

The saved selected text records show opaque white headings/descriptions; EPC's small eyebrow is `rgb(238,248,255)` / opacity 1. Residential's badge/subtitle are white / opacity 1, and its footnote remains white / opacity .9. Application's selected records include the white heading and description; its eyebrow color was checked in the frozen native source, not invented as a captured after field. These observations agree with the conditional envelope in the source review. They do not certify every descendant, alpha/blend state or antialiased photo/text pixel.

The white Residential composer is visibly still white, the photo is darker underneath, and its icons/placeholder are not faded along with the photograph. EPC's white main CTA and Application's white main CTA remain separate foreground elements. Image subjects remain recognizable in each after photograph, rather than disappearing behind an opaque dark block.

## Per-pair actual observations

### Epc

- **`before-epc-en-1440.jpg` → `after-epc-en-1440.jpg`** — The formerly bright sky/cabinet behind both title lines is now consistently tinted. The eyebrow and title separate clearly from the sky; the lower description remains readable. Crane, suspended cabinet, other equipment and panel rows remain identifiable. White CTA and the next white section are unchanged and distinct.

- **`before-epc-en-390.jpg` → `after-epc-en-390.jpg`** — The four-line title, especially storage systems. over the cabinet, no longer blends into the equipment. Small eyebrow is clearer against the darkened sky. Title and lower explanation/white CTA stay separated; the scene remains recognizable and no new clipping is visible.

- **`before-epc-de-1440.jpg` → `after-epc-de-1440.jpg`** — The long two-line German title stays in the same position and now has stable backing over sky and lifted equipment. Eyebrow/description remain separated from the photo. No change in line breaks, CTA placement or visible section boundary; equipment details remain visible.

- **`before-epc-de-390.jpg` → `after-epc-de-390.jpg`** — Three-line German heading remains complete at the same width; white letters have a stronger, uniform backing across sky/equipment. The longer explanation and main CTA retain their spacing. No text/control overlap or right-edge cut.

### Residential

- **`before-residential-en-1440.jpg` → `after-residential-en-1440.jpg`** — The small HOME STORAGE badge and explanation are clearer on the central gray cabinet; the two-line main heading is stronger. Cabinet, wood siding, plants and lit window remain visible. White composer and attachment/mic/send icons remain bright and unoccluded; suggestion positions do not move.

- **`before-residential-en-390.jpg` → `after-residential-en-390.jpg`** — The formerly light central cabinet behind the small explanation is uniformly darker. White text is clearer while cabinet outline and photographed ring/logo remain visible. White composer is not faded by parent opacity; icons and three suggestions stay distinct. Existing small target sizes are not fixed.

- **`before-residential-de-1440.jpg` → `after-residential-de-1440.jpg`** — HEIMSPEICHER eyebrow and small German explanation gain dark backing while the two-line title stays unchanged. No new wrap, composer tint or CTA/pill occlusion. The scene is darker but still conveys the home installation and equipment.

- **`before-residential-de-390.jpg` → `after-residential-de-390.jpg`** — The three-line title and smaller explanation remain inside the same phone width, now on a stable darkened cabinet. Placeholder, icons, the two-line final suggestion and .9-opacity footnote remain separate and complete. No new collision or horizontal clipping; chips still have their existing target-size issue.

### Application

- **`before-application-en-1440.jpg` → `after-application-en-1440.jpg`** — The title over field/panels and small lower explanation over gray containers now have a darker continuous backdrop. Crane, panels, field and container row remain recognizable. Solid-white primary CTA and separate secondary link keep their original spacing and geometry.

- **`before-application-en-390.jpg` → `after-application-en-390.jpg`** — The two-line heading and three-line lower explanation are clearly separated from the field/containers after tinting. The crane and container scene remain visible, and the intended image gap between heading and actions remains. Primary and secondary actions stay on separate rows. Secondary link target remains only the existing 28 px.

- **`before-application-de-1440.jpg` → `after-application-de-1440.jpg`** — Long German two-line headline and three-line explanation retain their wraps and positions. Previously bright container surfaces no longer compete as strongly with the small white explanation. Photo framing and both CTA rows are preserved; no new occlusion.

- **`before-application-de-390.jpg` → `after-application-de-390.jpg`** — Four-line heading and four-line explanation keep the same widths/spacing. Light container patches under the explanation are now dark enough by eye for a clear improvement; full strings remain visible. Main button and secondary link are unoccluded; no new truncation or overflow.

## Remaining scope under the same full-site goal

The observed backdrop repair can pass as a bounded batch while interaction target work remains open. Root measured Application's secondary link at 28 px high / 12 px text (primary 45.5 px) and Residential prompt chips at approximately 35.59 px / 11 px. The saved action records retain those same sizes before/after. Readable small labels do not make these controls accepted for the broader target-size requirement. The new background changes neither their dimensions nor native event handling.

No native CTA destination was followed by this reviewer. Keyboard focus, pointer behavior, composer submission/attachments/voice, hover transitions, full-page parity and production readback were not tested here. The source-level layer review reduces the risk of new event obstruction but does not replace root's interaction acceptance. Other photo families and their controls likewise do not inherit an untested all-hero PASS.

The before weaknesses are retained as before evidence. This report does not overwrite the d1 header/history reports or turn the original Utility diagnostic frames into successes. All conclusions are tied to these exact d690 after bytes and matching viewport pairs.

## Exact individually inspected image and JSON hashes

Private review manifest SHA256: `c66f92cc5e80e74d943d0db63de4219a9112a81cf736907a183f212a92e6eaf6`.

Private independent DOM comparison SHA256: `532f9b4c80d4a04c287f5810edda2bb5d7003b3482a1c40d94deece1f8c46779`.

| Image | Viewport | JPEG SHA256 | Paired JSON SHA256 |
| --- | --- | --- | --- |
| `before-epc-en-1440.jpg` | `[1440, 844]` | `61523c44d6d194323ec35ae04a95e2f472912bd06ef908685691d0379d2d4004` | `1dcd9c8e958bac354dd617e1909a6b8bbef647fb6e4709fd1708d543b9acfa2b` |
| `after-epc-en-1440.jpg` | `[1440, 844]` | `350f188c038c8a4a5cf7e670563dc2ad7599b2ed086968e052380f05487b0849` | `a129c96fab566120e09db486cf871afd82692448cddb685d254889f618bbd67e` |
| `before-epc-en-390.jpg` | `[390, 844]` | `e3b17602eba9b77ad1a40507df504d7846caf492a9957c7ea0f95353295cb52a` | `3f48578626d86483b9d08532bb019388674dd78eba5fedff28c5eb54e9439d88` |
| `after-epc-en-390.jpg` | `[390, 844]` | `a2ec7a567fb761356a4c080ba4bc9abb908600063d423334e1bdb0a85e066803` | `7e05aebd42096086e8d32fb779ae8d353fe42cd519ec0ba12162ac8227488b6c` |
| `before-epc-de-1440.jpg` | `[1440, 844]` | `e541c0944c92c6a3fb886f6bc1ae7199e7f3c3e2ba64c3c6e158553a0150bea2` | `295afff26ba683ce1bc2f66e46a8d7104d3e095657cc5fe425a7eec5c510c7a6` |
| `after-epc-de-1440.jpg` | `[1440, 844]` | `825843eb62bba2d40e03dfff01aff0bcfa2ed9036590508cbd0c786885dfadf0` | `b6b3a391f60ca98942120129329c85d63bc45394dde0cbe52dcc3f66c5d4388e` |
| `before-epc-de-390.jpg` | `[390, 844]` | `d78fb683b2f60e37d70446d22d8d5bf92708cb3399c6247d64cc36e11b8bcfb5` | `8bc9d4b1906ea32176117d42ea1ae01d28d9139fb596f62e48f7f8b6e5607ac3` |
| `after-epc-de-390.jpg` | `[390, 844]` | `b0ccb4f458343671bae253242299024e4454f3d1738dbfd16922aef6a3fb5676` | `1552cac19cb74fc6b441368c91e01aacdacfa5e241d07bb6c108811a74433623` |
| `before-residential-en-1440.jpg` | `[1440, 1000]` | `d7888962661bd8f75a5ab8081b9fa21e7025118c303dec65b94ee51f76010331` | `bb7b86734567cc59e76946f317836440337783737d6215b2aa1e9379702f6829` |
| `after-residential-en-1440.jpg` | `[1440, 1000]` | `0057e48fc221ac3685ba383595fb9c4f1af240768285687cf556eaf7c6e081d8` | `2b57ad8c80b3e5a8b745f3ee63793ad07bb609921d4bb79dc510bb0b201137bb` |
| `before-residential-en-390.jpg` | `[390, 844]` | `b286390c8ffa8568c4cce1189edcf29edd98f9763c1ce61b9d8b99957aad528e` | `45801298740d4c1a6a48bfbd3948d9bfacd8da39821550c41920515b3082afd3` |
| `after-residential-en-390.jpg` | `[390, 844]` | `6afc42bbeee16a1405d89e02fde47f7f2ad7d8638ffafc0266bbbe3ab6c97312` | `690443f9260040760cbfe7a326d1c64f1ae0fdf90a740046bed0e246f915d1ec` |
| `before-residential-de-1440.jpg` | `[1440, 1000]` | `f9d34beb89cd5258ab40fd0b96f47c15ccd8813eb208f41d55b8b29148d481a0` | `c9492800c10c6ba9c3ad6d496fd8ca9bdc922fa831453477738d9a588e55ce16` |
| `after-residential-de-1440.jpg` | `[1440, 1000]` | `f0ea699a7b60c341da212ba8136d40e4516797b859251ee9250894fb5fe46acd` | `ba4de76585950e170c50a71b5017d2d5664ee94b0b32c408600bc21504e68e6a` |
| `before-residential-de-390.jpg` | `[390, 844]` | `80b3aadb049d168fd9350580f0ec65a7bede4c57efb5cb75371eacd3f132ee4b` | `26d5644af5cf27fd80ae7eea786b5ec59ff3729233670de128d37dbe45d9f561` |
| `after-residential-de-390.jpg` | `[390, 844]` | `62fcfa3c7bd139bcb74959571a08e871159299cea4f9fa267dab726c6e81040b` | `dd4b196d6d9df3d2d9fb46f347b7f3931bfa09218f00da1c2b70e1c5a9a1313d` |
| `before-application-en-1440.jpg` | `[1440, 1000]` | `ab22c7ee0583e36fbd00842a9a7e27305d335a41913822607a200a684cf003f0` | `8ae1872f796c02aff509f93266b3428752df75e6aa3692ce67a5161f2597eec7` |
| `after-application-en-1440.jpg` | `[1440, 1000]` | `881f490d77562cf1a7323a4a1b24214ee89f2a2ad1cd4fd5b3e5dfd93086d619` | `79147f51ae2017e03cc8569bca9827cbb4eb548a11edeb2f6a41f3b99bf19fab` |
| `before-application-en-390.jpg` | `[390, 844]` | `67bc93a348964740de4c75aedf6840da1ee0ce17e8bf8232553547435ff08eaf` | `7a5028cde67a1d3d46029a64040a4330b6e3e289f047b9b58836ebe8b39e7b7f` |
| `after-application-en-390.jpg` | `[390, 844]` | `3ce49ca3273b646253d950d5830a639cff328b381a07a4780d26f9d9eb0ad8b2` | `165576646529be893a75cfeb4e7c8101025ec21062d37257befe3eba9ab58327` |
| `before-application-de-1440.jpg` | `[1440, 1000]` | `791d1f7b87f23f5004a5aa6d81385b3b5a03383d0f84e42691e431ca4bc23c40` | `0de7181e6be8b359ba8fce0e2a00d1c47270a6ca31e506af8a80bee780114f04` |
| `after-application-de-1440.jpg` | `[1440, 1000]` | `57eedda5cb634c96e2ce8033c66fb84b3daa6466881198881b0df56a908ee494` | `7fb7cab235f488b6da1d28a6b9641d500c6150014ef82bd5588498c24e9ed076` |
| `before-application-de-390.jpg` | `[390, 844]` | `7a5b0a8011804938190bec868a1b28f4b4f8c9b343dcd546f009042394430621` | `fdf19775fb9dff4d92f03f2274fc5566b1788c321b775fbb6c2dc7a68aaba3e7` |
| `after-application-de-390.jpg` | `[390, 844]` | `228c939b2430e7201fcbdc3908c812ad9733f720e5115bc8dd43e64168237264` | `3b05c823bffa3cabc023af5d30822d2ee245062f415923796d7ba253ed06eaf3` |
