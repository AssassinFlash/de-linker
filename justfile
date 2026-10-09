# de-linker tasks. Toolchains, versions and setup: README.md.

set shell := ["bash", "-euo", "pipefail", "-c"]

# `just build` and `just build::check`.
mod build "tools/build.just"

plugins := "linker-commerce linker-i18n linker-tools"
services := "genie engine"

# The PHP tools run on PHP 8.3, the production host's version
# (docs/research/2026-10-09/framework-choice.md §2): Homebrew's php@8.3 when it
# is installed, otherwise `php` on PATH (CI). `PHP=/path/to/php just …` wins.
php := env("PHP", if path_exists("/opt/homebrew/opt/php@8.3/bin/php") == "true" { "/opt/homebrew/opt/php@8.3/bin/php" } else { "php" })

# List the recipes.
default:
    @just --list --list-submodules

# Lint and static analysis of every chain, and the build/ manifest.
check: php-check js-check py-check build::check

# Unit tests of every chain and the end-to-end tests.
test: php-test js-test py-test

[private]
php-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! {{ php }} -r 'exit(PHP_MAJOR_VERSION === 8 && PHP_MINOR_VERSION === 3 ? 0 : 1);'; then
        echo "PHP 8.3 is required; {{ php }} is $({{ php }} -r 'echo PHP_VERSION;'). See README.md." >&2
        exit 1
    fi
    composer="$(command -v composer)"
    for plugin in {{ plugins }}; do
        (cd "plugins/$plugin" && {{ php }} "$composer" install --no-interaction --no-progress --quiet)
    done

[private]
php-check: php-install
    #!/usr/bin/env bash
    set -euo pipefail
    for plugin in {{ plugins }}; do
        echo "== $plugin: PHPCS, PHPStan"
        cd "{{ justfile_directory() }}/plugins/$plugin"
        {{ php }} vendor/bin/phpcs -q
        # PHP's default 128 MB is too small once the WordPress stubs load; the
        # PHPStan worker peaked at 270 MB on 2026-10-09, so the limit is lifted.
        {{ php }} vendor/bin/phpstan analyse --no-progress --memory-limit=-1
    done

[private]
php-test: php-install
    #!/usr/bin/env bash
    set -euo pipefail
    for plugin in {{ plugins }}; do
        echo "== $plugin: PHPUnit"
        cd "{{ justfile_directory() }}/plugins/$plugin"
        {{ php }} vendor/bin/phpunit
    done

# Installs node_modules from package-lock.json, unless the last install is newer than the lock file.
[private]
[working-directory("plugins/linker-tools")]
js-install:
    if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then npm ci --no-audit --no-fund; fi

[private]
[working-directory("plugins/linker-tools")]
js-check: js-install
    npm run lint:js
    npm run lint:types
    npm run lint:format

[private]
[working-directory("plugins/linker-tools")]
js-test: js-install
    npm run test:unit
    npx playwright install --only-shell chromium
    npm run test:e2e

[private]
py-check:
    #!/usr/bin/env bash
    set -euo pipefail
    for service in {{ services }}; do
        echo "== $service: Ruff, mypy"
        cd "{{ justfile_directory() }}/services/$service"
        uv run --locked ruff check .
        uv run --locked ruff format --check .
        uv run --locked mypy src tests
    done

[private]
py-test:
    #!/usr/bin/env bash
    set -euo pipefail
    for service in {{ services }}; do
        echo "== $service: pytest"
        cd "{{ justfile_directory() }}/services/$service"
        uv run --locked pytest
    done
