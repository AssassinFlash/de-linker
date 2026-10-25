# CTA hover-fix actual visual review — 00ae7fc2

Verdict: **bounded local visual/runtime-record PASS for the thirty-six new `hoverfix-*` captures.** Both CTA labels remain clear in normal and selected hover+focus states; no pale text/background interpolation, clipped focus outline, button overlap or long-German label overflow was observed in these frames. The actual computed property list on all seventy-two link records excludes text/background transitions. This is not a destination-consumer, full-page, continuous-video, whole-site or production acceptance.

## Fixed provenance and inspection

Reviewed source aggregate:
`00ae7fc26d8df2d5bc63c9e4ab99e7c82da7caf8e2e4fb8d261ad3e892e742ff`.

The source delta was independently reviewed in `standards-review-hover-00ae7fc2.md`: only two scoped transition-property lines and one comment differ from d690; `chrome.css` and `hero-readability.css` are exact unchanged bytes. This visual review is assigned to the new aggregate, not to old d690 frames.

Root executed the native local capture and reports the persisted compile10 cache at mtime `1792656909.8150694`, 709779 bytes, SHA256 `7b3b0ed61f18f3f6fd5897f844532ab4c342bc6138ef34388a49ce8e98c3d1cc`; three native volume source hashes match 00ae. Root also reports the native UI completed, native logout was confirmed, and all 33 prior cookies were restored exactly after the compiler session. I did not execute those operations. No HTTP response was captured for compile10; this report does not invent an HTTP 200 from the UI or cache readback.

