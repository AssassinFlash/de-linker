# #246 / PR #290, review round 2

The round-1 implementation is accepted by [Claude's round-2 review](https://github.com/AssassinFlash/de-linker/pull/290). This continuation addresses the atomic connection limit, a separate site-wide receipt allowance, fresh-cookie guest submissions, and the optional-name interface needed by #243. Worktree and local instance: c246 only.

## Accepted pixel gate and reproducible capture method

Claude recaptured live vs c246 at feature head `51e27285`. The full contact page, with **no mask and no tolerance**, passed every language/viewport pair:

| Language / width | Live vs c246: differing pixels | Live repeat control |
|---|---:|---:|
| EN 1440 | 0 | 0 |
| EN 390 | 0 | 0 |
| DE 1440 | 0 | 0 |
| DE 390 | 0 | 0 |

Method recorded by Claude: a fresh browser context for **each capture**, the same Chromium on the same machine, identical viewport, animations disabled, all images forced eager and decoded before capture, and each image wait bounded to five seconds. Fonts are ready before the full-page capture. Repeating the same live URL also gave zero differences. This evidence supersedes round-1's unresolved photo/anti-aliasing residuals: those came from the earlier capture method, not the site.

`tests/visual/pixel-parity.mjs` is absent from the rebased `origin/main` (`71d950db`); the review says #229 will supply it. The method above is retained here so the gate does not depend on the absent shared script. These are the reviewer's measured results, not a claim of a new capture by this continuation.
