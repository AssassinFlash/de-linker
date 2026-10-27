# Initial independent Spec review

Reviewer: `/root/pv_reference_spec_cbadc619`.
Diff: `79632d0e9eaa04423aec7c736d93dbe5d1351082...0deef6efb4132e448d388922ae8760674a62f117`.

One P2: prepared-profile preview still runs numerical PV generation inside HTTP.
`ProfilePreview.page` calls `frozen_profile`, whose PV-reference branch calls
`frozen_reference_profile` and `generate_pv`. Newly worker-published profiles
use this format, so `/profiles/preview` reruns all 8,760 solar/POA/temperature/
DC/converter steps before returning a page. This violates the specification's
requirement that numerical PV generation must not execute in HTTP.

Required repair: project the worker's immutable output through hash-verified
CAS reads, retain full reproduction in the worker, and add an actual HTTP test
that forbids `generate_pv` while checking original values and provenance.

No additional findings in inspected ownership/transfer, frozen source/history,
atomic publication and fencing, dependency retention, executor dispatch/cache
reconstruction, capability identity or energy-only compatibility. This was
read-only inspection, with no live-instance or external research actions.