I copied every new JPEG and paired JSON before review into:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/hoverfix-00ae-standards-visual-20261022T082449386293Z/`.

I **actually opened all thirty-six original JPEGs individually** through `view_image`, checking each native normal/action1-hover-focus/action2-hover-focus frame at 1440×1000 or 390×844. I checked visible colors, complete labels, focus rings, target separation, phone stacking and long German text. I then independently read and validated every paired JSON and rehashed all **seventy-two files**. I did not operate the browser, instance, source, compilation, destination consumers or production.

Actual coverage is three families (Installer, Services, Application) × EN/DE × 1440/390 × three states = **36 frames**, with exactly two links in one recorded CTA group per frame. The list below records the precise viewed files and hashes.

## Independent state, property and geometry readback

All thirty-six saved records match the 00ae source tag and load:
`tailwind.css?ver=1792656909`.

All report loaded fonts, no horizontal overflow and no admin bar. Root's explicit native logout provides the guest provenance; absence of an admin bar alone would not prove a guest identity.

I independently asserted the following over all records:

| Check | Actual result |
| --- | --- |
| Normal frames | 12; both links have `hovered=false`, `focused=false`, `focusVisible=false` |
| Action 1 hover+focus frames | 12; first link has all three true and second all three false |
| Action 2 hover+focus frames | 12; second link has all three true and first all three false |
| Native transition property | All 72 links: `border-color, box-shadow` |
| Label font / target height | All 72 links: `14px` / exactly `48px` |
| CTA group gap / preceding content gap | All 36 groups: `12px` / `32` |
| Preceding recorded content font | All 36: `16px` |
| Viewport/font/overflow | Correct EN/DE × 1440/390; fonts loaded; overflow false |

Existing native transition-duration lists remain in the readback (for example Installer's three `.18s` items). Those durations do not animate text or background when the winning property list excludes them. This property readback plus the source delta addresses the actual old interpolation mechanism; the screenshots separately demonstrate the visible new state. I did not claim to watch every refresh of a continuous transition or inspect an unrecorded animation timeline.

Actual saved colors are exclusively endpoint pairs, not fractional pale intermediate RGBs:

| Foreground | Recorded button background | Link records |
| --- | --- | ---: |
| `rgb(255,255,255)` | `rgb(12,127,115)` | 24 |
| `rgb(12,127,115)` | `rgb(255,255,255)` | 16 |
| `rgb(12,127,115)` | transparent | 16 |
| `rgb(23,39,33)` | `rgb(255,255,255)` | 8 |
| `rgb(23,39,33)` | transparent | 8 |

For the transparent button backgrounds, the surrounding section is visibly white in the inspected images; the previously checked native sections also specify white. Independently modeling these transparent backgrounds over white gives a minimum solid foreground/background luminance ratio of **4.8849226068:1** across the 72 sampled records. This is a conditional calculation from the actual recorded endpoint colors, not a blanket WCAG certificate for every pixel, border, focus ring, parent opacity or site control. The private DOM review explicitly marks which rows use the white-section assumption.

## Actual visual findings by family

**Installer, 12 frames:** the normal primary is a solid teal button with readable white label; the outlined partner-account link is dark on white. Action 1 switches to teal text on white with a fully visible outline; action 2 similarly shows a complete teal focus ring without losing its label, while action 1 returns to the solid normal state. Both EN and DE labels fit at 390, with 12 px between the full-width controls. The photographed equipment and text remain separate from the buttons. No new visible fading, clipping or ring collision was found.

**Services, 12 frames:** the primary support request and secondary partner-portal link have the same clear state distinction. The previous service line-break issue is not visible as an empty third action. German `Support-Anfrage öffnen` and `Auf Partnerportal zugreifen` fit within both row and phone-column layouts. All selected rings are complete; the lower photo/collage does not occlude the controls. No pale intermediate label or background was observed.

**Application final CTA, 12 frames:** both primary configurator and secondary engineering labels remain clear. Normal primary is teal/white; the selected primary becomes white/teal with a complete rounded focus ring, and the selected secondary remains white/teal with its own ring. EN desktop uses one action row; the longer DE desktop actions wrap into separate rows with the recorded 12 px gap. This is the existing responsive flex wrapping, not overflow. Both full-width phone buttons fit with complete long labels and no ring clipping.

Several native focus actions scroll the page, leaving some preceding heading/eyebrow above the sticky header. The screenshots are used to assess the complete visible buttons and their states; these crops do not prove a whole-section heading/anchor placement PASS. No CTA is hidden behind the header, image or footer in any inspected frame.

## Historical failure and scope boundaries

The original thirty-six `release-*` d690 JPEG/JSON pairs, including root's nine diagnosed weak/intermediate frames, remain original failure/transition evidence. I neither overwrote nor reclassified them. The new `hoverfix-*` prefix and exact hash list make the distinction explicit. The new source removes text/background from interpolation; it does not obtain a pass by waiting out an unchanged failing transition.

The frozen d690 hero before/after evidence remains a separate backdrop review. These final CTA groups are not Application's photo-hero secondary link or Residential's prompt chips. Their previously measured small target/font issues stay open under the same full-site task and are not accepted by the 48 px measurements here.

No button was clicked or followed by this reviewer, and href strings in JSON do not prove their destination consumer. No form, account flow, target route, continuous key traversal, full-page pixel parity, deployed file/readback or whole-site acceptance was tested. This is the requested bounded CTA visual/state closure only.

## Exact files individually inspected

Private review manifest SHA256: `b19bd0e6ff67bbdc4174af798def563feb426c78c329d506919109272c7e6815`.

Private independent DOM/color review SHA256: `c340e7f16c3ea0a66d0b8cbad6efe6985c42dd8aa571def4d5a68d03bab21fa8`.

| JPEG file | JPEG SHA256 | Paired JSON SHA256 |
| --- | --- | --- |
| `hoverfix-application-de-1440-action1-hover-focus.jpg` | `2036ae62b0de4e52081cc73f68c19e72480902800d87fdcdf688bb958873510b` | `55edceab5d25f3a7269bb9e29bdaef66efa8444bc7b08e5ed0c605563e42e3b2` |
| `hoverfix-application-de-1440-action2-hover-focus.jpg` | `072d637a8ca7c7013a24e2db4386dc53d88b014da62f5477eff7d67b796f2727` | `56215b0b2ce806a1ac6a3e42e407c7f10ed4dbd75a85c546f35673960f66242a` |
| `hoverfix-application-de-1440-normal.jpg` | `c322418a25cfb064635b3aa33bb2879279ab7cb8e7a8b0424321aea2866d6347` | `3a29a5bb1d590ae4acbc3bb670dc8f3d7d12f500def995d061a8f0eb0edf5c4d` |
| `hoverfix-application-de-390-action1-hover-focus.jpg` | `750382f548b79193ac19d491f4b076576dc6bd6fc5c9a0475b6bdd07bd69842a` | `b321db2145654890aa7ff177c5af6c581ad148317dd24192d8bd511bd960c50f` |
| `hoverfix-application-de-390-action2-hover-focus.jpg` | `e14e440c88030858317301a29071e20f76f3d8383b50f581e6eed48482d0fe15` | `9eee3676beb58e443c767bf94b042b142f9d907d2915b6646917575c6ac162c2` |
| `hoverfix-application-de-390-normal.jpg` | `064dd218ba09450dbec58c0145f4fe97ed8e3886f0b3940ac4ef41f19dc52195` | `f35725ae195060edf186dd97ea5262bbc40e94e72d1e82756cfbc124d196dff6` |
| `hoverfix-application-en-1440-action1-hover-focus.jpg` | `974a3a8cdb80ea74d4d34aa108462d7b4c3a85fca01a01ae46695f1e4ba350dd` | `eb795b109618edc6db2e1a724013da7b0003f80c69dcfbcf9658cd64047f184b` |
| `hoverfix-application-en-1440-action2-hover-focus.jpg` | `778ea20169c5f04b437dfe6028768a4446703033b8b065890fe18fe21569ff35` | `153395ba1ac569ff0e2fb6f61e95df654d0d0b56892e3d17257c68efddfb4fba` |
| `hoverfix-application-en-1440-normal.jpg` | `4940164ce9e67b0123413fffc96931716cf74de368621bca0e8740b8ceecd3b6` | `194e555efd1bb7fd35349550582ea9bb0ed3dbe176c9646a835d6c4e5c5becdb` |
| `hoverfix-application-en-390-action1-hover-focus.jpg` | `78f9d4c4fdfabae3e27af9544c70fa757302914112951f4bc922c535b7137a6f` | `70941ff9b7ed4550790f797df11ae73e2f97440c149c7d2e32e79a35796a129d` |
| `hoverfix-application-en-390-action2-hover-focus.jpg` | `4976cba00f5a043fc0118853f77fa88a0ce0b59e5c87965cf538b1f95ee6069c` | `3c865150f077995b40f20f1a47d87e38d43f1892aaa6902dfa270a0fe4bd6d23` |
| `hoverfix-application-en-390-normal.jpg` | `35b1a31ecc37397f427681d840ef801a515623ebecb716965ffa18c1d64ff553` | `840d9143ab85c8ca8d42c11ab1fbdc08ade6deb49411d0b0d36ec49ae72a45a2` |
| `hoverfix-installer-de-1440-action1-hover-focus.jpg` | `6a6920eae24713f7a4e2b3b98967c61ab8baf2a58295042951c679b2ffb3a21c` | `758a3b531c799a18495dbe0fe03cd93b2e529a1d87e9b394ca0fdf211a835dc0` |
| `hoverfix-installer-de-1440-action2-hover-focus.jpg` | `fb5b86590ffde5bb78c1404f1832c02c551b361240c74a63c636b7299f7b78a9` | `7399e1974e1cd987bc845c9bdc13df16d0650d73a228c4cd3046694635be7ddd` |
| `hoverfix-installer-de-1440-normal.jpg` | `45bc9d9c25b0873ea811fa390f4cb8c9353d19ccf0e7365164751b78b72606fa` | `601e5ee27e58f112b0b3598577012140c4e4c758c5c194d27f9b3b9126bbdf8e` |
| `hoverfix-installer-de-390-action1-hover-focus.jpg` | `842c0d679dbbab521aeacf2ace69c4edaaf9822f406718c1f401be0926eed44e` | `1652fcf8cb1ad829e32aa9136dfca46269deee015139c85a1350a5b8d8864b9b` |
| `hoverfix-installer-de-390-action2-hover-focus.jpg` | `9c68e3baabeba2105850645f7c5c13791f5f1eb2f90100cd1eea0d57b2a382d3` | `b2abcff8d406518c4d00824069857221f0143816870f85df0c8759f1d625e730` |
| `hoverfix-installer-de-390-normal.jpg` | `25d9b1d344e7e796a79e98a5443b444931f462f2a1b2569cd357e1340834aee5` | `755d0a9fa60e2c66b850bd06b3ab39736aeb9367e8eb9bab59a9a32c973b20a7` |
| `hoverfix-installer-en-1440-action1-hover-focus.jpg` | `73669b7a7e9da159be1a05230a84816225adbd6e923f71c8d1102f38ae66b48a` | `3143367bb618e80d5eebf7e4e6720b2755118acbdf4dcbd548bd3404826a4bf4` |
| `hoverfix-installer-en-1440-action2-hover-focus.jpg` | `1986eb253f0edb2530220bf2350e1d657567e523083daf9ff374ab0e902cf373` | `73e1319e9ffb2f28e7dacb37f12628a5f041c73b3a5f62dc83e033f54c1e5d17` |
| `hoverfix-installer-en-1440-normal.jpg` | `beacee3b008b308e9ca08cef551faec996523092250fa2d32b973dd14e28ca5b` | `9a2a7f95f6808ba4a1326c6a144d9dfdbda9ee1478728c62d46cf8fb56932fb1` |
| `hoverfix-installer-en-390-action1-hover-focus.jpg` | `b0d4b707821ea82ba3d2d6bb0cc417b7915139c02e22e29f427e47e94a261b9a` | `c576f45a2c89fd0c84ad1419a3830c2270a55aac1ec40e3fefc2dd567858ecbe` |
| `hoverfix-installer-en-390-action2-hover-focus.jpg` | `85ced074325c131ec90c933128cd94bbef9662dc307b01d9aa3bf83bb41fe8e0` | `22a3768bd7600511cff16a3bc30d9f261dd2e73b59f7d9a5e183e88f242fdb82` |
| `hoverfix-installer-en-390-normal.jpg` | `afeeb99cbc1e0be26c231949e49cd93f3f461c4e14442f8d8eedf462498c4d70` | `713449e5750ecd65b84c10db0f1889ec253c9d6550ab6b0a85518eee3d78f7c3` |
| `hoverfix-services-de-1440-action1-hover-focus.jpg` | `32548f771778f74c3f279419b14b2b713e7ae47f71ea0c4c37b0cf03b73101bf` | `dee0e76e72947864a434d1365e1e05513b5a62fd908a0e9413445f357a37a8dc` |
| `hoverfix-services-de-1440-action2-hover-focus.jpg` | `1fa6e42722196082c36ff1a33e6ac914d69cf53768a3de1dac78d70782b09c16` | `7218ce9a54c7611496faa270e76cd3de1f8f9658686cd7bb70b3c131cbc98f92` |
| `hoverfix-services-de-1440-normal.jpg` | `140da968ccb612a8c93c258f2c4e30214203acb4d7f36211158ae95b7c113da0` | `caa5eff3b6b99517121b55b1c8fd660a71e7672d25888251128fe87618c1f5fa` |
| `hoverfix-services-de-390-action1-hover-focus.jpg` | `37e90102aac6a65b7f43ec56d7492271fb26c86c9a5c9d20f1162bc79b52a55c` | `d389e7e2e9bd88eb118f5728f0e6535a5791212469a0678a7e5bb78d4f4145b3` |
| `hoverfix-services-de-390-action2-hover-focus.jpg` | `097b635b2623383904153a97bc9437f8fdb3ff726523dde8f487b71e59e046b9` | `0a04a274b8cf6fc0fe679595159a8e1be109767862d5d44e150420fe4160d442` |
| `hoverfix-services-de-390-normal.jpg` | `454d0b9610ca7ef440ec838642c708e5a5e6b04c6006359bb699521341f270fd` | `c06d11073515e696a77ccb40d663255c9680fe46fb4930567063fc1f168a0c49` |
| `hoverfix-services-en-1440-action1-hover-focus.jpg` | `6187fbf679902ecdfdea64b23768d5669935c2e890cb56ed75c2e042e4364409` | `01ff1cac730d7b57a494a9c5111d27502597d2b5acd68ce7d47e6babca4d1187` |
| `hoverfix-services-en-1440-action2-hover-focus.jpg` | `552a2716eb10869c6040dee3dd321433020558a8b7fb6349e9755518ab46ecbd` | `183de487247c7345e2766ea1265cfaafaac5353e32cf0f8cbe9bccd32fec007c` |
| `hoverfix-services-en-1440-normal.jpg` | `acdb829b95d42a7f1d0e9863dad40e1b8198790ec29bdef4951bf2ee9b5b7a0a` | `75d87fd578424cddb8ea17fcc9603afc8a7b3a035419fe00a7fe8c97dc7fbd49` |
| `hoverfix-services-en-390-action1-hover-focus.jpg` | `5ab8476079ef710f665c6c923726a47f6827520a3b148a2c5c4a31b952544bae` | `8c6c2f38ff545c29df0748e563fc02924e361a257b651ffd68c6943478a5c60d` |
| `hoverfix-services-en-390-action2-hover-focus.jpg` | `a6a004675d5c916e328d5f8a2abda4992b4c544b4be164a73bd60fa7af65bc19` | `97db74a71a12e47e0ab63ae23bdf82c551eb1e0663148806e2328b578dbb8854` |
| `hoverfix-services-en-390-normal.jpg` | `6fa8866eb4e853de911a1e1bdc1462f93630231beaf968b4b9cca1b029e8883e` | `00037be2a0081fd3a1a4216b06785d18a50f9a649a2a92e2352c2fd7473852fd` |
