# Dedicated managed numerical worker: systemd hosting facts

2026-10-24. Scope: construct and review the worker service; no unit was installed,
reloaded or started. Read-only `ssh linker-services` returned
`systemd 255 (255.4-1ubuntu8.18)` and confirmed `systemd-analyze verify`,
`--man=no` and `--generators=no` are available. The upstream v255 documentation
below matches the installed major version; Ubuntu packaging may contain patches.

## Environment and command execution

`EnvironmentFile=` reads UTF-8 assignments shortly before executing the process.
An absolute filename without the optional leading `-` makes an absent file an
error. It is an assignment file, not a shell script. Values from it override
`Environment=` values; later environment files override earlier files.
[systemd.exec v255: EnvironmentFile](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html#EnvironmentFile=).

`ExecStart=` performs its own argument parsing and environment substitution.
`${NAME}` contributes exactly one argument, preserving whitespace; an undefined
variable becomes empty. `$NAME` as a separate word can split into multiple
arguments. Pipes, redirection and command substitution require an explicitly
invoked shell. The executable in the first position cannot itself be a variable.
[systemd.service v255: command lines](https://www.freedesktop.org/software/systemd/man/255/systemd.service.html#Command%20lines).

The proposed direct command therefore needs no shell wrapper:

```ini
ExecStart=/opt/linker-engine/current/.venv/bin/python -m linker_engine.planning.worker_host serve --expected-runtime ${LINKER_PLANNER_RUNTIME_SHA256} --expected-execution ${LINKER_PLANNER_EXECUTION_KEY} --expected-storage ${LINKER_PLANNER_STORAGE_BINDING} --generation ${INVOCATION_ID}
```

Project integration: `/etc/linker-planner-worker.env` should supply only
`LINKER_PLANNER_CONFIG`, `LINKER_PLANNER_WORKER_CONFIG` and the three expected
non-secret identities above. These are the runtime/worker JSON paths and expected
runtime, execution and storage hashes defined by
[the managed-worker contract](../../specs/548-managed-energy-worker.md) and checked
by [worker_host](../../../services/engine/src/linker_engine/planning/worker_host.py).
The strict CLI validation rejects missing/empty or malformed identities. Do not
put model, service, HTTP or provider credentials in this file. Environment
variables are not a confidential credential transport according to
[systemd.exec](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html#Environment=).
This choice does not establish a complete security assessment.

## Launch generation and readiness

`INVOCATION_ID` identifies one unit runtime cycle: systemd assigns a new
randomized 128-bit ID on an inactive-to-activating/active transition, and passes
the same ID to every process of that cycle. It is not a PID or a fresh ID per
`ExecStartPre`/`ExecStart` child.
[systemd.exec: INVOCATION_ID](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html#%24INVOCATION_ID).
The v255 implementation formats it through `sd_id128_to_string`, whose format is
32 lowercase hex digits, matching `worker_host`'s generation validation.
[unit.c, invocation formatting](https://github.com/systemd/systemd/blob/v255/src/core/unit.c#L3487-L3488),
[sd_id128_to_string](https://www.freedesktop.org/software/systemd/man/255/sd_id128_to_string.html#Description).

The generated value is available to `ExecStart` substitution: v255 adds it to
`our_env`, merges that into `accum_env`, then calls `replace_env_argv` against
that merged environment.
[exec-invoke.c: generation](https://github.com/systemd/systemd/blob/v255/src/core/exec-invoke.c#L1936-L1943),
[environment merge](https://github.com/systemd/systemd/blob/v255/src/core/exec-invoke.c#L4505-L4510),
[argument expansion](https://github.com/systemd/systemd/blob/v255/src/core/exec-invoke.c#L5183-L5194).
Keep `INVOCATION_ID` out of explicit environment settings/files so they do not
override systemd's generated value.

`Type=exec` waits until the main executable has been successfully invoked and
makes invocation/setup failures visible to `systemctl start`. It does not wait
for Python imports, configuration validation, execution-identity agreement or
publication of the readiness record. That requires the project's independent
readiness check, including live process identity and generation. `Type=notify`
would require explicit notification support in the application; the current host
publishes a private file instead.
[systemd.service: Type](https://www.freedesktop.org/software/systemd/man/255/systemd.service.html#Type=).

## Restart and stop semantics

| Candidate directive | Verified behavior and integration consequence |
| --- | --- |
| `Restart=on-failure` | Retries a nonzero exit, unclean fatal signal or applicable operation timeout. Exit zero and clean signals including SIGTERM/SIGINT do not trigger it; explicit `systemctl stop` does not trigger it. Restart rate limits still apply. It is not a promise to restart every termination. [Restart](https://www.freedesktop.org/software/systemd/man/255/systemd.service.html#Restart=) |
| Explicit `TimeoutStopSec=` | With no `ExecStop=`, systemd sends the initial termination signal immediately, waits this duration for termination, then normally forces SIGKILL. Select and document an operator stop budget; the project's 30-second development drain deadline is not measured production sizing. [TimeoutStopSec](https://www.freedesktop.org/software/systemd/man/255/systemd.service.html#TimeoutStopSec=) |
| `KillMode=control-group` | The default mode covers all processes in the unit. It begins with SIGTERM by default, followed by SIGKILL after the timeout with default `SendSIGKILL=yes`; it does not mean immediate SIGKILL. Children receive the initial signal too. `mixed` initially signals only the main process, then forcibly removes remaining unit processes; `process`/`none` permit unmanaged survivors and are discouraged upstream. [KillMode](https://www.freedesktop.org/software/systemd/man/255/systemd.kill.html#KillMode=) |

Project integration: the current SIGTERM/SIGINT handler in `worker_host` sets a
stop event; it does not interrupt the active synchronous `worker.run_once()`.
The next loop iteration stops claiming. An active call can therefore finish
within the actual stop window; the timeout can still kill it, leaving the
existing durable lease-recovery contract. A unit stop is not the project's
transactional admission drain and does not prove queued jobs have completed.
If execution later spawns children, review their signal behavior because
`control-group` also signals them. No production timeout or capacity is inferred
from these systemd defaults.

## Release pin and shared-queue boundary

First-party facts: `WorkingDirectory=` sets the process working directory.
Python `-m` finds the module through `sys.path` and normally prepends that working
directory. Python virtual environments can contain absolute interpreter paths
and should be recreated at their intended location when moved.
[WorkingDirectory](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html#WorkingDirectory=),
[Python 3.12 -m](https://docs.python.org/3.12/using/cmdline.html#cmdoption-m),
[Python 3.12 virtual-environment portability](https://docs.python.org/3.12/library/venv.html#how-venvs-work).

Integration inference from those facts and this project's execution-key contract:
`/opt/linker-engine/current/...` is a mutable release selector, not an immutable
executable pin. A later start through it may select a different interpreter,
installed package or source tree after `current` moves. This does not establish
that an already running process immediately switches all its imported code.
A retained executable strategy must bind the interpreter/venv, working directory,
package/source lookup and runtime identity to the same immutable release, and
keep that release usable while jobs require its execution key. Pinning only one
path is insufficient evidence of that agreement. The first executable cannot be
made `${RELEASE}/...` through ordinary `ExecStart` environment substitution;
materialize an absolute per-release executable path in the reviewed unit or
choose another explicitly verified launch mechanism.

Systemd provides no application-level queue-schema or energy-model compatibility
guarantee. Older/newer retained workers sharing one workspace still need the
project's matching execution keys, storage binding, additive routing behavior,
lease fencing and actual compatibility tests. This is an integration requirement,
not a vendor claim or proof that retained releases are installed in production.

## Verification limit

`systemd-analyze verify` can detect unknown directives, required dependencies and
missing/non-executable command paths. Run it against the staged candidate with
the installed systemd version and its intended executable/dependency paths
available. A clean analyzer result does not run Python startup, validate the
private JSON settings, prove readiness, exercise SIGTERM/lease recovery or prove
that the matching HTTP/worker release is serving the shared queue.
[systemd-analyze: verify](https://www.freedesktop.org/software/systemd/man/255/systemd-analyze.html#systemd-analyze%20verify%20FILE...).
No candidate verification or production acceptance is claimed by this research.

## Acquisition and provenance

External material was acquired through Apify only. Authentication succeeded using
the available environment credential; no credential or account identity is stored
here. All prose above is paraphrase or explicitly marked project integration;
there are no verbatim prose quotations.

| Actor | Run / dataset | Acquisition UTC | Result |
| --- | --- | --- | --- |
| `apify/website-content-crawler` | `PFWDQGHIW4QyE51cs` / `YMBZs06NMU63Xm92w` | 2026-10-23 23:14:47.691–23:14:54.553 | Six official systemd/Python pages, six requests succeeded, all nonempty. |
| `apify/website-content-crawler` | `pkCF5PInXQdT2AcLy` / `INTmR87ImNM5g0IaL` | 2026-10-23 23:15:47.772–23:15:54.091 | GitHub HTML acquired but source truncated; not used as source evidence. |
| `apify/website-content-crawler` | `ZoyYi3N3ua5tkRVmh` / `nqq4xxHZ9e3GJUPnT` | 2026-10-23 23:16:45.460–23:16:50.380 | Raw source captured by the file downloader; HTML requests reported download-start errors and dataset is empty. Complete source recovered from this run's Apify key-value store. |
| `apify/website-content-crawler` | `OLxqSwc1ghI8aEsTf` / `IaxyRvv0x4oRlCqVh` | 2026-10-23 23:18:12.964–23:18:17.633 | Official ID-format page, one request succeeded, nonempty. |

The raw-download recovery uses key-value store `6xqZPZd0z3iuQYu5A`, records
`file-24cf82b-exec-invoke.c` (214490 bytes) and `file-0804f5f-unit.c` (229411 bytes).
An alternative Cheerio Actor request was denied before producing a run; no
non-Apify retrieval was used. Recovery through the original crawler's stored
files supplied the complete code and line numbers above.

SHA-256 of acquired Markdown text (manuals) or exact file bytes (source), in
source URL order:

| Official source | SHA-256 |
| --- | --- |
| `systemd.exec.html` v255 | `89ed71c57c2a65028246012599da1b0f503198993cfc2ddb6be3269847fa1d77` |
| `systemd.service.html` v255 | `33d51656af50ef4a32d193e2061f87b43a2577e8f779f8bf4dcd7fd5cb005f42` |
| `systemd.kill.html` v255 | `d74a5c1dc9072b1a542770ce70d7af78ece9067ac321d99ee09e3a3127b93336` |
| `systemd-analyze.html` v255 | `9bf85b40b718cca9ec774050204a6da882e00649c2bd96e37dd8477efb2fe6bf` |
| Python 3.12 `using/cmdline.html` | `70d6d782bcfc789d68434ae75e6532a36eda0ea74839194abfd7028719b3c38b` |
| Python 3.12 `library/venv.html` | `af428162ef3363cea75e3646cb15898f9daaa6b15aaed5cf12feee45de892f83` |
| `sd_id128_to_string.html` v255 | `e0fff94e4c89af4318a70b13fa103be31cc52e7d42b95149fc3a8a6fa17a3d76` |
| [v255 `exec-invoke.c`](https://raw.githubusercontent.com/systemd/systemd/v255/src/core/exec-invoke.c) | `33da124c5cd657c09c2325641425a99be6df50e40e92d2bb18441f209d29ae46` |
| [v255 `unit.c`](https://raw.githubusercontent.com/systemd/systemd/v255/src/core/unit.c) | `d3c14e765dceeafd8e2d1fe94ed685c5dfc1c35f0a32c8459046a0459a1c57c4` |

Only this small report was created locally. No new worktree, instance,
dependency tree, backup or copied source archive was created.
