# VPS boundary evidence

Source baseline: deployed dcd5560d. Production was inspected read-only; this branch has not been deployed by this worker.

## Native checks

- Full engine pytest: 157 PASS (15.22s), including normal postcode, residential/commercial, PDF and roof fixture behavior, service-gate slots, private live-version contract, and the new endpoint inventory/config backup+rollback tests.
- Focused Genie pytest: 58 PASS (20.91s), covering endpoint inventory, header-first refusal, health, real work-slot lifetime, provider accounting, inquiry assessment and ordinary turn fixtures.
- Engine Ruff PASS; mypy PASS (52 files).
- Full Genie pytest: 1963 PASS,1 skipped,195 deselected,6 existing xfailed (52.65s). No new skips or expected failures.
- Genie Ruff PASS; mypy PASS (183 files).

The native tests use fixtures/stub transports; they issue no paid model request or mail. The shell migration fixture uses real tar/install against a temporary filesystem, and mocked nginx/systemctl commands. A real isolated Nginx test is a distinct gate and must not be inferred from that shell fixture.

## Before-change runtime readback

- Engine `POST /design/residential`, `/design/commercial`, `/roof/outline`, `/roof/pack`, `/report/pdf`: all unauthenticated401, directly and through dedicated TLS proxy.
- Genie `POST /budget/take`, `/turn`, `/assistant/turn`, both vote aliases, `/summary`, conversation forget, `/pages/invalidate`, `/inquiries/assess`: all unauthenticated401, directly and through dedicated TLS proxy.
- Engine private version GET: anonymous401, trusted200 with valid64hex. Trusted malformed engine POST without resource subject400; trusted malformed Genie turn422.
- Both services schema UI/OpenAPI GETs200 before change. Native revised apps404 for docs/redoc/OpenAPI/OAuth redirect.
- Engine0.0.0.0:8901, Genie127.0.0.1:8902, dedicated Nginx0.0.0.0:8443. IPv4 firewall blocks8901, permits8443 only from Hostinger egress, blocks other8443. No project IPv6 wildcard listeners.
- Engine gate enforce; provider budget enforce; Genie work enforce. Persistent provider/work/engine-slot files0600, parent directories0700.
- Project Nginx old4MiB cap confirmed; existing engine6MiB/WordPress Genie30MiB raw-request caps; native Genie schema headroom is33,659,180bytes and remains unchanged. TLS1.2/1.3. Shared Nginx/VPN instance is separate and unchanged.

Aggregate route/status observations only; no submitted customer content, service token, model key, raw credentials or unrelated proxy credentials are included.

## Real isolated ingress fixture

`proxy_probe.py` ran with the installed engine virtualenv and both installed native Gate classes, on three random loopback high ports under a disposable `/tmp` tree. It parsed the exact candidate project configuration with real Nginx before creating an isolated copy. Only runtime/listen/upstream paths, worker user and TLS were adapted for the loopback fixture; the actual proxy/body directives were retained. The upstream after each Gate was a synthetic byte-count sink, so no model, attachment parser, engineering calculation or mail ran.

`proxy-results.txt` records candidate SHA256 and all11 checks: anonymous header-only requests were401 before any body was sent (engine1.6ms,Genie2.3ms);4MiB+1 and the engine6MiB/WordPress Genie30MiB maxima reached the sink intact; declared and chunked proxy cap+1 requests were413; the actual native Genie33,659,180byte counted-stream cap independently returned413 at+1. Spool file count was0. The fixture's30MiB ingress envelope is deliberately distinguished from Genie's larger schema-derived headroom; neither source cap was changed.

All owned processes and temporary trees were removed. The follow-up socket/process check found no fixture listeners or `/tmp/linker539-*` trees; the live project's engine56381,Genie54499 and TLS731 PIDs remained unchanged and active. No live configuration, firewall, ledger or shared service was changed.

## Review and release boundary

Independent Spec/Standards reviews, exact-head CI and production activation/readback are separate gates coordinated by the root execution. This evidence does not mark the ticket or full security upgrade complete.
