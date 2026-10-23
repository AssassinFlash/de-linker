# Native profile intake in the unified project

2026-10-23. Implements the next W02 workflow within the same active workbench
delivery. This is a source-intake increment, not completion of path A or SKU
qualification. The mature-software basis is the [Apify primary-source
research](../research/2026-10-23-profile-intake/RESEARCH.md); generic column
mapping and real UTC/DST handling are this site's explicit integration design,
not features falsely attributed to the three documented competitors.

1. A currently owned project opens a UTF-8, unique-header CSV. File selection
   alone makes no project or source mutation. A replacement clears the former
   file before reading, including when replacement fails. The deployment
   `max_csv_bytes` bounds files; JSON/base64 is also subject to `max_body_bytes`.
2. `/profiles/inspect` is a private read, with the existing native nonce/scope
   and service gates. Ownership precedes base64 decoding. Its declared
   delimiter and page size produce raw column names and cells, original record
   starting file lines, full structural record count and sample truncation.
   The entire CSV structure is checked, including rows beyond the sample. It
   publishes no blob, asset, receipt, quota write or project revision. It
   declares `csv_structure_only`; it neither parses dates/values nor certifies
   time-series quality. Preview replies are bounded by the deployment JSON
   ceiling without silently truncating cell text. Legal cells are bounded by
   that source/reply contract, not Python csv's implicit default field cap.
3. The user explicitly maps distinct timestamp/value and optional end/fold
   columns, measurement point, interval-average kW or interval-energy kWh,
   decimal separator, origin, source timezone and fixed duration or explicit
   ends. Timezone prefill is the visible project value, never UI language.
   UTC offsets take precedence; fold semantics and clock-change issues retain
   the existing frozen time-series contract. Units are not guessed from values.
4. A source label and basis for permanent private storage are required user
   declarations. They do not verify meter accuracy or third-party permission.
   The original filename is not sent or put into metadata. Import saves the
   same original bytes, mapping, provenance and captured TZif as the existing
   `profiles/csv` service. No implicit zero fill, sorting or annual extrapolation.
5. Before dispatch, one immutable original body/UUID is saved to IndexedDB.
   Exact retry returns the original receipt; there is no automatic replay on
   refresh. Several pending imports require selection. Recovery records are
   scoped to confirmed native identity and project, with same-UUID/different-
   body refusal and exact-body conditional cleanup. Two tabs cannot overwrite
   one another. Database version 5 preserves version 3/4 drafts and creations.
   Local policy is 16 MiB per import body, 32 imports/32 MiB per scope; limits
   refuse visibly and never evict uncertain work. Storage failure does not
   disable an available server, but the open in-memory request remains frozen
   and the UI makes no across-refresh recovery promise.
6. Unknown acknowledgement keeps the exact request. Typed pre-publication
   400/413/415/422 input refusal returns it to correction immediately, even
   when browser cleanup fails. Its stale selector entry is removed and durable
   admission revoked before awaiting cleanup. Source-import
   recovery survives until selection is durably stored in the project draft;
   selection failure or cleanup failure retains recovery. Same-scope native
   verification preserves local input; different confirmed scope fences old
   awaited writes, RPC dispatch, selection and cache publication.
7. The confirmed source is read again through owned `assets/read` and
   `profiles/preview`. Full-period summary is independent of the displayed
   interval page. Original unit/time conventions, source declaration, UTC
   extent, energy, coverage, gaps, min/max interval means and native/effective
   resolution remain visible. Gap locations and rows are bounded, with a first
   page return. Raw metadata/source/transformations and both hashes are
   inspectable. Net import is signed imports minus exports; it is not total
   site load. Interpretation is not an annual forecast, a billing/instantaneous
   peak, battery sizing or fitness for a calculation.
8. Only the explicit use action puts the owned asset ID into versioned
   `profile_selections` for its actual measurement point. One source is selected
   per point. The server refuses cross-project/owner IDs, unknown roles and
   role relabelling on project revision; a newly created project cannot point
   at another project's assets. Selecting/replacing/removing is an ordinary
   undoable local command and uses the same project Save/revision/conflict
   mechanism. Removing a selection preserves its immutable source and history.
   The UI distinguishes stored source, open draft selection and server save.
   An owned receipt selected in the server-confirmed project baseline completes
   intake even when browser storage is unavailable; best-effort recovery cleanup
   cannot invalidate that save. An editable selection alone grants no such proof.
9. Unprotected file input, including its asynchronous byte-read stage, warns on reload and blocks project close until
   imported durably or explicitly cancelled. A persisted intent can be closed
   and reopened for explicit recovery. Authentication failures recheck native
   identity without an infinite retry loop; persistent failure needs a user
   retry. Owned queries consume cancellation signals and resume after confirmed
   same-scope verification. UI/error copy is EN/DE, independently reviewed,
   with site tokens and the native WindPress pipeline only.

Acceptance requires actual native HTTP and browser upload→mapping→safe refusal
and correction→quality→selection→Save→refresh, EN/DE × 1440/390, plus native
IndexedDB upgrade/concurrency/isolation and identity/lifecycle fixtures. This
increment does not claim cross-identity pending-upload reconciliation, project
package import/export, other unit adapters, scenario calculation or completed
path A; those remain in the same overall active implementation and cannot be
discarded at delivery.
