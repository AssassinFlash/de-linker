# Independent Spec review — published company-email preservation

Verdict: **PASS**, limited to frozen aggregate `9c3bf6a1c44ade8422f23b59ddec9f9556030ef93aa1e95ebebadaa6e4879180`. No actionable Spec blocker was found. This is the independent Spec axis, not a replacement for the separate Standards review, native import/readback, or whole-site acceptance.

## Fixed scope

Reviewed worktree: `/Users/chesterjohn/.codex/worktrees/visual-pull-public-email/de-linker`, branch `codex/pull-public-company-email`, HEAD/base `5da007fabb2beca2356da353a4b7dafa5eb3225c`.

I read the complete tracked production diff, the full untracked permanent test file and both acceptance documents, and independently recomputed the sorted manifest aggregate. Exact bound files:

| File | SHA-256 |
| --- | --- |
| `tools/pull/src/linker_pull/anonymize.py` | `5914ca7c9b08b0b73f129bb40d984b775cff8874ad2cf98c8d5c10f6241f1d17` |
| `tools/pull/tests/test_public_company_email.py` | `29fb49e8d12aca4773f917ca1dbb96bc371da6612ed75248d41f418ae1d64f79` |
| `README.md` | `7749ac2ea248f15f8a5aac1b6beb695eb3cf11d220eb4451c1ca994651ef22be` |

The only production change is the anonymizer. No SQL parser/writer, snapshot loader, native WordPress importer, credential configuration, model route, page content, translation or UI source changed. This report is an additional reviewer artifact and is not part of the candidate's pre-existing three-file aggregate.

## Contract and source behavior

The requested exception is narrow: preserve an already public company-domain mailbox in **only** a confirmed `wp_posts` row with exact `post_type='page'`, `post_status='publish'`, and an originally empty password, and only in that row's `post_content`. Customer identity and private records retain the old customer-map precedence.

The implementation meets that contract:

- `anonymize.py:479–490` determines eligibility from the actual parsed table/column values before the per-table post rule runs. In particular, the existing rule's later clearing of `post_password` cannot make a formerly protected page appear public. Absent status/schema, NULL password, nonempty password, non-page type and non-publish status cannot qualify.
- `:502–506` passes the exception only for the exact `post_content` column of that eligible row. It is a local per-value argument, not mutable anonymizer state. Title, excerpt, unknown columns, next rows, post meta, user meta, HPOS/order records, comments and unknown tables retain the default false flag.
- `Emails.replace():356–367` bypasses customer mapping only for the existing exact company-domain policy when that field flag is true. It does not treat every address on a public page as public. Domain matching is case-insensitive, preserves the original address's case and rejects company-looking suffixes/subdomains. Neither `Emails.keeps()` nor the default customer-first behavior is relaxed.
- `scrub():515–537` keeps the existing JSON credential pass, recursive PHP-serialized credential-key checks, general secret/hash/payment removal and guest/customer pseudonymization. Qualified presentation context is carried through serialized members in the same already-qualified field; it is not attached to another database row or column. Existing SQL/PHP serialization code still handles escaping and repaired byte lengths.

The exception changes which email replacement is chosen, rather than skipping `scrub()` wholesale. That is why a public contact mailbox can survive while a credential-valued field and unrelated buyer address in that same body are still scrubbed. There is no global reorder of the private-data policy and no new allowlist of personal addresses. The requested published `page` scope intentionally does not extend to public products, posts, LC template types or private fields.

## Independently executed consumers

I copied the source and tests to an isolated private directory and used the worktree's already-existing Python environment, with `PYTHONPATH` pointing at the fixed copy. No dependency was installed. Actual module `__file__` and SHA were recorded for candidate and original variants, so these runs did not silently import the editable source from another worktree.

| Actual run | Result |
| --- | --- |
| Candidate new permanent cases plus existing anonymize, sqldump, phpserial and scan files | **86 passed** |
| The same final 24 permanent cases over `git show HEAD` original anonymizer, SHA `75fbcc8d8092befe8b7bc0aa59657c8d37dd5db322f6f067c4701d75d4b9bcb2` | **8 failed, 16 passed** |
| Additional independent dump-stream/handler controls, private copy only | **5 passed** |

The original-source failures are the expected public-preservation cases, while private/nonpublic controls continue to pass. The permanent tests drive `accounts_from_dump` → `Anonymizer.run` → actual SQL parsing/readback, including a single colliding customer/public mailbox, customer/user billing/HPOS/private metadata, comments, missing/NULL/protected/nonpublic cases, next-row/unknown-field isolation, SQL quotes and literal backslashes, JSON-escaped markup, serialized string lengths, credential keys, case and domain-suffix boundaries. They are not implementation-mirroring checks that only assert the new boolean exists.

The five independent controls additionally prove:

1. Reordered SQL columns still select the intended field; original password `''` permits the body exception, while a space or `'0'` remains protected even though the local post rule later clears all three stored passwords. Excerpts remain pseudonymized.
2. Nested PHP-serialized public content preserves its contact address, empties its `smtp_pass` member, scrubs an external buyer, and remains a valid serialized value with exact repaired lengths.
3. After that same `Anonymizer` handles a public row, a subsequent default `scrub()`, `Emails.replace_all()` and `Emails.keeps()` still use private customer-first semantics.
4. An otherwise identical `wp2_posts` row is not admitted.
5. An otherwise identical `WP_POSTS` row is not admitted.

The SQL roundtrip assertions compare decoded content values byte for byte where no intended redaction applies. They do not claim that every formatting byte of the entire dump stream is unchanged; customer/private redaction and SQL re-encoding are intentional. Existing related SQL/serializer/scanner tests also pass. Worker-reported Ruff/mypy checks were read as producer evidence, not rerun or relabeled as independent checks here.

## Evidence and limits

Independent fixed test root:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/pull-public-email-spec-20261022T082333905783Z/`.

| Entry | SHA-256 |
| --- | --- |
| `review-evidence-manifest.json` | `4f4092a4b2a554355611c10201c284b23071720057a38a9f9d5d65dab960b531` |
| `candidate-related.log` | `236f8973d41a61976382f120142833fa6149744aea38f5bc000d05f615f1904e` |
| `before-permanent.log` | `606f8ec50fc9c37a19a90ad32fd09077adac6329ee9ffa9ffa9b528cd3164d4f` |
| `independent-controls.log` | `ef0e7ef49e71fa999842be0cb8d22ec1058d3a384ed5c0a2ec6efb8f434975ac` |
| `candidate/tests/test_spec_readonly_controls.py` | `40634c8d81a33878b48315772520884b6d80b522ef8f112375ddf475aec0aec2` |

`execution.json`, `source-imports.json` and `independent-controls-execution.json` retain the exact commands, fixed module paths, environment override, exits and raw-log hashes. All fixture addresses/accounts are synthetic or the already named public company mailbox; no real customer table was read.

Only isolated pure tests and read-only source/file comparisons were executed. No application source or permanent test was edited; no checkout/reset, database or instance operation, browser, snapshot import, model, mail, production change, commit or deployment was performed. The previously repaired local 14-page alignment is a separate operation and not evidence that this new snapshot producer has already been imported or deployed. Before final approval, the parent still owns any required native snapshot/import readback and the independent Standards conclusion.
