# Profile interpretation and import diagnostics

2026-10-23. Implements the W02 quality view required by the approved unified
workbench. This increment exposes authoritative interpretation to the native
gateway; the upload/mapping/selection UI and complete path A remain required
within the same active delivery.

1. `/profiles/preview` accepts schema version 1, current owned project and
   asset IDs, a zero-based interval offset and positive page size. The native
   cookie/nonce/scope, private service credential and project checks still
   apply. It does not accept content hashes as access grants. Reads add no
   project revision, asset, calculation or quota mutation.
2. Supported assets are the already implemented permanent CSV profile and
   PVGIS system-profile formats. Interpretation reads the original bytes,
   frozen metadata and captured TZif or provider interpretation. It does not
   recapture current host timezone rules or apply another PV loss chain.
   A mismatched purpose/format or unavailable version fails explicitly.
3. Response identity includes project, asset, original byte SHA-256 and
   metadata SHA-256. `evaluation_scope=profile_interpretation` describes data
   interpretation, not fitness for an engineering goal or hardware release.
   The source origin, effective/native maximum intervals, reconstruction flag
   and complete transformation documents remain visible.
4. Summary covers the entire interpreted profile independently of paging:
   real start/end UTC, interval count, covered and spanned seconds, exact gap
   count/duration, signed integrated energy and min/max interval-average kW.
   Missing intervals are not zero-filled, sorted away or inferred from row
   count. Maximum interval mean is not an instantaneous or billing-window peak.
   Net import stays signed net import and cannot become gross consumption.
5. Rows contain zero-based `interval_index`, explicit start/end UTC and mean
   kW. `next_offset` is null at the end. `first_gaps` is a bounded diagnostic
   sample with `gaps_truncated`; its cap does not change full gap totals.
   The HTTP page ceiling uses the existing declared deployment max_page_size.
   All public numbers satisfy the shared finite interoperable representation
   window; values are not rounded or clamped to force a response.
6. A malformed CSV returns the existing `invalid_input` code plus an optional
   `profile_issue` with stable issue, nullable line and nullable mapped role.
   `line` is the one-based physical line on which the affected CSV record
   starts, including files with blank lines and quoted multiline cells. It
   is not an Excel row number or zero-based profile interval index. Timestamp
   and end-timestamp roles are distinct. No raw cell text, column-name value,
   filename, exception trace or project identity is included in diagnostics.
7. Issues distinguish encoding/header/width/syntax/empty input, number format
   and finite range, time format/range, DST ambiguity/nonexistence/fold conflict,
   interval order/duration, sign and integrated-energy overflow. Invalid data
   fails before permanent source or TZif publication. An arithmetic overflow
   is a typed validation refusal rather than an unhandled server exception.
8. Upload acceptance, interpretable data and fitness for a selected goal are
   separate. A contiguous hour series does not prove quarter-hour peaks; a
   source declared measured is not an independently certified meter record.
   The browser must retain original units/mapping/source and present these
   quality facts before attaching the asset to an editable project scenario.

Acceptance uses real CSV records, frozen TZif, independent gap/energy arithmetic,
both captured 8784-hour PVGIS originals, real ASGI/SQLite and native WP/Woo HTTP.
The frontend still needs its file chooser, column preview/mapping, localized
diagnostic presentation, persisted unknown upload intent and explicit selection
of a confirmed owned asset. No renderer or screen is claimed by this contract.
