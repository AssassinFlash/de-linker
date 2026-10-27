# Apify weather transport: verified implementation facts

2026-10-24 UTC. External reads reused the existing Apify dataset and INPUT/KV endpoints. One small docs-only pinned Actor run acquired the previously missing requestListSources specification. **No weather Actor was started, no weather body was downloaded, and no application, dependency, service or database was changed.** This is component research, not live workflow acceptance.

## Exact HTTP contracts

Recovered the omitted response sections by GET of existing dataset `dftNO1TLfoZWg7XyJ` from run `lXvujgaIwxLKdgr07`; the selected docs response was HTTP 200/application/json. [Acquisition hash and excerpt ranges](raw/api-doc-response-provenance.json).

| Operation | Documented success | Successful body |
| --- | --- | --- |
| POST `/v2/actors/{actorId}/runs` | **201** | Object with **`data` containing the run object** |
| GET `/v2/actor-runs/{runId}` | **200** | Object with **`data` containing the run object** |
| POST `/v2/actor-runs/{runId}/abort` | **200** | Object with **`data` containing the run object** |
| GET `/v2/datasets/{datasetId}/items?format=json` | **200** | **Array** of records; no run/data envelope |
| GET `/v2/key-value-stores/{storeId}/records/{key}` | **200** | **Raw stored value**, e.g. INPUT object or weather `inputs`/`outputs`/`meta`; no Apify envelope |

