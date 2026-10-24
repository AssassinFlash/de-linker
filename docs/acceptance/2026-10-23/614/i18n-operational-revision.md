# Translation bookkeeping and publication revisions

This narrow correction is based on the actual `publication614` reference
withdrawal/republication acceptance, after the integration source `97308f43`.
It changes only the product revision projection. WordPress translation state,
source content, original documents and the retained UI recovery state are kept.

## Observed failure and exact diagnosis

The current and as-built manifests each contained 86 products and 144
documents. Every document field matched, including both reference PDFs' original
SHA values. Only reference product 8369 changed its `product_revision`.
Seventy products had gained knowledge readiness during preparation; readiness is
attached after source hashing and did not cause this source change.

Read-only native ROW/FULL binlog inspection isolated the actual status roundtrip:
two post updates changed only status and modification times. The only metadata
update for this reference changed `_linker_i18n_note` from
`DeepSeek unreachable` to `queued`. The translation queue writes that diagnostic
on a normal published-source save. `Publication::product_record()` previously
included it in `_facts.meta`.

Native PHP Reflection reconstructed the current product revision exactly:

```text
03727a356806128f9b0e254d4904b623f73c773832637f01fb2aad9148c4a480
```

Changing only that note back in the in-memory record, with no metadata write,
reproduced the original product and complete source revisions exactly:

```text
product: 98f2ed95d61870b6881708e65b788cc823e7d56ce8b396bcf8d354a937d29de2
source:  04a8e966a46143279a81c6db3b30bbc1df45252a4f83aa8d1cc61c4339c41268
```

Removing both keys could not reproduce that historical raw hash because the
original record already contained translation state. This correction defines a
new stable projection; automatic preparation must bind its resulting revisions.
No historical metadata is deleted to force a previous version.

## Corrected boundary and regression

The existing metadata exclusion now also names `_linker_i18n_status` and
`_linker_i18n_note`. All other product metadata, content and evidence bindings
retain their existing version behavior.

`RevisionTest` calls the actual manifest and dependency validation seams. The
retry diagnostic and translation state lifecycle keep source/product revisions
stable and preserve stored operational metadata. Real product content changes,
same-URL replacement PDF bytes and removal of a Woo document association still
change the source and reject old dependencies. The document cases use actual
temporary files, removed after each test.

Before the correction, the five-case regression ran with two failures at the
unchanged-source assertions. After the correction it passed five tests and
29 assertions. The complete Commerce unit suite passed 1,299 tests and
6,664 assertions; complete PHPStan and changed-file WPCS passed. This source
increment does not exercise the shared WordPress
instance; the coordinating integration task owns the native status roundtrip
and actual worker rebuild/readback. The original 8369 recovery state is retained.
