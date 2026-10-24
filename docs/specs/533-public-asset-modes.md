# Keep private staging modes out of public browser resources

The browser investigation after the protection restoration found actual
uncached 404/text-html responses for header, consent and protection scripts and
fonts. The installed bytes matched the accepted source, but the two published
plugin directories were 0700 and their JS/font files 0600. Their retained
previous versions used 0755/0644. The HTML, native backend and hash-only checks
did not establish that those browser resources loaded or executed.

The immediate production correction belongs to the authorized page chat. It
preserves a complete metadata/hash preimage and restores only public static
resources and their necessary directory traversal. Private configuration,
ledgers, backend PHP and vendor permissions remain separate. No CSS repair
should conceal a failed script request.

## Publication contract

At the atomic publication boundary, after uploading all artifacts, normalize
only the incoming versioned plugin/theme roots and their assets/build browser
resources. Public directories use 0755; JS/CSS, fonts, images and Wasm use
0644. Individually owned theme browser files use the same file policy.

The local source and cached staging stay private. PHP loaders, arbitrary JSON,
vendor, MU PHP, neighbours, unowned parent directories, private backups and
configuration retain their modes. This is not a generic transfer or recursive
WordPress permission reset. New resource types require an explicit browser
contract; the change does not label every JSON or executable as public.

Build a digest of the prepared public path/mode inventory on the target. In
the final same SSH, before the rename/recovery trap, repeat a read-only check
of that inventory and its permissions. Reject unreadable enumeration, links,
missing/additional public paths or changed modes before any live rename.
Do not silently repair an intervening change at this last boundary.

If this final check explicitly refuses the candidate in that SSH, first verify
the whole unswitched preparation's identities: unchanged live paths, this
attempt's single-file backup copies and absence markers, and its original
empty private batch directory. Then remove only those preparation copies,
markers and empty directory. Do not run rename recovery before a rename or
clean up blindly after an uncertain transport result. A mixed plugin/MU/theme
batch must be able to retry without manual edits; replaced preparations are
retained for inspection instead of being deleted.

This digest covers public paths and modes, not code-byte authenticity. The
existing whole-source/release fingerprint checks remain independently needed.
Normalizing a .next candidate is not a claim that every server ACL or browser
interaction is correct: real static GET/MIME and browser loading/execution
remain acceptance requirements.

## Evidence and limits

Regression fixtures use real restrictive staging, rsync, a cached stage,
atomic rename/archive/rollback, private sibling files, and last-callback
permission/path/link damage, and a mixed existing/absent batch's refusal,
retry, archive and rollback. The initial seven controls fail against the old
publisher. Checks must preserve source/stage modes and private backup modes.

The configured Cutover test suite and its static checks must pass; final
source receives whole-diff Spec and Standards reviews and exact-head CI.
The immediate host repair is separately verified in fresh EN/DE desktop and
mobile browser sessions with actual responses, correct MIME, header controls
and asset execution. A green backend or visible HTML form alone is not an
interactive customer acceptance result.

No application PHP, model routes, quotas, inquiry data, marketing templates,
Solution Configurator or RoofTop mechanisms change in this tool repair.

Private evidence remains under
`/Users/chesterjohn/de-linker-data/incident-20261022/security-restore-after-publication-20261024/`,
including the preserved correction and `public-asset-modes/` test records.
