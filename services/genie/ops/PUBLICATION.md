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

Old indexes without proof tables cannot authorize knowledge hits. Every search resolves the current symlink, opens the immutable new release and retires the old connection under the shared search lock. Authenticated `POST /knowledge/loaded` returns the process's actual `index_version`, `source_revision`, available product revisions, `preparation_complete` and `unprepared_documents`. Reading a disk manifest alone is insufficient.

New turns omit historical assistant messages from model input. Customer messages remain project inputs; old uploaded-file readings are re-identified against Woo before reuse. A supplied withdrawn model, including in a photo, permits identification and the owned bilingual team handoff sentence only. Personal saved solutions are explicitly historical snapshots and grant no current product-card IDs. The PHP proxy revalidates before committing; stored current-turn receipts carry server-only dependencies, and receipts without those proofs cannot bypass the service on replay. Historical transcript text remains available.

Historical active document links require a stored `document_id` and the same current `document_revision`; old links without identity or links to a replaced same-URL file are disabled. The current original-file gate independently enforces download permission. These technical document rules do not touch the account's owner-gated historical report files.

## Mac worker installation

Use a stable checked-out source path with the locked Genie index dependencies installed. Do not install a launchd job pointing at a temporary review worktree. Keep one configured worker for this site. Heavy Docling/OCR/embedding preparation stays on the Mac; the worker refuses to run elsewhere.

1. Provision a mode-0600 environment file outside the repository with `LINKER_PUBLICATION_JOBS_URL` (ending `/wp-json/linker/v1/publication/jobs`), `LINKER_PUBLICATION_USER`, `LINKER_PUBLICATION_PASSWORD` (existing WP Application Password user with `manage_woocommerce`), and `GENIE_SERVICE_TOKEN`. Keep existing embedding credentials and model routing. `--rest-config` uses the existing private REST JSON; its site origin must equal the queue origin. No credential goes in a plist or issue.
2. Choose the polling interval for the build machine's availability and a lease longer than its measured complete-build budget. Render the plist first with `python ops/install_publication_worker.py --env-file <private-path> --interval-seconds <interval> --lease-seconds <measured-budget> --worker-id <stable-id> --loaded-url <service-loopback>/knowledge/loaded --host <configured-ssh-alias>`. Add `--install` only in the deployment session, then read back `launchctl print` and the actual process/path. Replacing an existing worker requires reading its active definition first; this implementation session does not install it.
3. With `--host`, the worker uses the same SSH alias for a single remote loopback request to `/knowledge/loaded`; it owns no persistent tunnel and needs no manually maintained forward. The service token is supplied on SSH stdin and is absent from process arguments, scripts on disk and logs. Without `--host`, a local rehearsal calls the local loopback directly. The request keeps the existing service gate; no port is exposed or authentication disabled. The existing publish CLI uploads and atomically switches the index; the worker then reads the **serving process** and acknowledges only matching loaded source/index versions and prepared product revisions.
4. Rehearse offline, build failure, expired leases, edit-during-build, partial readiness, old loaded process and restart. Woo retains pending work; `claim` automatically reconciles current source. Old jobs cannot authorize later states. A materialized generation preserves semantic warnings and the actual proven subset without rebuilding identical inputs forever. Failed parsing remains pending and is genuinely retried; the polling interval bounds retry frequency. Runtime withdrawal does not wait for this schedule.
5. After actual loaded verification and accepted Woo acknowledgement, the worker prunes only its ledger-owned local successful build directories to current and previous; existing evaluation/bake-off evidence is preserved, while the established host release tool retains its bounded current/rollback set. The build reports its just-created directory before writing index data. An explicit pending journal and directory ownership marker identify that one generation; build/publish/loaded/ack failure removes only that pending generation, and the next locked invocation recovers an interrupted worker. Untracked shared builds are never inferred from timestamps or deleted. It reuses content-addressed PDF, parse and embedding caches. Do not make a fresh full site copy for each job. At acceptance/merge remove this task's rebuildable dependencies and retire its managed worktree following `docs/agents/local-storage.md`.

## Acceptance boundaries

The implementation tests use actual FTS5/sqlite-vec SQLite files and HTTP transports without paid model or email calls. Source-layer tests establish fail-closed permissions and loading behavior; they do not establish production deployment, a completed full knowledge rebuild, live model-answer quality, or launchd installation. Review-station acceptance must include one Woo edit flowing through claim/build/publish/loaded/ack, fresh EN/DE customer turns, 390/1440 artifact states, and stage-one production controls before promotion.

Keep the 49 emergency EcoFlow paths until the replacement file gate proves anonymous original URLs, aliases, HEAD/GET/Range and caches are equally protected. Preserve the reversible current code/index generation; rolling back an index never rolls back current Woo permission.


## Preparation identity and actual serving rules

`recipe_revision()` hashes all index modules, runtime source, publication operations, project definition and locked dependencies automatically. A code-only fix queues current Woo inputs again. Parse cache reuse additionally requires a successful complete artifact set and the current parser recipe. The chunk tokenizer is pinned by immutable upstream commit and measured content digest.

The SQLite `serving_revision` is an expected runtime identity. `RUNTIME_SERVING_REVISION` is measured from the actual immutable service release at process startup. The loaded endpoint returns both independently. The worker refuses a new generation unless source, recipe, expected/actual runtime identity, generation, epoch and exact current proven product revisions match. A ready queue is checked on each ordinary poll and automatically requeued if its actual loaded receipt drifts; failures do not turn the supplied receipt into publication permission.

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
