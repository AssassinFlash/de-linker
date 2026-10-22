# Independent Standards review — public company-email preservation

Verdict: **PASS for frozen aggregate `9c3bf6a1c44ade8422f23b59ddec9f9556030ef93aa1e95ebebadaa6e4879180`**. No actionable Standards or privacy-boundary defect was found in the complete production diff or new permanent tests. This is a source and isolated-consumer conclusion; it does not close snapshot import, website visual acceptance, production deployment or the wider site audit.

## Exact reviewed scope

Worktree: `/Users/chesterjohn/.codex/worktrees/visual-pull-public-email/de-linker`, branch `codex/pull-public-company-email`, HEAD/base `5da007fabb2beca2356da353a4b7dafa5eb3225c`.

I read the full tracked diff, full untracked test file and bounded acceptance documents. I independently recomputed the manifest's SHA-256 aggregate from sorted `SHA256 + two spaces + repository-relative path + LF` entries and rechecked the same bytes after testing:

| Candidate file | SHA-256 |
| --- | --- |
| `tools/pull/src/linker_pull/anonymize.py` | `5914ca7c9b08b0b73f129bb40d984b775cff8874ad2cf98c8d5c10f6241f1d17` |
| `tools/pull/tests/test_public_company_email.py` | `29fb49e8d12aca4773f917ca1dbb96bc371da6612ed75248d41f418ae1d64f79` |
| `docs/acceptance/2026-10-22/pull-public-company-email/README.md` | `7749ac2ea248f15f8a5aac1b6beb695eb3cf11d220eb4451c1ca994651ef22be` |

The only production edit is the anonymizer. I also traced its actual consumers through `sqldump.py`, `phpserial.py`, `snapshot._database()` and the CLI anonymize path. The SQL parser/writer, snapshot producer, loader and serialization implementation have no candidate change. Reviewer reports added afterwards are outside the original three-file aggregate.

## Standards and privacy findings

**Field ownership is explicit and remains local.** `anonymize.py:479–490` checks the exact parsed `wp_posts` table and the original decoded `post_type`, `post_status` and `post_password` values. It reads these before `_posts()` clears a page password for the local replica. Only `page` / `publish` / originally `''` qualifies; NULL or nonempty passwords do not. `:502–506` grants the exception only to that row's exact `post_content` column. Eligibility is recomputed for every row, and the flag is passed as a value rather than stored on the anonymizer. It cannot transfer to the next row, title, excerpt, unknown column, page-associated metadata or another table.

**The private-data default is unchanged.** `Emails.replace()`, `replace_all()` and `Anonymizer.scrub()` add a keyword-only argument whose default is false. The customer map retains priority on every default call. `Emails.keeps()` is unchanged, including its use by comment-author handling. Existing noncolliding company-domain and staff policies remain as before. The public branch at `:356–361` accepts only the existing exact company-domain policy, case-insensitively; it preserves the original address bytes and does not expand to unrelated buyers or company-looking domain suffixes. No credential, new personal-address list or wider privacy configuration is introduced.

**Preserving a public mailbox does not bypass redaction.** `scrub()` still performs JSON credential-key removal, recursive serialized-member credential checks, guest/customer email replacement and the existing hash, secret and payment-identifier removal. Serialized recursion carries the qualified field's flag, while its credential values are emptied before email preservation can apply. The new `_replace_match` call shape has no remaining incompatible call site. The context parameter has one narrow purpose; replacing it with a larger policy object would add complexity without improving this boundary.

**The real storage path stays authoritative.** `Anonymizer.run()` and `snapshot._database()` both pass parsed SQL inserts through the same `_insert()` implementation. The latter still observes and writes the transformed stream, scans the resulting gzip and deletes failed output. Unsupported INSERT shapes and wrong row widths are rejected by the unchanged parser; missing columns required by `_posts()` also raise rather than emitting a partially qualified row. Missing status alone merely prevents the exception. Untouched SQL values keep their original literal bytes; changed values use the existing `Value.of()` quoting path. PHP serialized values use the existing recursive rewrite and UTF-8 byte-length repair. No new escaping, import, exception-swallowing or alternate write channel was added.

