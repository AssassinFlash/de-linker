# Official-source weather acquisition

Owner clarification, 2026-10-24: Apify is exclusively for R&D research and
verification. The customer application must not depend on an R&D Apify account,
credential, Actor, Dataset or quota. The previous proposed runtime integration
was an implementation error; its historical record is retained under
`research/2026-10-24-runtime-provider-correction/SUPERSEDED-APIFY-DESIGN.md`.

Customer weather preparation uses the official JRC PVGIS HTTPS API through a
server-owned typed request, with no research credential and no arbitrary URL,
header, executable or crawler supplied by the browser. R&D-acquired originals
remain valid retained research/validation evidence; their acquisition channel
does not become a customer runtime dependency.

The request, selected databases and year range, terrain horizon policy, TMY
interpretation and resource limits are frozen in a saved project task. A
separate leased worker performs only bounded GET requests. Since the download
is idempotent, interrupted reads may retry under the original attempt/deadline
budget; there is no chargeable remote POST/job to reconcile or abort.

Only the exact official HTTPS origin and versioned TMY path are admitted.
Redirects, automatic request retries, netrc/cookie authentication and inherited
research credentials are excluded. Enforce connection/read/overall time, body
size, content type, response status, URL and complete data/metadata checks.
HTML refusal pages, error JSON, incomplete axes or changed provider echoes
fail visibly; they never become zero generation or a valid source.

Blocking DNS/TLS/headers/body reads run in a disposable HTTP child. Its parent
checks lease/cancellation while supervising the original wall-clock and
monotonic overall budget, then kills and reaps that owned child on loss or
expiry. A child-owned exit timer also bounds a transfer if its parent dies.
No workspace, application service token or research credential enters the
HTTP child. This avoids treating a socket inactivity timeout as an overall
deadline when a source continuously trickles bytes.

Retain original response bytes, exact request/response capture, interpretation
and source rights/attribution. Validate the complete TMY using the existing
trusted interpreter, preserve its two temporal axes, and record hashes in the
owned local journal. A retry reuses a completed validated capture. Source
publication remains fenced by the current task lease and commits atomically
with success. Selection and Save project are explicit later actions.

Test genuine local SQLite/CAS, a bounded official-origin adapter with realistic
response streaming, transient errors, redirects, unexpected encodings, HTML,
limits, cancellation/lease replacement, retained-capture reuse, backup/restore,
strict source ownership and complete weather→PV→energy behavior. Production
source access, provider rate/availability conditions and EN/DE customer states
must be validated before native installation and delivery. Full engineering,
country/equipment, reports and site-consumer goals remain unchanged.
