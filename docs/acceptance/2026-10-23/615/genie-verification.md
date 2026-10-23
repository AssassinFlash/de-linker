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
