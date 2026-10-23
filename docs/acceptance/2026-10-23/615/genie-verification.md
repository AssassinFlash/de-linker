# Genie publication boundary verification

This records local source and fixture evidence for the Genie portion of
phase two. It does not claim a production deployment or real-site acceptance.

The source contract uses WooCommerce's current published products and their
current document associations. Genie captures the complete current candidate
and evidence set, verifies it after the service reply and before release,
and signs only the normalized, complete product list. New draft writes and
saved product lists verify the same signed dependencies again. Restoring a
historical conversation does not issue new action tokens. Account history
retains its own product labels and identifiers.

Actual permission changes return HTTP 409. Authority transport, malformed
verification and failed request-local cache refresh return HTTP 503. PHP
proxy tests exercise actual WordPress HTTP responses for both service status
contracts; Python FastAPI tests use an HTTP transport fixture to withdraw
permission or fail the authority after the model begins preparing a reply.
The reply is not released in those cases. Browser-state tests verify the
distinct visible reasons and retained input.

The proxy checks permission before recording an answer and again before
releasing it. If permission changes during the native record operation, the
unsigned historical snapshot can remain while the current response is
refused. No action token is released, historical restoration does not mint
one, and the Python turn boundary excludes historical assistant messages from
new fact sources. This preserves history without granting fresh permission.

English published products with a draft German twin are refused by Get,
Search and Compare. The explicit fixture marks the twin as draft and asserts
that neither its title nor its permalink is read. Permission is also checked
inside ProductText, so an input product's published status alone is not enough
to authorize a translated post.

The automatic knowledge worker is exercised using the installed command's
absolute interpreter and script arguments, with PYTHONPATH removed and an
unrelated working directory. The installer renders those same arguments.
When a host alias is configured, loaded-version verification uses a single
SSH call to the serving process's private loopback endpoint, with the token
on stdin. It does not depend on a persistent local forwarding process.

Build creation is journaled immediately after the directory is made. Failed
parsing/building/publishing removes only that worker-owned pending directory;
a later locked run recovers an abandoned pending build. Successful local
generations rotate only after loaded-version verification and the accepted
Woo acknowledgement. Tests preserve unrelated shared/evidence directories.
The actual publish report supplies its index version, and loaded verification
reads the running service rather than a disk-only manifest.

Local checks on 2026-10-23:

- Genie Python full selected suite: 2,088 passed, 1 skipped, 195 deselected,
  6 expected failures; Ruff and mypy pass on the owned service/index/ops scope.
- Current-publication abilities and comparison fixture selection: 37 tests,
  224 assertions, passed.
- New Genie browser refusal/save-state selection: 13 tests, passed.
- Tools PHP unit suite: 310 tests, 2,428 assertions, passed.
- PHPStan passes on the modified Genie runtime and tests, publication
  abilities, locale fixture and native Genie action integration test source.
- PHPCS passes on all PHP files in this final delta; TypeScript type checking
  passes for the tools package.

The native Genie action integration tests are included for the root owner to
run against the existing real WordPress/WooCommerce fixture. Browser checks
at 1440 and 390 pixels in English and German, independent Spec/Standards
review, aggregate language-bundle assertions, deployment and live readback
remain root integration acceptance gates. The earlier aggregate browser unit
run had unrelated configurator timing failures and language extraction gaps;
it is not reported as a full green run here.

After merging the root integration changes through `c32ce658` (including
`12860cf6`) into local merge `15398415`:

- Tools PHP unit suite: 311 tests, 2,431 assertions, passed.
- Tools browser unit suite: 506 passed, 3 failed out of 509. Two failures are
  translation unused-text assertions being updated by the root integration
  owner. The third is the existing Steps Chromium check's five-second limit;
  its complete file passes separately (8 tests, 4.55 seconds).
- Commerce PHP unit suite: 1,252 tests, with four errors and six failures in
  the newly changed FAQ/evidence/document-management presentation fixtures.
  The root integration owner is fixing those owned fixtures. The modified
  Genie abilities and comparison fixtures pass in that combined run.

These aggregate failures are disclosed rather than excluded or presented as
completed acceptance.

After merging `6ed933d7`, the updated language-source assertion and the new
independent Genie/hero JSON test both pass (9 tests). The retrieval review's
duplicate direct/neighbour permission decoration now uses one helper; its
current-association fixtures cover English and German with neighbour expansion
both enabled and disabled. The complete publication/retrieval test files pass
(59 tests), together with Ruff and mypy for that change. No additional full
suite is claimed after this narrow refactor.

No site instance, daemon, port, snapshot or backup was created by this Genie
handoff. The existing assigned worktree and its lockfile-built dependencies
remain active for the root owner's aggregate review and real-site fixture
work. They can be reclaimed when that integration is accepted; no additional
runtime copy is needed for this handoff.
