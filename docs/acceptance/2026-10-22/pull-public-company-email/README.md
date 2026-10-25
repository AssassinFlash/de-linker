# Published company email preservation during local snapshot anonymization

Status: source/test candidate frozen for independent Spec and Standards review. No commit, push, PR, merge, deployment, snapshot import, browser, local instance or production operation was performed.

Worktree: `/Users/chesterjohn/.codex/worktrees/visual-pull-public-email/de-linker`.
Branch: `codex/pull-public-company-email`.
Base: fetched `origin/main`, `5da007fabb2beca2356da353a4b7dafa5eb3225c`.

## Failure and source boundary

The existing anonymizer resolves a customer-account email before the company-domain preservation policy. A synthetic customer 42 with the already public company address therefore changes the public Contact/legal page body and mailto into `customer-42@example.test`. Moving the company rule ahead of customer mapping everywhere would also preserve that address in private account and order records.

The permanent test uses the public stream boundaries `accounts_from_dump` → `Anonymizer.run` → `sqldump.read`, including actual SQL quoting/re-encoding. It supplies no real customer or instance data. It proves the same address is preserved in the public body and still pseudonymized in the customer, user billing meta, HPOS billing email, page-associated private meta, comments and order metadata.

## Narrow implementation

Only `tools/pull/src/linker_pull/anonymize.py` changes production code. The SQL reader already provides column names and row values, so neither `sqldump.py` nor `load.py` needs a new context interface.

The row must belong to `wp_posts`, its decoded `post_type` must be exactly `page`, `post_status` exactly `publish`, and the original `post_password` exactly empty. The password is examined before the existing per-post rule clears it for a local replica; a protected page must not accidentally become an eligible public field. Missing status/schema and NULL password remain unconfirmed. Only that row's `post_content` receives the exception; title, excerpt, other fields, metadata, other tables and later rows do not inherit it.

The explicit flag defaults to false through `scrub` and `Emails`. It only allows a match approved by the existing `kept_as(...)/COMPANY_DOMAINS` policy. Private callers retain the original customer-first behavior and `Emails.keeps` is unchanged. Case-insensitive exact domains remain supported; a company-like subdomain does not qualify. Serialized members receive the same already-qualified field context, while PHP string lengths are still repaired by the existing serializer. JSON credential keys, guests, hashes/secrets and payment redaction continue through the original scrub path.

This preserves existing behavior for company mailboxes that do not collide with a customer account; it does not invent a wider global private-data policy or whitelist arbitrary addresses. No customer-visible copy or translation changed.

## Evidence

Private immutable run root:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/pull-public-email-20261022T081242807375Z/`.

- `first-red.log`: original source, initial actual dump-stream collision test, 1 failed on public text/mailto replacement.
- `first-green.log`: minimal implementation, same initial test, 1 passed.
- `before-tree/src/linker_pull/anonymize.py`: original source bytes, isolated from the candidate. `pristine-source-import.log` proves the replay imported this fixed original.
- `final-tests-on-pristine-red.log`: final 24 permanent cases on original source: **8 failed, 16 passed**. The expected public preservation cases fail; the private/nonpublic controls remain valid.
- `related-green.log`: candidate, **86 passed** over the new 24 cases and existing anonymize, SQL dump, PHP serializer and scanner tests.
- `ruff-check.log`, `ruff-format-check.log`, `mypy.log`: exit 0; formatting 22 files, strict mypy 22 files.
- `command-results.json`: exact replay commands, working directory, environment override, exit codes and timestamps.
- `source-files.json` in this acceptance folder: exact final source/test/README SHA. Private `evidence-manifest.json` binds raw logs and the source diff.

Reproduce in `tools/pull`:

```text
uv run --locked pytest tests/test_public_company_email.py tests/test_anonymize.py tests/test_sqldump.py tests/test_phpserial.py tests/test_scan.py -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy .
```

The related tests are pure file/SQL-stream consumers. Native `test_load.py` is intentionally not run because it creates real WordPress/MySQL instances; no runtime parity or deployment claim is made. The existing locked project environment was created only inside this new worktree. The normal Genie worktree remains HEAD `6bdb8869`, with b472's 19 product sources unchanged; no source or build there was touched.
