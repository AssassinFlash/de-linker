# `just cutover …`: the one-time switch of de-linker.com onto the new tree
# (docs/specs/17-cutover.md). Every step is separately re-runnable; the target
# is the production host unless a step is given `--target local:<name>`, which
# is how the drill runs the same code.

set shell := ["bash", "-euo", "pipefail", "-c"]
set ignore-comments := true

# `justfile_directory()` is the directory of the root justfile that imported this
# module (tools/pull/pull.just does the same and appends its own path).
project := justfile_directory() / "tools/cutover"
# WP-CLI runs on PHP 8.3, as in the root justfile.
php := env("PHP", if path_exists("/opt/homebrew/opt/php@8.3/bin/php") == "true" { "/opt/homebrew/opt/php@8.3/bin/php" } else { "php" })
linker_cutover := "uv run --locked --project " + quote(project) + " linker-cutover"

# List the recipes.
default:
    @just --list --list-submodules --justfile {{ justfile() }}

# Rehearse the whole switch on a local instance: switch, roll back, switch
# again (spec 17's precondition). Writes; leaves a record under docs/acceptance.
[positional-arguments]
drill instance *options:
    PHP={{ php }} {{ linker_cutover }} drill --instance "$@"

# Step 1: the complete backup of the site into ~/de-linker-data/cutover-<date>/.
[positional-arguments]
backup *options:
    PHP={{ php }} {{ linker_cutover }} backup "$@"

# Steps 2 and 7: the maintenance window. `just cutover maintenance on|off`.
[positional-arguments]
maintenance state *options:
    PHP={{ php }} {{ linker_cutover }} maintenance "$@" --write

# Step 3: build and deploy the three plugins, install Polylang.
[positional-arguments]
deploy *options:
    PHP={{ php }} {{ linker_cutover }} deploy "$@" --write

# Restore the preceding file deploy by rename; no database import or upload.
[positional-arguments]
rollback-deploy *options:
    PHP={{ php }} {{ linker_cutover }} rollback-deploy "$@" --write

# Step 3: export the snippet rows, then deactivate and delete the legacy plugins.
[positional-arguments]
plugins *options:
    PHP={{ php }} {{ linker_cutover }} plugins "$@" --write

# Step 4: the data migrations (7, 8, 9). Without --write they print their plan.
[positional-arguments]
data *options:
    PHP={{ php }} {{ linker_cutover }} data "$@"

# Step 4: retire the retained SEO plugin's stored Product schema template.
[positional-arguments]
schema *options:
    PHP={{ php }} {{ linker_cutover }} schema "$@"

# Step 5: publish the two services. Needs the VPS; without --run it reports.
[positional-arguments]
services *options:
    PHP={{ php }} {{ linker_cutover }} services "$@"

# Step 6: host housekeeping. Without --write it reports what it would do.
[positional-arguments]
hygiene *options:
    PHP={{ php }} {{ linker_cutover }} hygiene "$@"

# Step 7: the read-only regression subset of both languages and the redirect.
[positional-arguments]
verify *options:
    PHP={{ php }} {{ linker_cutover }} verify "$@"

# Step 8: put a backup back.
[positional-arguments]
rollback *options:
    PHP={{ php }} {{ linker_cutover }} rollback "$@"

# Ruff (lint + format) and mypy (strict) over tools/cutover.
check:
    cd {{ project }} && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked mypy .

# pytest; no WordPress is started (the drill itself is the end-to-end run).
test:
    cd {{ project }} && uv run --locked pytest