Primary sources: [start](https://docs.apify.com/api/v2/act-runs-post), [get run](https://docs.apify.com/api/v2/actor-run-get), [abort](https://docs.apify.com/api/v2/actor-run-abort-post), [dataset](https://docs.apify.com/api/v2/dataset-items-get), [KV record](https://docs.apify.com/api/v2/key-value-store-record-get). Corresponding compact `*-responses.txt` files retain the exact relevant sections and official example envelopes. Actual prior [start/readback](../2026-10-24-pv-managed-intake/raw/docs-run.json) confirms 201/200 and the pinned build. Abort success is documented; no abort was performed here.

Select only `id`, `actId`, `buildId`, `buildNumber`, `status`, `defaultDatasetId`, `defaultKeyValueStoreId`, `startedAt`, `finishedAt` from a run; do not retain its account/billing/access fields. The actual start has READY and null `finishedAt`, later SUCCEEDED and a finish timestamp. `maxTotalChargeUsd` is a **query `double`**, not an integer; use an explicit finite positive decimal value. `maxItems` limits pay-per-result charges and does not guarantee the number of returned records. [Start contract](https://docs.apify.com/api/v2/act-runs-post), [retained response prose](raw/act-runs-post-responses.txt).

## INPUT, capture and KV bytes

Existing docs and weather INPUT GETs both returned **200/application/json**, no Content-Encoding, and exact submitted-field echoes. Apify adds defaults. A headers-only HEAD of the existing weather file record also returned **200/application/json**, without following redirects or downloading its body. [Current selected readback](raw/input-kv-readback.json).

For weather, require the unique matching dataset `url`, `crawl.loadedUrl`, `crawl.httpStatusCode == 200`, `crawl.contentType` JSON and a file record in the acknowledged run's own KV store. The actual retained record has `html/text/markdown == null`; raw weather comes from `fileUrl`, not those text fields. The original weather remains SHA256 `5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`, 1268118 bytes. [Existing capture](../2026-10-24-pv-generation/raw/acquisition-items.json), [existing weather provenance](../2026-10-24-pv-generation/raw/weather-provenance.json).

KV documentation explicitly permits **302** and returns the stored content type; content may be decompressed according to request headers. A 302 is not a weather body. Reject unapproved redirects before consuming the body or forwarding authorization; keep token authentication in server-held headers and omit temporary signed queries from evidence. Validate the MIME base type separately from optional charset parameters, then strict JSON. Capture wire length is not decoded length: the prior source-file capture reported 14520 bytes while its verified KV body was 60724. [KV primary contract](https://docs.apify.com/api/v2/key-value-store-record-get), [actual differing lengths](../2026-10-24-pv-managed-intake/raw/files-provenance.json).

### Complete safe effective-INPUT baseline

The exact known-safe weather INPUT is retained once as [weather-effective-input-baseline.json](raw/weather-effective-input-baseline.json): **1686 bytes**, SHA256 **`361ce26601d9028ac3f76712f7be4977b99fc724c6a77054912ccfdd9a0cf5ab`**. [Endpoint/hash/safety provenance](raw/baseline-provenance.json).

It has **51 keys**, with no intrinsic per-run variable field found across the two observed runs after accounting for submitted overrides. Sensitive-capable fields are currently safe: `proxyConfiguration={"useApifyProxy":true}`, fixed public `startUrls`, fixed Accept/User-Agent headers, empty `pageFunction`, false `signHttpRequests`, `summarize`, `useLlmsTxt` and `useSitemaps`; there are no pre/post-navigation hooks, proxy credential URLs, cookies or signed URLs. [Known field/type projection](raw/effective-input-safety.json), [pinned build schema](../2026-10-24-pv-managed-intake/raw/apify-metadata.json).

The docs acquisition explicitly supplied `initialConcurrency=1,maxResults=8`; those are **not** the omitted-field defaults. The weather run omitted them and received **`initialConcurrency=0,maxResults=9999999`**. Start from the safe weather baseline and overlay the exact server-owned `plan.actor_input()`; the plan's `maxResults=1` overrides the large default. Complete canonical equality before CAS retention proves all known effective values and rejects unknown/dangerous values. This is a strict pinned-build application contract supported by observed responses, not a provider promise that its schema will never change. If fields are dropped instead, label the retained object a projection and keep the original hash; do not call it the full exact INPUT.

## Installed client source: bounded reads and cancellation

Inspected **requests 2.34.2 / urllib3 2.8.0** under the existing engine `.venv`. [Exact local source paths, hashes and bounded line excerpts](raw/http-client-source.json).

- **Redirect trap:** `Session.send` lines 817–822 invokes `resolve_redirects(...yield_requests=True)` even with `allow_redirects=False`; that resolver consumes `resp.content` at lines 211–214. Consequently a streamed Session request can consume an unbounded redirect body before the caller's status check. Direct `HTTPAdapter.send(PreparedRequest,stream=True,...)` bypasses that Session path; the adapter sets `redirect=False,preload_content=False,decode_content=False` (adapter lines 695–708). The adapter's default is `Retry(0,read=False)`; do not enable implicit start-POST retries.
- **Raw read boundary:** urllib3 `HTTPResponse.read1(amt,decode_content=False)` uses `_raw_read(amt,read1=True)` and returns without the decompressor loop (response lines 1241–1245). Choose a positive bounded amount, check cancellation/deadline before and after each call, and count actual bytes. Avoid `read()`, `.content`, `.text` or `.json()` before enforcing the body bound.
- **Decompression trap:** `read1(...decode_content=True)` may perform repeated internal 8192-byte reads until decoded output appears (lines 1247–1256). `_decode` also removes its max-length bound while flushing (lines 660–675). It is not one raw-read/cancellation opportunity. Reading encoded bytes without automatic decoding and applying an explicitly bounded identity/gzip policy permits checks between input chunks; gzip output and completion need their own limits/validation. This is an engineering conclusion from the inspected source, not a claim that all decoder paths have strict memory bounds.
- **Error/close boundary:** direct raw reads expose urllib3 `ReadTimeoutError`, `SSLError` and `ProtocolError` from `_error_catcher`; requests translates these only inside helpers such as `iter_content`. `Response.close()` closes an unconsumed raw response and releases its connection. Close every response on success, rejection, cancellation and error.
- **Deadline limits:** urllib3 documents read timeout as time between socket reads, not whole-response elapsed time; even its `total` option does not create an absolute complete-body deadline, and DNS may ignore socket timeouts. A monotonic overall deadline, finite per-call timeouts clipped to the remaining budget, finite poll/retry counts and cancellation checkpoints are separate application controls. Do not describe these as immediate interruption of every blocking resolver/header read. [Installed timeout source lines 76–103](raw/http-client-source.json).

No duplicate library source, new weather sample or running copy was retained. The raw folder contains only compact official-doc response excerpts, selected readback, one unique safe INPUT baseline and local source fingerprints/excerpts.

## Requested correlation-nonce evidence

The pinned build's `startUrls` schema is an array with editor `requestListSources` and no item-property restriction. Its readme shows URL-only examples; it does not state `userData` echo behavior. The version API exposes version/source-type metadata but no Actor source files. [Selected pinned-build/version probe](raw/start-url-correlation-probe.json).

Docs-only run **`a6I92wwUlGLV6ZcPd`**, pinned to the same build, fetched the previously unacquired official input-schema specification and completed SUCCEEDED, 1/1 requests. It had already started with a URL-only entry before the request to add a nonce arrived; it was not restarted. [Immediate handle and final readback](raw/correlation-docs-run.json), [request](raw/correlation-docs-input.json), [document provenance](raw/correlation-docs-provenance.json).

The specification explicitly says the `requestListSources` editor supports formats defined by Crawlee `RequestListOptions.sources`, and its value can be passed to `RequestList`. It links that source contract but does not itself name `userData`. [Official specification](https://docs.apify.com/platform/actors/development/actor-definition/input-schema/specification/v1), [exact excerpts](raw/request-list-sources-excerpt.txt). Together with the start endpoint's INPUT-payload contract, this supports trying a server-owned `startUrls:[{url,userData:{linker_acquisition_intent:nonce}}]` correlation field in the intended weather trial. **Exact acceptance/preservation by pinned Actor 0.3.101 remains unverified here**; no nonce-bearing trial was performed. Recovery must not rely on that echo until the intended trial confirms the exact submitted/effective field, rather than merely an older identical URL/input. No second documentation or weather trial was started.

## Subsequent implementation verification by the owning session

The research-only scope above ended before these two separate weather tasks.
The owning session subsequently exercised the actual new client and durable
orchestrator in an isolated component workspace. Both used the pinned build,
an exact official request and `userData.linker_weather_intent` with the local
journal's unique nonce. Both effective INPUTs echoed that exact value and
passed the complete safe-default equality check. This closes the nonce-echo
question for the exercised build/input; it is not a general Actor guarantee.

Run `tXCGhHtxHRpnGQrOS` reported SUCCEEDED but the origin returned HTTP 200,
245-byte text/html “Request Rejected”. The client rejected it before any
weather file download or capture publication. The original one-POST permit
was not reused. [Selected dataset diagnostic](../../acceptance/2026-10-24/548/weather-transport/actual/rejected-origin-1/dataset-diagnostic.json),
[exact safe INPUT](../../acceptance/2026-10-24/548/weather-transport/actual/rejected-origin-1/effective-input-exact.json),
[local retirement](../../acceptance/2026-10-24/548/weather-transport/actual/rejected-origin-1/retirement.json).

The prior successful primary request explicitly supplied
`User-Agent: python-requests/2.32.5`; the initial typed plan had omitted it.
A separate explicitly issued local task restored that fixed header in the
server-owned submission rule. Run `lIRorkxw3OO4XpEUq` completed and supplied
one matching application/json file. Authenticated fixed-origin retrieval,
exact INPUT/nonce validation, full original-TMY checks and durable capture
all passed. The 1,268,118-byte raw file's SHA256 is
`5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`,
identical to the retained prior primary sample; only a hash-verified reference
was retained for that original. [Actual result](../../acceptance/2026-10-24/548/weather-transport/actual/accepted/result.json),
[capture/CAS references](../../acceptance/2026-10-24/548/weather-transport/actual/accepted/blob-references.json).

One successful repair does not isolate the header as the cause of the earlier
rejection or establish cross-location availability. Do not loosen content
checks or silently retry a start on that basis. This entire increment started
**one docs-only Actor and two weather Actors**, each weather task exactly once.
It created no live owned asset, touched no p548 data/runtime and installed no
managed executor/UI. The temporary rehearsal workspace was retired after
hash-verifying its retained evidence. [Cleanup](../../acceptance/2026-10-24/548/weather-transport/cleanup.json).
