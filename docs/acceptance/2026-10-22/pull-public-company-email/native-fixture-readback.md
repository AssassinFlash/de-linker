# Independent native SQL fixture readback

Verdict: **PASS for the anonymizer-to-native-MySQL storage and PHP serialized-value consumer boundary**, using frozen source aggregate `9c3bf6a1c44ade8422f23b59ddec9f9556030ef93aa1e95ebebadaa6e4879180`. This adds a real SQL import/readback to the earlier isolated pure-test Spec report; it does not claim a complete WordPress snapshot import, site behavior, visual acceptance or deployment.

## Exact source and authorized environment

The real stream processor was imported from the fixed independent Spec copy at `pull-public-email-spec-20261022T082333905783Z/candidate/src/linker_pull/anonymize.py`, SHA `5914ca7c9b08b0b73f129bb40d984b775cff8874ad2cf98c8d5c10f6241f1d17`. The current worktree's three frozen source/test/README hashes were rechecked unchanged when this report was written. The implementation and permanent tests were not edited.

The fixture is entirely synthetic: fake customer 42 uses the already named public company mailbox, fake customer 43 uses `buyer@customer.example`, and an unrelated guest uses a reserved example address. There is a dummy credential string, not a real secret. No existing WordPress instance, customer, user, order or content table was read. The only server-wide metadata reads were server version and exact existence checks for this reviewer's unique database names. Authentication used the existing local root socket with `--no-defaults`; no password file, grants, user creation, global variable change or server restart was needed.

Actual client: `/opt/homebrew/bin/mysql`; actual server: **MySQL 9.6.0**. The imported dump sets UTF-8 and an explicit **session** SQL mode for that one client process. It does not alter global SQL mode or other connections.

## Real consumer path

1. Privately generate a minimal WP-shaped SQL dump: 8 tables / 23 rows, with numeric ID columns and utf8mb4 LONGTEXT payload fields.
2. Scan the same synthetic stream through the real `accounts_from_dump` and `Anonymizer.run` implementation. Retain the exact before and anonymized SQL privately.
3. Assert that `linker_pull_email_verify_20261022_083428_3b0ed87b` does not exist, then create precisely that database without `IF NOT EXISTS` or grants.
4. Import the actual anonymized SQL through the native MySQL client, without `--force` or ignored failures.
5. Query every fixture table through `SELECT HEX(CAST(column AS BINARY))`. Decode those stored bytes and compare with independently constructed expected content/redactions, rather than merely re-parsing the anonymizer's SQL output.
6. Feed the actual MySQL-read nested serialized values to standalone native PHP 8.3 `unserialize(..., ['allowed_classes' => false])`; require outer and inner `serialize()` byte equality and expected values.
7. In `finally`, drop only that exact owned database and query its exact name again. The post-drop count is **0**. All commands in the successful run exited 0.

The public exception applies only to the fixture's qualified post-content rows. All other SQL tables and records remain private consumers of the original customer-first path:

| Native readback boundary | Result |
| --- | --- |
| Public HTML body and mailto | Company mailbox preserved; registered buyer anonymized. Exact expected quotes, Unicode and literal JavaScript/Windows-path backslashes survive. |
| Public JSON body | Exact expected JSON bytes; company contact preserved, buyer/guest anonymized, `api_key` and `smtp_pass` empty; path, escaped Unicode text, quotes and German text intact. |
| Public nested PHP-serialized body | Company contact preserved; buyer anonymized and `smtp_pass` empty. Exact expected UTF-8 string lengths and nested native PHP roundtrips pass. |
| Password-protected, private, draft, non-page and NULL-password content | Company-address collision remains customer42's pseudonym. The later local clearing of a protected/NULL password does not grant an exception. |
| All page titles/excerpts | Customer-map precedence retained. |
| Customer accounts and user billing meta | Customer42/customer43 emails pseudonymized. |
| HPOS billing and order metadata | Pseudonymized, including nested serialized private payload. |
| Page-associated post meta | Public-page association grants no exception; text, JSON and serialized payload stay private. |
| Comments | Author/email/content remain under existing private-data rules. |
| Unknown table with otherwise identical page/publish/empty-password columns | No public-field exception. |
| All stored native fields | Dummy API secret absent; the company mailbox appears only in the three specifically qualified public `post_content` fields; the other buyer's original address is absent everywhere. |

**24 explicit checks passed** over the actual native readback. Both public/private serialized values passed standalone native PHP's outer and inner byte roundtrip and semantic checks. This tests SQL quoting, client encoding, database storage and a separate serialization consumer, rather than repeating only the earlier 86 Python tests.

## Preserved initial verifier failure

The first attempt imported the same anonymized synthetic SQL successfully, but its reviewer readback expression used `HEX(ID)` on numeric IDs. Native MySQL returns the hex representation of the number there, not the bytes of its decimal text, so the reviewer's text-byte decoder failed. This was a fixture readback error, not a product failure or failed import. That attempt's own database `linker_pull_email_verify_20261022_083351_fe7fc882` was dropped in `finally`, and its exact post-drop count was also 0.

Its source, SQL, failure trace and command results remain untouched at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/pull-public-email-native-spec-20261022T083344872568Z/`. The corrected attempt uses `HEX(CAST(column AS BINARY))` for every column. Before/after SQL bytes, product source, fixture values and expected assertions are identical between attempts. No assertion was removed or weakened; the original and corrected SQL files were independently compared byte for byte when this report was written.

## Evidence and cleanup

Successful fixed evidence root:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/pull-public-email-native-readback-20261022T083423274612Z/`.

| File | SHA-256 |
| --- | --- |
| `original-synthetic.sql` | `1a04e6ace0c29377c55d6923b34417c10d5f3d48bd1af880b1b873d8088f12da` |
| `anonymized-synthetic.sql` | `028ace411e8b9c48271ee33a34fec259ae1204716a16909c882ed2fae6e39bf7` |
| `collector.py` | `6f63ba1a30c77210cc7af4cca2b89a8a6da60ba99b2ff36385f776acbc054733` |
| `native-selected-values.private.json` | `55c7bae1f04047757a04c7e102e427a62956c7d3a047e631b431f386ae348f78` |
| `php-native-unserialize.stdout` | `faf00c209d894c92a60241cfaccbe20376b85414372011c65a774dcdeb8640bf` |
| `results.json` | `5079354ba648de8a872db9395e255780e5899e0915e0f00d5cef87d60ee0769e` |
| `manifest.json` | `865b96014b9089bb7b62ee9aef9bc6e489a00f2f9d68c6e6cb88a8ff8344852d` |

The manifest binds original SQL, transformed SQL, collector source, all native import/SELECT/cleanup stdout/stderr, PHP readback and results. `results.json` contains the exact native commands, scoped database name, session-input hashes, times, checks and cleanup confirmation. `prior-harness-diagnostic.json` records the reason for the one readback-expression correction. Synthetic values remain private as requested; no SQL or selected row body was added to the repository report.

The only database mutations were creating, importing into, and dropping the two unique review-owned disposable schemas. Both are confirmed absent. No existing schema was imported, modified or dropped, and no global privilege/settings operation, real snapshot pull, browser, mail, model, production, commit or deployment operation occurred. A full-snapshot/WordPress-runtime claim would require its own authorized acceptance and is not implied by this narrow native fixture PASS.