**The tests exercise consumers and privacy controls.** The 24 new permanent cases drive account discovery, the actual anonymizer stream and SQL readback, rather than mocking email replacement or checking that a boolean exists. They cover the colliding public/customer address alongside private identities and metadata, password/status/type exclusions, row/field/table isolation, quoted markup, literal backslashes, JSON and PHP serialization, credentials, case and domain-suffix boundaries. Assertions compare exact content/redaction values and serialized lengths. The fixture contains synthetic account data and already named public company addresses, with no copied customer payload or secret. The change introduces no page composition, PHP design, snippet, customer copy or language-route change.

The documented scope deliberately excludes posts, products and LC template post types even if publicly rendered. It also does not claim to classify every third-party access restriction. Those are not additional permissions granted by this change.

## Independent execution

I fixed private copies of the candidate and exact original source, used the already-installed worktree interpreter, and set `PYTHONPATH` to the respective private source directory. Each run records the imported anonymizer's actual path and SHA. No dependency install was needed. Copied bytecode directories were removed from the private copies before the final recorded runs; the initial otherwise equivalent runs remain retained separately.

| Run | Actual result |
| --- | --- |
| Candidate permanent cases plus existing anonymize, sqldump, phpserial and scan tests | **86 passed** |
| The identical final 24 permanent cases with the base anonymizer (`75fbcc8d8092befe8b7bc0aa59657c8d37dd5db322f6f067c4701d75d4b9bcb2`) | **8 failed, 16 passed** |
| Additional private Standards controls | **7 passed** |

The additional controls independently verify:

- Both supported INSERT formats each process 64 interleaved type/status/password combinations with reordered columns. Only the one exact public combination preserves the body; every title and excerpt remains mapped, including after protected passwords are locally cleared.
- Handling a public body and an explicit public `scrub()` call does not alter later default `scrub()`, `Emails.replace()`, `replace_all()` or `keeps()` behavior on the same object.
- Nested serialized values preserve the qualified contact address while removing `smtp_pass` / `token`, pseudonymizing a guest and retaining exact Unicode/path bytes and rebuilt nested lengths. The subsequent default call produces the exact private form.
- Missing required post columns and an INSERT with the wrong width fail without yielding that INSERT's private row.

The original-source failures are the expected public-preservation regressions. The same private/nonpublic controls still pass on the original. No assertion was weakened between variants.

## Evidence and acceptance boundary

Independent evidence root:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/pull-public-email-standards-20261022T084137442858Z/`.

| Evidence | SHA-256 |
| --- | --- |
| `review-evidence-manifest.json` | `82181adb69bbd611c9500cf2dae58992d9d1ba55936d35a2af2cf9523e869d68` |
| `related.log` | `6a19f8df05882d779de750712ac1f36d97e2cda0862a7ec54490dd3fd24729d1` |
| `before.log` | `e4d2ffc4f4308d292732ccfb06b3679987058632ebb98411a4618af27729d9f5` |
| `controls.log` | `48c5696fc05812f4fa3fb6a8c8b8374820243316710b456ba8d038effb5655cf` |
| `candidate/tests/test_standards_boundaries.py` | `9ec35f2d038b2ebbbeaac4de67e6ce86e52f91d6a89a581778fba95417b3bb1f` |

The manifest binds the exact production diff, original/candidate provenance, private fixture, runner, raw results, import identities and per-run commands/environment/exits. The independently authored Spec report and its native SQL/PHP readback report are separate evidence by that reviewer. I read their stated boundaries but did not relabel their native execution as mine. Producer Ruff/mypy results likewise remain producer evidence.

This review executed isolated Python fixtures only and wrote this review document plus private evidence. Application source, permanent tests, instance/database state and production were not changed. A full snapshot/WordPress import, fresh-browser EN/DE acceptance and deployment/readback require their own evidence; neither this PASS nor the separate native synthetic fixture substitutes for them.
