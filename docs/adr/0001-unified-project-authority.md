# Unified project authority in the Python engine distribution

Date: 2026-10-22. Status: accepted for implementation; production acceptance is
still pending. Owner: Codex, execution map #548.

## Decision

The unified Solution Configurator owns projects, immutable revisions, frozen
calculation runs, private assets, durable work and engineering handoffs inside
the existing `linker-engine` Python distribution. WordPress/WooCommerce remain
authoritative for identities, products, account/price/stock rules and inquiries.
The roof workflow is an optional project task, not a second application.

The first persistent implementation is same-host SQLite WAL plus private
content-addressed files. Short HTTP commands and a separate worker process
share this store. No external request or scientific calculation holds a write
transaction. A registered worker handler operates only on pinned bytes, with
an expiring lease and fencing token. Only its current attempt can atomically
publish a result. Cancellation, retries and crashes cannot silently replace a
published result or attach an old run to edited input.

The same distribution reuses locked dependencies, deployment and Python 3.12;
it does not import the previous residential/commercial sizing algorithms.
There is no new model channel, graph database, Redis, Node server or separate
front-end Tailwind pipeline in this choice.

## Evidence and alternatives

The approved research compared a WordPress-owned orchestration, a modular
Python planning application and separate geometry/energy/selection services.
It selected a modular application because geometry, electrical topology and
continuous dispatch depend on one another, while callers need one consistent
project interface. The recorded host was one CPU, about 4 GB RAM and Python
3.12 with SQLite available. This is a baseline, not a load-capacity promise.
The fixed research is
[`ARCHITECTURE.md`](https://github.com/AssassinFlash/de-linker/blob/e1bfc71801e2a4a6f89fb95a5141264f348dd068/docs/research/2026-10-22-roof-system-rebuild/ARCHITECTURE.md).

SQLite WAL allows concurrent readers and one writer; the processes must share
the same host. It is not the store for a cluster of calculation nodes. Backup
must include committed WAL data and the private files referred to by the
database. We use the online backup API, then copy and verify immutable bytes.
These rules were refreshed through Apify: actor
`apify/website-content-crawler`, run `3weUUeQHqnc23K8ev`, dataset
`UfvuRmJIRs05TMTay`, 3/3 requests succeeded. Primary sources:
[SQLite online backup](https://www.sqlite.org/backup.html),
[SQLite WAL](https://www.sqlite.org/wal.html),
[Python 3.12 Connection.backup](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup).
Input and captured pages are in
`docs/research/2026-10-22-planning-implementation/external/`.

## Consequences and boundaries

The planning service becomes responsible for ownership on reads and writes,
retention, byte integrity, backup/restore, queue recovery and resource limits.
Browser-supplied owners and BOMs cannot establish authority. A verified WP
gateway must supply identities; an `Actor` value inside this module is not an
authentication mechanism. Project commands are not mounted publicly until
that gateway and service authentication are implemented and verified.

Command receipts and acknowledged state commit together. A repeated key with
different input conflicts. Historical inputs/results survive new revisions.
Task success, engineering feasibility/evidence and relation to current input
are independent states. A successful persistence fixture proves no PV or
equipment capability.

There is no blob deletion/GC while an online snapshot can require its bytes.
A snapshot may contain additional published bytes not referenced by its DB
snapshot. Restore verifies DB/hash/foreign keys and every referenced blob,
and writes into a new directory rather than overwriting a running workspace.

Observed write contention, a move to multiple worker hosts, or availability
requirements beyond one host are reasons to revisit storage. Performance,
retention/quotas, gateway identity, numerical models, report/commerce consumers
and live readback remain explicit parts of the active end-to-end delivery;
this record does not mark them delivered.
