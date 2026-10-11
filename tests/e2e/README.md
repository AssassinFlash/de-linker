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
(the English catalogue's German twins) and `tools/migrate/8-engineering.py
--write` (the engineering data the configurator sizes against — `just serve`
reads the site's own `linker/v1/engineering-feed` into the engine, and the
engine refuses a design without it).

The suite resolves the instance from `~/de-linker-local/instances.toml`
(`LINKER_LOCAL_HOME` overrides the location, `LINKER_E2E_INSTANCE` the name).
A missing instance, a missing service or a typo in the name fails the run with
the command that fixes it — nothing is skipped silently.

## What it needs from the machine

- The site answering on the instance's port, and `just serve`'s two services.
- `uv` (the Jev cascade in `services/genie/eval/judges`), and the judge
  credentials the cascade reads from `~/.config/terravolt-builder/` — the Jev
  first pass and the direct DeepSeek escalation (`docs/specs/33-judge-bakeoff.md`).
- A live snapshot under `~/de-linker-data/` for `i18n.spec.ts`'s German
  address list (`LINKER_E2E_SNAPSHOT` points at a specific one).

## Shape

- `specs/` — one file per surface; the Genie rows are `genie.spec.ts`
  (service level, R1–R14 with the cascade judging every question) and
  `genie-dock.spec.ts` (the browser half: disclosure, chip, session, reload).
- `lib/` — the instance and its mail spool, the Genie and engine clients, and
  the bridge to the cascade judge.
- Rows that depend on work the main line still owes are marked `pending-main`
  at runtime (`test.skip(condition, 'pending-main: …')`), so they stay visible
  in the report and run again as soon as the reason is gone.
