# Verification visibility — narrow configurator recovery correction

Base: `2d632574fb655d80ce4031abe7912e443254a201`. This change implements the
owner-authorized visibility correction following the native configurator/PDF
walkthrough. It retains the protection contracts in specs 519 and 521. It does
not claim to explain or resolve Cloudflare's `300030` decision.

The report's existing Download PDF control supplies a semantic `report_pdf`
anchor. The shared resource transport puts verification at a visible matching
anchor before falling back to its existing form/main placement. If a previous
anchor becomes hidden, its old widget/status are removed and the native fallback
remains usable. No CSS, customer wording or report calculation changes are made.

The shared client uses Cloudflare's documented `before-interactive-callback` to
scroll a connected, current, uncompleted challenge into view. Normal passive
success does not scroll. Cancelled, replaced, expired or already completed
attempts cannot cause a late scroll. Server proof, identity, limits, operation
UUID, timeouts and provider routing retain their existing implementation.

A completed design retains its reusable proof. When that idle proof expires,
the resource status becomes empty; the next call still obtains a fresh proof.
An error or expiry during an active challenge still shows the existing failure
and preserves input. Business-form expiration handling is unchanged.

## Official API evidence

The [Cloudflare widget configuration reference](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/)
documents the exact `before-interactive-callback` render option and its invocation
before interactive mode. It also distinguishes token expiry from resetting a
widget. Retrieved through Apify website-content-crawler, one official page,
Playwright Firefox, run `T7E0HF1q14zQEkPH8`, dataset `OnHjCc1tdLKnt35cl`,
1 succeeded / 0 failed on 2026-10-22 UTC. Private raw research contains no
production credentials and is kept outside the repository.

## Deterministic verification

Tests execute the actual components and shared clients, replacing only provider,
HTTP and DOM-layout boundaries. Tools' Vitest configuration explicitly permits
reading the sibling Commerce source for that integration fixture; no second
implementation of the client is introduced.

| Slice                                                                | Observed red                                                           | Green                                                                        |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Native report anchor + transport placement                           | 2 failures / 42 passes: no report anchor; widget appended after report | 44 / 44                                                                      |
| Required-interaction scrolling + stale/cancelled/disconnected guards | 2 failures / 5 passes: official callback absent                        | 7 / 7                                                                        |
| Actual resource transport + actual shared client, idle expiry        | 1 failure / 1 pass: successful old design became a failure message     | Idle expiry cleared, next proof fresh; active failure/expiry still retryable |

Final full JavaScript suites: Tools **488 tests passed**, Commerce **26 tests
passed**. Both TypeScript checks passed. ESLint and formatting of all changed
source/test/config files passed. Both production builds and source/manifest
checks passed. Tools' existing vendor/entrypoint size recommendations remain
visible (three webpack warnings); no CSS artifact changed.

The focused tests also cover a hidden anchor reverting to the native form,
unchanged retained text, proof reuse before expiry, no upstream work on failed
proof, original UUID recovery, and actual cancelled/replaced challenge behavior.
All are offline: they do not call a real challenge, engine, model or mailer.

## Native and visual handoff boundary

The owned local instance is `v563`, port 9368, prepared from the
existing complete live snapshot `/Users/chesterjohn/de-linker-data/20261022-2159`,
with this worktree's plugins. Its local-only controlled fixture preserves native
same-origin nonce, prepare, verify, receipt and resource consumers; only the
external widget/Siteverify and configured loopback engine transport are synthetic.
Mail and outbound isolation remain installed. The fixture is not shipped or
activated by this implementation.

Native HTTP preflight proved: missing proof returns HTTP 400 `linker_admission_proof`;
original prepare/verify returns HTTP 200 for design and report_pdf; guarded design
returns its synthetic result and complete report; guarded PDF with the actual
`{input, logo}` envelope returns HTTP 200 / application/pdf / 1350 bytes. `pdfinfo`
independently reads the synthetic artifact as a valid one-page PDF 1.7. This is
HTTP/file evidence, **not a browser download**. Both native EN/DE pages return200
and load the fixture/mount. The imported site has 212 published products, 2756
attachments and 0 missing attachment files. Local mail capture has 0 files.

Native present first refused stale WindPress cache as expected, then
`--allow-stale` installed the local presentation for root to compile before any
visual verdict. The stale-cache gate is not claimed passed. Initial instance
setup also exposed a native rewrite child using 128 MiB and exhausting memory in
the snapshot's ACF. A private shutdown probe confirmed it; only this instance's
WP_MEMORY_LIMIT was aligned to its existing 2048 MiB php.ini, rewrite/flush then
succeeded, and the probe was removed. No global or other-instance setting changed.

A clock-advance fixture additionally caught an overly strict wall-clock guard in
the new scroll callback (1 failure / 6 passes). The final guard uses explicit
provider expiry/current lifecycle rather than a new wall-clock cutoff, preserving
the original challenge timer and proof semantics. Final full-suite counts above
include this case.

EN/DE at 1440/390, actual interactive placement and browser PDF download readback are assigned
to root after native presentation/WindPress setup. They are **not claimed passed
by these offline tests**. Native or browser acceptance details will be recorded
separately after they occur. Production is unchanged by this branch.
