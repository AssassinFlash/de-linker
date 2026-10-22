# Shared archives — Standards integration review after current-main rebase

**PASS for the rebased source candidate.** No new actionable integration blocker was established. This is a new ruling against base `c022f81a48010c9ee66967245d81468495b1b21f` and head `7ce513e162f7b1474788b986d41873b3970f8ca8`; the earlier `d27f3dc` ruling alone is not used as current-main approval.

The full candidate remains 22 product/test/catalog files. The independently recomputed compact sorted-key JSON SHA-256 of the complete file/hash map is `d671e3b91033193ec848ad0d099c91268bc949b726d3138afc1f66f6bcf32dbc`, matching `source-rebased-22-files.json`. All 22 current file hashes match that manifest. All **19 non-catalog files** match the exact hashes in the prior complete source review; there are zero non-catalog mismatches. Only PO/POT/MO differ from the earlier source freeze. The aggregate method here is the new manifest's compact JSON method, not the earlier report's sorted-line method.

## Integration checks

- Compared the complete `c022f81a...7ce513e1` plugin diff: exactly the intended 22 taxonomy/LC/empty-state/catalog files changed. The early `pll_filtered_taxonomies` whitelist, native Woo main-query type inference, constrained empty-root hide policy, rewrite declaration fingerprint, native LC assignment preflight, exact backup/readback, Throwable restoration, empty data fragment, three exports and scoped WindPress styles are unchanged reviewed bytes. There is no conflict resolution that silently substituted an older implementation.
- Compared current bytes and Git diff of the public-protection implementation, its built entry/asset, Commerce module registration, account presentation bridge and i18n translation client against `c022f81a`: this candidate does not change them. The new protection module remains registered from current main. It is not removed or replaced by the taxonomy integration.
- Inspected the actual integration seams rather than assuming disjoint names: protection frontend `connectForms()` binds only markers carrying `data-linker-protected-action` inside their native forms. The shop's GET search/sort and the added empty-state action do not acquire such a marker. Protection's native Woo gate explicitly returns for requests without recognized mutation commands. The empty-state All-products action is a native shop-page link, not an admission/write transport. No protection form mutation, proof token, body policy, quota or mail path is inserted into these public read surfaces.
- Protection registration has no competing Polylang filtered-taxonomy declaration, LC template matcher, archive query/hide policy or assignment writer at these seams. The metadata publish/rollback code continues to restrict its saved template IDs and generic assignment keys; it does not capture, restore or consume public-protection ledger/configuration options. Its existing outer presentation settings backup is not broadened by this integration.
- The shop still uses installed native LC `lc_label` in the Commerce domain and the native Woo page URL tag. Current-main protection changes did not alter the fixed label processing, localized empty message, existing EN/DE archive pair or structural shop fallback. Neither a PHP page layout nor a custom translation/URL renderer was introduced.

This is an integration review of the taxonomy candidate's contact with current main. It is not a fresh security audit or runtime approval of the complete public-protection subsystem already present in the base.

## Independent language readback

Parsed PO entries with context/plural keys and compared them with the exact current-main base rather than the older catalog. Results:

| Check | Base → head |
|---|---|
| PO message keys | 1061 → 1062 |
| PO additions | Only `No products are listed here.` |
| Existing PO translations changed / removed | 0 / 0 |
| Duplicate PO / POT keys | 0 / 0 |
| Current PO keys missing from POT | 0 |
| MO entries excluding header | 1013 → 1014 |
| Existing MO values changed / removed | 0 / 0 |
| MO addition | `No products are listed here.` → `Hier sind keine Produkte aufgeführt.` |

Thus the protection rollout's 1013 compiled translations are preserved, with the one approved neutral empty-state sentence added. Static reference movement is not a translation deletion. The existing “All products” / “Alle Produkte” and “Product filters” / “Produktfilter” labels retain their native catalog source.

Exact rebased catalog SHA-256 values:

- PO: `234678b492ca99ee2362fe1af2e8c543d5f8975cd785308938c41ba24fea410a`
- POT: `9bddddb38f3ecb9c23f31e250a1cc673761ea4ea651c86ef3626e0dede132fc4`
- MO: `3b122b3d04d654ca95137f99c55555eab549d267da871de8c88bcefc85f968f9`

## Evidence limits

No source, instance, dependency or build operation was performed by this reviewer. This pass independently read Git state/diffs, verified the complete hash map, inspected the public protection seams and parsed the catalog artifacts. The complete parent-owned check/commerce run was in progress when this ruling was made; no unobserved result is claimed here. The prior native LC fault/rollback, cache lifecycle and browser evidence retain their own explicit source/compiled-version attribution. Rebased local/native/browser and production readback are separate gates.

The candidate still does not implement SAJ family pagination or contact continuity. This source integration PASS must not be used to close those investigations or the full-site visual goal. The prior complete source report remains useful for the unchanged 19 file-level findings, while this document supplies the current-base integration and catalog ruling.
