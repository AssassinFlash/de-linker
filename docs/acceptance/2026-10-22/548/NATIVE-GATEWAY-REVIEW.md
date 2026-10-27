# Native gateway, input and receipt review

2026-10-23. Fixed final component: `ca4918ef02b640697725316e2ca33375fe01a7c3`.
The full workbench goal remains active. This record covers native identity,
bounded public admission and stable input/receipt recovery, not the full UI,
equipment qualification, country rules or production release.

## Findings and corrections

The initial native bridge was not accepted merely because its private hop
worked. Independent review and real native fixtures found public pre-parser
coverage missing for non-POST methods, refusal state leaking when WordPress
reused a request for an unrelated route, and a second PHP canonicalization
that disagreed with the engine's durable command intent. The gate now covers
all planner methods with bodies, clears and reasserts refusal at the native
parser boundary, and leaves unrelated native requests alone.

The engine's existing mutation receipt now supplies both the canonical intent
hash and the actual command scope. Scope was added after review reproduced a
same-key command targeting a different project. Native quota recovery cannot
settle that other mutation against the first project's reservation. Expired
native metadata does not erase the engine receipt or charge its replay again.

PHP's JSON number representation was also an actual counterexample: a large
integer could be rounded on re-encoding while its input hash still named the
original bytes. Public commands and public read/replay results now require
finite binary64 values with magnitude at most 2^53-1. The browser enforces the
same wire policy. Trusted internal CAS integers are not silently rewritten.
This is a serialization boundary, not an equipment or engineering limit.

The project brief preserves unknown information as null and does not derive
country/timezone from interface language. Review reproduced acceptance of
host TZif special files, including a host that actually listed `localtime`.
New intake now explicitly excludes localtime/posixrules and the posix/right
trees before consulting the installed IANA set. Historical parsing retains
its archived TZif bytes and does not require a current host name.

A second review reproduced a receipt regression when the installed name set
changed after a successful save. The stable DTO now validates syntax/shape;
only a genuinely new create/revise checks the current IANA set. Workspace
checks ownership and the permanent receipt first, then validates and writes
new bytes within the transaction. Original create/revise and permanent replay
return their original revision even after a newer revision or host update.

Moving intake publication into the transaction exposed an outdated concurrency
test barrier. Its first full run was 292 passed / 1 failed. The test paused a
writer while synchronously awaiting another writer, creating its own lock
timeout. The corrected fixtures independently cover claim-first and
create-first orders without relaxing timeouts or moving publication back out
of the transaction. An intermediate test run also caught a missing test import;
it was corrected before the fixed final reviews.

## Independent outcomes and practical limits

- Standards: PASS at ca4918ef; no remaining hard violation or independent
  blocking smell. Independent fixed archive: 294 passed in 16.84 seconds.
- Spec: PASS at ca4918ef; no missing/wrong/extra behavior in this component.
  Independent fixed archive: 294 passed in 18.73 seconds.
- Implementer: 294 planning tests passed in 15.70 seconds; targeted private
  HTTP/brief/profile tests and strict mypy passed. Native integration evidence
  also exercises real WordPress/Woo cookies, nonce/origin, parser ordering,
  quota and permanent receipt behavior in the explicitly owned p548 snapshot.

The reviewers used fixed source archives, real SQLite/CAS, ASGI, PHP and
controlled concurrency probes. They did not modify p548, the app work in
progress or production. Browser/EN-DE/mobile, complete asset intake, map/3D,
engineering calculations, site consumers and release/readback remain separate
required paths inside this same delivery goal.
