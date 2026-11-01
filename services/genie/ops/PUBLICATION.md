# Woo publication preparation and runtime checks

Implementation responsibility: [Genie and knowledge publication](https://github.com/AssassinFlash/de-linker/issues/615). Business rules: `docs/specs/609-product-publication.md`.

The model channels, customer ownership rules and private historical PDF downloads do not change. The existing EcoFlow draft states and emergency file rules stay in place. This code must be rehearsed with the Woo foundation and engine/receipt work before deployment.

## Runtime

`GENIE_WP_URL` supplies the sole publication authority. Every turn reads the no-store Woo manifest and validates the complete input dependency set again before release. Product tools validate all returned candidates, not only displayed cards. A missing authority closes the affected turn. Product vocabulary and page/draft caches are also invalidated by the current source revision; hooks are an optimization rather than permission.

Knowledge search intersects current Woo product/document revisions with the actual loaded SQLite proof tables. Empty filters authorize no passages. Fallback and same-page/short-datasheet expansion use the same permitted rows. Content SHA reuses parsing, not authorization; document IDs, content revisions and per-product associations remain separate.

A passage explicitly covering current models A and B can be authorized by two
separate current document identities, one actually associated with A and one
with B. Its scope binds each `document_id`, `document_revision`, `blob_sha256`,
`product_id` and `product_revision` as one required group. Every recorded link
must still match the loaded and current source, and the group must cover every
model in the whole passage. Asking about A does not skip B's dependency. Losing
either link rejects the whole passage; another public URL with identical bytes
cannot replace it. Store availability and runtime retrieval use the same
`authorize_chunk` rule. The existing complete-source checks run again after
retrieval and before the current answer is released.

For split technical tables, the chunker records the native Docling TableItem,
its physical page/origin and the preceding continuous text-chunk identities.
Only an original Technical Data column declaration can supply the ordered
model set to the immediately following TableItem. Every fragment must retain
all original columns; the proof stores the original labels, column order and
header source IDs. A new table or section ends propagation, and an unresolved
model on the column axis closes the group. Runtime returns
the proven column heading with each fragment, so alphabetic document metadata
cannot reorder its values. Missing or inconsistent column proof is refused by
both availability calculation and retrieval. Generic headings grant nothing.
An original model axis inside that TableItem must also match the complete
preceding column order; a partial, different or reversed local axis refuses
the entire TableItem, even when its model set and column count are equal.

One narrow exception concerns an original component property row, not a model
axis. The source field `Pack Type / model` is isolated as its own complete row;
an unknown or withdrawn pack row remains denied. Other native rows may use the
original full current-system column axis only with their source TableItem,
original row indices, literal text digest and the excluded role-row anchor in
the proof. Every column stays in source order. Missing provenance, another
unknown model row, a changed/local model axis or a partial column set still
rejects the group. A legacy chunk containing the unknown row cannot use this
exception. No source text or PDF is removed or edited.

A manual's original declaration of the systems it covers can also prove a
specific host compatibility sentence. A literal `meter <manufacturer>'s
<model>` phrase supplies an external-device role; a bare code, product category
or generated header cannot. The host subjects retain their own current manual
associations. The externally named meter is recorded only as a
`referenced_product`, with its current Woo revision and the literal role quote
and source chunk ID. It gains no association to the host manual and cannot
retrieve it when used as the requested product. Its withdrawal or revision
change rejects the whole sentence. This applies only to the isolated original
non-parameter prose, with the explicit manufacturer scope declaration and no
local model override or unknown device. It does not release external-device
specifications, another product's parameters or any table. These distinctions
implement 609's requirement to retain valid current-A content in an original
manual that also names unavailable B; neither B nor a referenced device borrows
A's technical-fact permission. The existing full-source pre/output validation
also includes every referenced Woo product.

The build records the scope proof for each passage. A model is identified by Woo and authored model context; an ingress rating, frequency, standard or report number is not a product simply because it contains letters and digits. A single current model in an unambiguous authored section or document can supply its scope. Truly model-free warranty/certificate terms require the explicit Woo document purpose. Mixed files need a manufacturer-authored public-terms declaration and positive current-model evidence before model-free non-parameter prose can inherit a common scope. Mixed withdrawn/unknown-model tables and unnamed technical values remain denied. The generated context header grants no permission. `chunk_scopes` records the basis, source chunk IDs and authorizing document IDs; `manifest.json.permission_coverage` reports proven versus total chunks.

Manifest inventory normalizes only derived metadata. The known Woo language
labels EN/DE/MUL/MULTI/EN/DE/DE/EN/empty become `en`, `de`, `mul` or `und`;
the existing ES label remains `es`. Multilingual or unstated documents use the
existing per-passage language detector. Document role takes precedence over
type, using the same explicit EN/DE vocabulary as `Materials::document_kind`:
for example Handbuch/user_manual becomes manual, Datenblatt becomes datasheet,
and Kompatibilität/compatibility_list becomes compatibility. Warranty purpose
remains available to the scope proof even though the index's five-type metadata
stores it as other. `publication_manifest` retains the original tags, roles and
types byte for byte. Unknown metadata fails preparation visibly; it is never
guessed to be a language or a particular document purpose.

Knowledge availability and complete preparation are separate. A current product is available when it has at least one proven passage that the current retrieval guard can actually release. A missing or ambiguous supplementary document does not suppress an already verified manual. The process reports `preparation_complete=false` and `unprepared_documents` entries `{document_id, product_id, reason}` until each current association is parsed and proven. Reasons are `document_unparsed` or `no_proven_passage`; no original text enters the diagnostic. Worker acknowledgement sends both fields and preserves the available product subset while Woo keeps incomplete work pending. Having all products available does not imply all documents are complete. Engineering reference products are excluded from Genie products, documents and actions.

A conditional first-contact warranty procedure can make a product available, but does not by itself prepare the policy's duration and conditions. Until an eligible terms passage is proven, that policy association remains `no_proven_passage` under the existing Woo acknowledgement vocabulary.

Old indexes without proof tables cannot authorize knowledge hits. Every search resolves the current symlink, opens the immutable new release and retires the old connection under the shared search lock. Authenticated `POST /knowledge/loaded` returns the process's actual `index_version`, `source_revision`, available product revisions, `preparation_complete` and `unprepared_documents`. Reading a disk manifest alone is insufficient.

New turns omit historical assistant messages from model input. Customer messages remain project inputs; old uploaded-file readings are re-identified against Woo before reuse. A supplied withdrawn model, including in a photo, permits identification and the owned bilingual team handoff sentence only. Personal saved solutions are explicitly historical snapshots and grant no current product-card IDs. The PHP proxy revalidates before committing; stored current-turn receipts carry server-only dependencies, and receipts without those proofs cannot bypass the service on replay. Historical transcript text remains available.

Historical active document links require a stored `document_id` and the same current `document_revision`; old links without identity or links to a replaced same-URL file are disabled. The current original-file gate independently enforces download permission. These technical document rules do not touch the account's owner-gated historical report files.

## Mac worker installation

Use a stable checked-out source path with the locked Genie index dependencies installed. Do not install a launchd job pointing at a temporary review worktree. Keep one configured worker for this site. Heavy Docling/OCR/embedding preparation stays on the Mac; the worker refuses to run elsewhere.

1. Provision a mode-0600 environment file outside the repository with `LINKER_PUBLICATION_JOBS_URL` (ending `/wp-json/linker/v1/publication/jobs`), `LINKER_PUBLICATION_USER`, `LINKER_PUBLICATION_PASSWORD` (existing WP Application Password user with `manage_woocommerce`), and `GENIE_SERVICE_TOKEN`. Keep existing embedding credentials and model routing. `--rest-config` uses the existing private REST JSON; its site origin must equal the queue origin. No credential goes in a plist or issue.
2. Choose the polling interval for the build machine's availability and a lease longer than its measured complete-build budget. Render the plist first with `python ops/install_publication_worker.py --env-file <private-path> --interval-seconds <interval> --lease-seconds <measured-budget> --worker-id <stable-id> --loaded-url <service-loopback>/knowledge/loaded --host <configured-ssh-alias>`. Add `--install` only in the deployment session, then read back `launchctl print` and the actual process/path. Replacing an existing worker requires reading its active definition first; this implementation session does not install it.
3. With `--host`, the worker uses the same SSH alias for a single remote loopback request to `/knowledge/loaded`; it owns no persistent tunnel and needs no manually maintained forward. The service token is supplied on SSH stdin and is absent from process arguments, scripts on disk and logs. Without `--host`, a local rehearsal calls the local loopback directly. The request keeps the existing service gate; no port is exposed or authentication disabled. The existing publish CLI uploads and atomically switches the index; the worker then reads the **serving process** and acknowledges only matching loaded source/index versions and prepared product revisions.
4. Rehearse offline, build failure, expired leases, edit-during-build, partial readiness, old loaded process and restart. Woo retains pending work; `claim` automatically reconciles current source. Old jobs cannot authorize later states. A materialized generation preserves semantic warnings and the actual proven subset without rebuilding identical inputs forever. Failed parsing remains pending and is genuinely retried; the polling interval bounds retry frequency. Runtime withdrawal does not wait for this schedule.
5. After actual loaded verification and accepted Woo acknowledgement, the worker prunes only its ledger-owned local successful build directories to current and previous; existing evaluation/bake-off evidence is preserved, while the established host release tool retains its bounded current/rollback set. The build reports its just-created directory before writing index data. An explicit pending journal and directory ownership marker identify that one generation; failures normally remove that pending generation, and the next locked invocation recovers an interrupted worker. A verified pre-activation review refusal is the bounded exception described below. Untracked shared builds are never inferred from timestamps or deleted. It reuses content-addressed PDF, parse and embedding caches. Do not make a fresh full site copy for each job. At acceptance/merge remove this task's rebuildable dependencies and retire its managed worktree following `docs/agents/local-storage.md`.

## Acceptance boundaries

The implementation tests use actual FTS5/sqlite-vec SQLite files and HTTP transports without paid model or email calls. Source-layer tests establish fail-closed permissions and loading behavior; they do not establish production deployment, a completed full knowledge rebuild, live model-answer quality, or launchd installation. Review-station acceptance must include one Woo edit flowing through claim/build/publish/loaded/ack, fresh EN/DE customer turns, 390/1440 artifact states, and stage-one production controls before promotion.

Keep the 49 emergency EcoFlow paths until the replacement file gate proves anonymous original URLs, aliases, HEAD/GET/Range and caches are equally protected. Preserve the reversible current code/index generation; rolling back an index never rolls back current Woo permission.


## Preparation identity and actual serving rules

`recipe_revision()` hashes all index modules, runtime source, publication operations, project definition and locked dependencies automatically. A code-only fix queues current Woo inputs again. Parse cache reuse additionally requires a successful complete artifact set and the current parser recipe. The chunk tokenizer is pinned by immutable upstream commit and measured content digest.

The SQLite `serving_revision` is an expected runtime identity. `RUNTIME_SERVING_REVISION` is measured from the actual immutable service release at process startup. The loaded endpoint returns both independently. Managed generation searches and passage permissions refuse a mismatched or missing expected identity; loaded diagnostics stay available so activation can repair the mismatch. The worker refuses a new generation unless source, recipe, expected/actual runtime identity, generation, epoch and exact current proven product revisions match. A ready queue is checked on each ordinary poll and automatically requeued if its actual loaded receipt drifts; failures do not turn the supplied receipt into publication permission.

## Fenced activation

Knowledge `activation_epoch` increases under the native job lock on every new lease, including retries. It survives source/recipe changes and deliberate rollback. The existing authenticated claim route's `operation=verify` checks the exact live context without changing the lease. No new route or purpose-credential scope is required.

The remote release helper holds a per-root flock, verifies the candidate's actual SQLite SHA and metadata, checks the fresh native lease and actual process runtime identity, then writes/fsyncs the accepted epoch/target journal before the atomic current switch. Lower epochs cannot replace a newer accepted generation. An equal epoch permits only the identical generation/SHA/job/source/recipe. Staging collisions refuse rather than delete another upload. Native credentials and the service token travel only through structured SSH stdin and live in memory; no credential is written into a release or journal, and authenticated requests do not follow redirects.

The two hosts do not share a distributed transaction: a new claim can occur after the fresh check and before the filesystem switch. The higher epoch wins when it activates, and current Woo checks continue to reject revoked content throughout. A stale acknowledgement never rewinds another worker's current generation.

## Deliberate rollback

Stop the owned managed worker through its normal release process after checking its actual executable and launch definition. Verify the installed target recipe using that immutable target release's `index.preparation.recipe_revision()`. Read the current native recipe and use internal WP-CLI only:

```php
(new \Linker\Commerce\Products\Publication\PreparationJobs())
    ->reactivate_recipe($expected_current_recipe, $verified_retired_target_recipe);
```

The target must already be a known retired hash and the expected current hash must still match. This CAS does not change products, original files, current Woo source or engineering. Resume the verified prior worker/runtime and allow it to materialize current Woo inputs with a higher epoch. An adopted managed index cannot use the old unfenced `rollback` symlink command. Read back the actual serving source/recipe/runtime/generation/epoch, native acknowledgement, current withdrawal controls and original-file digests before declaring recovery.

## Paired serving-rule release

`ops/paired_release.py` is the committed operator for an already prepared Genie
runtime and the final immutable Mac worker source. It changes only Genie API and
judge units. It does not stage sources, install dependencies, publish WordPress,
change launchd, or touch Engine. The ordinary scheduled worker keeps its existing
path. The previous one-use migration runner has been retired; do not recreate it.

Before this window, complete final review/CI, prepare one unselected VPS runtime
under `/opt/linker-genie/<version>` with its locked `.venv`, and prepare the same
final source on the Mac. Measure identities after all ops changes: ops Python
participates in the recipe, while runtime source also participates in serving.
The candidate source and current/previous source must remain immutable during the
window. Keep the original runtime/index pair and existing recovery points. Read
the installed launch definition/executable and pause its idle schedule under the
existing worker lock before executing this operator. No concurrent publication
owner may switch the runtime/index during the window. The API and judge unit
ExecStart must use `/opt/linker-genie/current/.venv/bin/`; actual post-start PIDs
must have the selected release as cwd. Resolve a different unit layout before
publishing, rather than weakening this check.

Use the existing shared interpreter, with `PYTHONPATH` pointing to the immutable
candidate `src`, service root and `ops`. Never copy or create another environment.
The existing private worker environment is read through the same loader used by
launchd, preserving provider proxy routing and exact-site bypass. Credentials
remain in the existing mode-0600 file/environment and structured SSH stdin. The
publication credential is used only for native jobs POSTs; the service token is
used only for private loaded readback. The existing inventory REST configuration
must identify the same Woo origin as the queue.

The release owner must record a single private journal path outside the source,
inside an existing mode-0700 directory, for example
`/Users/chesterjohn/de-linker-ops/knowledge-worker/paired-release.json`. It contains
the exact temporary lease capability and source manifest, never account keys.
Keep at most this one journal and its atomic `.next` sibling. Successful actual
ready ACK plus candidate-selector verification removes the journal. On failure,
keep it only until inspected recovery or native lease retirement is verified,
then remove it. Do not print, commit, or attach it to an issue.

From the final immutable Mac service root, use this same argument set for each
command (replace candidate and previous with the freshly verified exact names):

```sh
PYTHONPATH="$PWD/src:$PWD:$PWD/ops" \
/Users/chesterjohn/de-linker-ops/knowledge-worker/releases/1418dc26e14c/.venv/bin/python \
ops/paired_release.py preflight \
  --env-file /Users/chesterjohn/de-linker-ops/knowledge-worker/worker.env \
  --host linker-services --candidate <prepared-runtime-version> \
  --previous <verified-current-runtime-version> \
  --journal /Users/chesterjohn/de-linker-ops/knowledge-worker/paired-release.json \
  --worker-id publication-618-mac --lease-seconds 7200 \
  --loaded-url http://127.0.0.1:8902/knowledge/loaded
```

`preflight` reads the remote selector and hashes the actual prepared source; it
makes no lease, journal or service change. Execute `publish` with the same
arguments once. It requires the original selector and an unused journal path,
then runs native Worker/run_job. It builds a new generation with the real lease
and existing PDF/parse/vector caches. The operator is **cached-only**: a missing
vector fails visibly before any embedding API call. This intentionally requires
input/cache verification before the window; it never converts a metadata change
into an old generation's proof.

The existing publish helper checksum/delta/compress uploads and verifies actual
SQLite/manifest/owner bytes before the runtime hook. Only then does the operator
stop API/judge, CAS the selector, start both, and verify actual running PID/cwd.
Native fenced activation independently checks current lease and actual serving
identity. Worker then validates full loaded source/model/recipe/serving/index/
epoch/product coverage and sends the native ready ACK. The same native ACK response must contain both `accepted=true` and
`complete=true` for paired success; accepted-but-pending or a missing complete
field retains the journal and reports incomplete, without another POST/read.
The ordinary scheduled worker retains its accepted-ACK contract.
No-job and lock-busy exits are incomplete releases, not success. Semantic gaps remain visible.

Before any possible index activation, runtime-switch or startup failure restores
the old selector, starts both units even if the failed stop/start left them
inactive, verifies actual PIDs/cwd and compares the entire old loaded receipt.
If that readback succeeds after the explicitly supplied pre-activation guard refused while the original
lease is still live, the worker retains the one pending local build and journal
until that lease expires. It sends no failed ACK and ordinary polling does not
replace the candidate during the lease. On the first ordinary poll after expiry,
the owned pending build is removed before normal claiming resumes. The operator
may instead explicitly continue within that exact lease by invoking
`paired_release.main(arguments, guard=guard)` with `resume-candidate` and
the original release arguments. The same guarded entry point must be used for
the initial `publish`; other runtime failures retain their normal failure path.
The guard must be a callable receiving the local
build path, original loaded receipt and original epoch; it must rerun the actual
release's pre-activation checks and raise if they fail. There is deliberately no
unguarded CLI continuation. The command rechecks the original Woo lease, old
loaded pair, journal index identity and local SQLite checksum/metadata, then
uploads and reruns the guard before the native fenced activation. It cannot
rebind a build to a replacement lease or changed compiler. A hard process kill
before the deferred state is recorded still follows ordinary interrupted-build
cleanup and may require a rebuild.
After activation becomes possible, transport loss or later journal/loaded/ACK
failure preserves the candidate and original lease. No automatic runtime-only
rollback, activation replay, replacement claim or rebuild occurs.

For ambiguity, inspect the actual selector and native activation fence first.
`resume-ack` with the same arguments uses only the journal's exact lease,
`operation=verify` and native inspect of its exact index/SHA, then the existing
Worker ack-only full-loaded validation/ACK retry. It cannot make an ordinary
claim or a new generation. An expired/changed lease refuses. If ACK was accepted
but its response lost, the old capability is already retired: resume refuses.
Run `confirm-ready` with the same release arguments plus the already verified
privileged SSH alias and WordPress root:

```sh
# Same interpreter, PYTHONPATH, env-file and release arguments as above.
ops/paired_release.py confirm-ready <same-release-arguments> \
  --wp-host hostinger-de-linker \
  --wp-root /home/u388076051/domains/de-linker.com/public_html
```

This command makes only existing SSH/WP-CLI `eval-file -` reads. It projects the
native queue's acknowledged identity, coverage, retired-lease state and fresh
Woo source/model identity; no lease token or customer content is printed. It
compares the original journal's exact job/worker/source/model/recipe/serving/
index/epoch against the durable ready ACK and actual loaded receipt, verifies
the native index activation fence and exact SQLite SHA, and repeats the native
read to reject drift before removing the journal. It cannot claim, build,
activate or ACK anything. An absent/mismatched/pending receipt or live lease
refuses and retains the journal. Neither a 409 nor a supplied proof file counts
as success. Do not infer failed delivery or rebuild from a refusal. Deliberate rollback after activation follows the
retired-recipe CAS procedure above with a new higher native epoch.

After successful ACK, install the final immutable Mac source through the existing
launcher installer, restore the normal schedule and observe one actual natural
poll. Read actual runtime/source/index/recipe/serving/epoch and Woo ready receipt;
retain the semantic-gap state. Then retire the task stage/journal and superseded
source/runtime within current+previous and index KEEP3, protecting the shared
1418 interpreter and actual references. Publication is not complete until this
readback and resource cleanup are recorded by the release owner.
