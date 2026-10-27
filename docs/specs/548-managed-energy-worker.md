# Managed execution for the unified energy calculation

Continuation of the complete active workbench goal, base `e96d6bea`. The
existing durable Worker, source-pinned EnergyKernel, immutable request/results,
private HTTP and owned local runner remain the implementation basis. The
observed gap is operational: only tests instantiate Worker; the running site
has no managed numerical executor. No replacement physics or new queue library
is needed. This contract makes the existing execution interface usable by the
application; customer scenario/result work continues in the same goal.

## Execution identity and queue authority

- The worker runs as a separate process using the same private workspace and
  RuntimeConfig as HTTP. It registers the actual EnergyKernel, never a fixture
  handler. Startup explicitly matches the HTTP runtime, model and numerical
  settings before readiness. No credential is needed by numerical execution.
- A canonical execution key covers runtime source identity, models and actual
  numerical/resource parameters, excluding per-customer asset dependencies.
  Compatible workers claim only that key. A different runtime/settings job
  remains queued for its matching executable; it does not consume attempts or
  become a failed calculation merely because the newest worker saw it.
- A derived routing index is an additive, rebuildable cache in the existing
  database, not another project authority. New jobs route in the enqueue
  transaction. A rotating bounded scan verifies pending/expired rows, including
  present cache entries, from their hash-verified immutable manifests outside
  numerical execution. Missing and wrong routes are rebuilt; a cached key with
  no active worker cannot strand valid tasks. Corrupt bytes fail explicitly;
  execution identity is also checked before leasing.
  Core project/revision/run/job document formats remain readable unchanged.
- Existing lease, heartbeat, cancellation, retry policy and final publication
  fencing remain effective. HTTP response completion and browser disconnection
  do not execute, terminate or pause a job. Task success remains separate from
  scenario constraints, equipment evidence and country qualification.

## Process and deployment lifecycle

- Explicit strict worker policy includes name, lease, heartbeat, retry, idle
  polling, routing batch, drain deadline and a private readiness path. These
  are operator resource choices, not engineering defaults or capacity claims.
- A readiness record carries process ID, launch generation and execution key;
  a runner also verifies the recorded process birth identity is alive. A stale
  file alone cannot prove readiness. Duplicate use of one worker readiness path
  is refused. Signals stop subsequent loop iterations; a claim already in
  progress is in flight and can finish under its actual lease. A forced process
  loss leaves durable lease recovery.
- A private transactional drain gate rejects new evaluation intents while
  keeping exact existing idempotent receipts readable. Reads, cancellation and
  execution of already queued work continue. The gate check and enqueue share
  one database transaction, so admission cannot race past the drain boundary.
- The local runner owns one worker per existing instance and starts it only
  after authenticated HTTP identity/readiness. Restart drains before replacing
  the engine. A missing matching worker or a drain deadline refuses the restart
  and preserves tasks; it cannot discard jobs, kill another instance or silently
  resume admission. Successful startup opens admission only after both process
  identity and execution settings agree. Stop/status include this owned role.
- The private HTTP version response carries worker execution/storage identity.
  Native WordPress bootstrap projects the stable browser runtime contract
  (schema, runtime hash, models and limits), so private operational additions
  cannot break strict browser session validation or expose operator fields.
- Runtime files are private, created once and preserve subsequent operator
  settings. Existing Genie, PHP and site runtimes keep their identities and
  ports. Production units/configuration are reviewable here but installation,
  retained executable releases, full workload performance and production
  readback remain final-goal gates.

## Development policy and proof

The initial owned local policy is lease 30 s, heartbeat 5 s, retry 2 s, idle
poll 0.5 s, routing batch 128 and drain deadline 30 s. These are explicit
development choices for bounded polling, renewal headroom and interruption
tests, not measured production limits. Startup uses the runner's existing
10-second budget. No battery, load, PV, loss or country parameter is supplied
by this policy.

Verification requires real CAS/SQLite, two execution identities and process
isolation; old unindexed tasks, wrong/corrupt routing, concurrent claim/cancel,
admission-versus-drain and same-intent replay; actual subprocess startup,
signal/lease recovery and private readiness; actual composed HTTP queue to
the independent worker and analytic energy result. Native project reload after
the owned runtime change must retain v14 and its exact inputs. Spec/Standards
and all failures/corrections are separate evidence. This increment does not
accept the unbuilt customer calculation flow or the complete European product.
