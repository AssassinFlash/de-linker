# Preserve the REST user guard after initialization

Owner-authorized narrow repair, 2026-10-23. Base is the reviewed reminder hotfix `b29a979a16c39651fdbfb265413621f9d96f599f`; preserve that change and all existing REST behavior except the demonstrated missing anonymous user-list refusal.

## Evidence and native seam

Read-only production inspection found anonymous collection requests returning200, including a request with only the id field, an explicit small cachebuster and no-cache request header. The live MU file exactly matched source. With native current user0 and list_users=false, its direct guard returned rest_forbidden but native rest_do_request returned200. Tracing the actual callbacks showed ACF6.3.1 initialize at priority10 replacing the guard's earlier WP_Error with null. Later Linker callbacks retained the received null. This is an execution-order defect, not evidence that source was absent or that the default request helper added a cachebuster.

Register the existing MU rest_pre_dispatch guard at20, after ACF's observed initialization10. Keep its native list_users decision, case-insensitive users collection/item scope, error and response headers. Do not modify ACF, add dependencies, disable REST, change customer UI or alter other business/resource/mail rules. Priority20 is chosen from that observed hook ordering, not an unexplained rate threshold.

## Acceptance

- Native regression installs a same-priority initialization-only callback returning null, matching the demonstrated ACF contract. It must actually run.
- Anonymous collection and mixed-case item requests return403/rest_forbidden. A native administrator with list_users remains200; an unrelated public REST read remains200.
- Separately execute the actual byte-equal ACF initializer class on the owned native instance, with the minimal disabled-setting branch, and the repaired MU source installed only for that bounded run. Record the partial-plugin nature of this reproduction; do not pretend it is a full ACF activation.
- Keep raw traces private and record only status, capabilities and hashes, never returned account values. No real credentials, customer writes, mail or model calls.
- Independent Spec/Standards review, exact-head CI, production backup/deployment and fresh unauthenticated HTTP403 readback are required before release is closed.

The pending inventory-credential MU module has the same observed ordering risk. Its candidate is not included in this production hotfix. The coordinator owns its separate repair and actual credential/batch fixtures before combined release.
