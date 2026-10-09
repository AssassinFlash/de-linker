# `just pull …`: read-only snapshots of de-linker.com into
# ~/de-linker-data/<YYYYMMDD-HHMM>/ and loading them into local instances
# (docs/specs/6-live-pull.md). `just pull` takes a snapshot.

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments := true
set ignore-comments := true

project := justfile_directory() / "tools/pull"
# WP-CLI runs on PHP 8.3, as in the root justfile: Homebrew's php@8.3 when it
# is installed, otherwise `php` on PATH; `PHP=/path/to/php just …` wins.
php := env("PHP", if path_exists("/opt/homebrew/opt/php@8.3/bin/php") == "true" { "/opt/homebrew/opt/php@8.3/bin/php" } else { "php" })
linker_pull := "uv run --locked --project " + project + " linker-pull"

# Copy the live site into a new snapshot (database pseudonymized on arrival).
[default]
snapshot:
    {{ linker_pull }} snapshot

# Load a snapshot into an instance: <name> <snapshot|latest> [--port N] [--live-code].
load name snapshot *options:
    PHP={{ php }} {{ linker_pull }} load "$@"

# What changed between two snapshots: <old> <new> [--json].
diff old new *options:
    {{ linker_pull }} diff "$@"

# Check a snapshot's SQL for password hashes, credentials and addresses.
scan snapshot:
    {{ linker_pull }} scan "$@"

# Pseudonymize a mysqldump file: <source.sql[.gz]> <target.sql.gz>.
anonymize source target:
    {{ linker_pull }} anonymize "$@"

# Request every sitemap address of a snapshot from an instance: <snapshot> --base <url> [--sitemap <file>].
check-urls snapshot *options:
    {{ linker_pull }} check-urls "$@"

# Ruff (lint + format) and mypy (strict) over tools/pull.
check:
    cd {{ project }} && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked mypy .

# pytest; the load tests build real WordPress instances with this PHP.
test:
    cd {{ project }} && PHP={{ php }} uv run --locked pytest
