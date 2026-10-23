# Woo publication foundation verification

Scope: [unified Woo product/document authority](https://github.com/AssassinFlash/de-linker/issues/614), implementing [the confirmed publication rules](../../../specs/609-product-publication.md) and [the authority contract](../../../specs/614-publication-contract.md). These are local backend results; they do not constitute production deployment, aggregate Spec/Standards review or customer visual acceptance.

The existing `publication614` instance was reused. Its actual PHP process, executable, router and plugin symlink were checked before running fixtures. Runtime: PHP 8.3.35, WordPress 7.1.3, WooCommerce 11.2.0, Redis external object cache, request-local flush supported. No additional instance or full-site snapshot was created. It is a bare pipeline fixture, unsuitable for UI acceptance until the integration owner loads the verified site snapshot.

| Verification | Result |
| --- | --- |
| Commerce full unit suite | 1,234 tests, 6,395 assertions, PASS |
| Commerce PHPStan level 8 | PASS |
| Commerce WPCS over changed PHP files | 28 files, PASS; final edited subset rechecked after the last increment |
| I18n full unit suite | 276 tests, 626 assertions, PASS |
| I18n PHPStan and WPCS on the changed seam | PASS |
| Local router WPCS | PASS |
| Actual WordPress/Woo fixture | 30 checks, PASS, [small result](wordpress.json) |
| Actual concurrent HTTP/native Woo fixture | 32 checks, PASS, [small result](http.json) |

The WordPress fixture uses actual Woo products, Polylang pairs, media records, file bytes, metadata events and preparation leases. It verifies shared A/B PDF rights, no equal-SHA permission transfer, last-relation withdrawal, media withdrawal, stale acknowledgement rejection, actual native WordPress rewrite installation with preservation of an outside emergency marker, same-URL replacement, and figure binding. Re-running initial figure adoption or saving an unchanged fact does not attach an old number to replacement PDF bytes. The product editor visibly identifies the affected fields; an actual changed Woo fact can acquire the current binding. Initial figure adoption records existing explicit source associations and does not claim all existing numeric values were semantically checked anew.

The HTTP fixture verifies current GET/HEAD/Range behavior (200/200/206), no public caching, unassociated-path 410, unauthenticated worker 401, two distinct PHP workers sharing Redis, and withdrawal while the held process has already primed native post and metadata caches. It also creates an actual native Store API draft, withdraws its canonical source while the German mirror stays published, and verifies both direct product routes, collection inclusion and the old draft. Original and alias PDF requests then return 410 with zero bytes.

A real HTTP test discovered that internal `lang=all` became a native WordPress `language=all` taxonomy constraint and incorrectly produced an empty authority. Internal queries now use an empty native language plus a server-only boolean marker respected by the language companion. Native Woo builds its query from named supported request fields; it never copies the marker from HTTP input. The HTTP fixture explicitly tries `linker_publication_internal=1` in both language scopes and after canonical withdrawal, and confirms that it grants no additional language or publication access.

Unsupported or failed request-local cache refresh now returns 503 `publication_unavailable` on authority/feed routes; original-document streaming returns 503 without bytes. Unit fixtures cover both missing capability and an actual failed flush. No Redis database flush is used.

Reproduction uses these checked-in fixtures:

- `plugins/linker-commerce/tests/fixtures/publication-authority.php`: run with `wp eval-file <absolute-path> verify` on a local fixture instance; its `cleanup` argument removes only its own generated products/files/options.
- `plugins/linker-commerce/tests/fixtures/publication-race.php`: temporarily require this file from that local instance's MU directory. It refuses non-local environments and supplies only the synthetic race fixture.
- `plugins/linker-commerce/tests/fixtures/publication-http.py`: run after the WordPress fixture and local-only race harness are installed; its endpoint is fixed to `127.0.0.1:8888`. It restores its source state in `finally` and does not print session tokens.

After verification the fixture data and temporary MU loader were removed, the fixture route was checked unavailable, and the instance was released to the integration owner for immediate reuse. The running instance is retained only for the active aggregate acceptance task; integration must repoint it to the aggregate checkout and load the verified online snapshot. The source worktree remains until its unmerged commits and unique evidence are accepted. No production writes, deploy, main merge, new backup or extra worktree occurred in this implementation subtask.
