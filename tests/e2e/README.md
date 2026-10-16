# The regression suite (docs/specs/16-review-acceptance.md)

Playwright over a running local instance: the review site's whole chain, from
the behaviour panel of Genie to the commercial journey and the German tree.

## Running it

```sh
just up t16e
# load a live snapshot and activate the checkout's plugins (docs/specs/6-live-pull.md)
just serve t16e
just e2e t16e                 # everything
just e2e t16e specs/genie.spec.ts
just e2e t16e --grep "commercial chain"
```

The instance must be a real one: `just up` + a snapshot (`just pull load <name>
<snapshot> --live-code`), the plugins from this checkout, `wp linker-i18n setup
--assign`, `wp linker-commerce present`, `tools/migrate/9-i18n.py apply --write`
(the English products' German twins), `tools/migrate/8-engineering.py
--write` (the engineering data the configurator sizes against — `just serve`
reads the site's own `linker/v1/engineering-feed` into the engine, and the
engine refuses a design without it) and `tools/migrate/12-site-chrome.py apply
--write` (the tool names, the configurator's own addresses and the retired
pages — the chrome spec's redirect cases land on the pages it renames; pass
`--wp` a WP-CLI prefix and `--user <admin>`).

A snapshot instance that has not run one of the migrations is a setup gap, not
a defect: the row that needs it says which migration is missing and how to run
it, instead of failing as a 404.

The suite resolves the instance from `~/de-linker-local/instances.toml`
(`LINKER_LOCAL_HOME` overrides the location, `LINKER_E2E_INSTANCE` the name).
A missing instance, a missing service or a typo in the name fails the run with
the command that fixes it — nothing is skipped silently.

`LINKER_E2E_SKIP_SERVICES=1` is the one declared exception, for a page spec
that renders WordPress only and never talks to the engine or Genie
(`specs/empty-draft.spec.ts`; run it as
`LINKER_E2E_SKIP_SERVICES=1 just e2e <name> specs/empty-draft.spec.ts`). It
drops the two service health checks from the gate and keeps WordPress's: the
instance must still answer `/wp-json/`, and a name that is not registered
still fails. Any other value, or a service suite that needs the engine, runs
the full gate.

## What it needs from the machine

- The site answering on the instance's port, and `just serve`'s two services.
- `uv` (the Jev cascade in `services/genie/eval/judges`), and the judge
  credentials the cascade reads from `~/.config/terravolt-builder/` — the Jev
  first pass and the direct DeepSeek escalation (`docs/specs/33-judge-bakeoff.md`).
- A live snapshot under `~/de-linker-data/` for `i18n.spec.ts`'s German
  address list (`LINKER_E2E_SNAPSHOT` points at a specific one).

## Shape

- The cascade's records land under the instance, beside its mail:
  `~/de-linker-local/<name>/e2e-judge/<stamp>/` — `run/summary.json` per
  question, plus `run/jev.jsonl`, `run/deepseek.jsonl` and
  `run/cascade.jsonl`. They stay there after the run, so a disagreement the
  suite printed can be read back; the path is printed when judging starts.
- Screenshots a spec takes as evidence land in the repository's working area,
  `.scratch/e2e-shots/<spec>/` (`.gitignore`d): they show what that run
  rendered, so they are run artefacts, never a commit (ledger H10 — the
  account spec used to overwrite committed PNGs under `docs/acceptance/`).
- `specs/` — one file per surface; the Genie rows are `genie.spec.ts`
  (service level, R1–R14 with the cascade judging every question) and
  `genie-dock.spec.ts` (the browser half: disclosure, product entry, session,
  reload).
- `lib/` — the instance and its mail spool, the Genie and engine clients, and
  the bridge to the cascade judge.
- Rows that depend on work the main line still owes are marked `pending-main`
  at runtime (`test.skip(condition, 'pending-main: …')`), so they stay visible
  in the report and run again as soon as the reason is gone. A row whose
  subject only exists after an instance migration is marked `pending-setup` the
  same way, naming the command that closes it (`chrome.spec.ts`'s redirect
  landings before `12-site-chrome.py apply --write`). A row that waits for a
  fixture another row builds at runtime — neither the main line's work nor an
  instance migration — is marked `pending-fixture`, naming the row that builds
  it (`genie-dock.spec.ts`'s suite customer, built by `products.spec.ts`'s
  `ensureCustomer()` on every run: it exists from the second suite pass on).
