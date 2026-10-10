# de-linker tasks. Toolchains, versions and setup: README.md.

set shell := ["bash", "-euo", "pipefail", "-c"]

# `just build` and `just build::check`.
mod build "tools/build.just"

# Composer projects: the plugins, and tools/local for its mu-plugins and router.
php_projects := "plugins/linker-commerce plugins/linker-i18n plugins/linker-tools tools/local"

# uv projects: the services, tools/local (linker-local), the data migrations (tools/migrate), and the FAQ tooling.
py_projects := "services/genie services/engine tools/local tools/migrate tools/faq"

# `just pull` takes a snapshot of the live site; `just pull load|diff|scan|…`
# (tools/pull/pull.just, docs/specs/6-live-pull.md).
mod pull "tools/pull/pull.just"

# The PHP tools run on PHP 8.3, the production host's version
# (docs/research/2026-10-09/framework-choice.md §2): Homebrew's php@8.3 when it
# is installed, otherwise `php` on PATH (CI). `PHP=/path/to/php just …` wins.
php := env("PHP", if path_exists("/opt/homebrew/opt/php@8.3/bin/php") == "true" { "/opt/homebrew/opt/php@8.3/bin/php" } else { "php" })

# List the recipes.
default:
    @just --list --list-submodules

# Lint and static analysis of every chain, and the build/ manifest.
check: php-check js-check py-check pull::check build::check

# Unit tests of every chain and the end-to-end tests.
test: php-test js-test py-test pull::test

# Local WordPress instances (docs/local-stack.md): `up` creates the instance on
# first use, then (re)starts it with this checkout's plugins.
linker_local := "uv run --locked --project tools/local linker-local"

# Create the instance if needed, then (re)start it; --snapshot <dir> installs a snapshot's plugins and uploads.
[positional-arguments]
up name *options: php-install
    PHP={{ php }} {{ linker_local }} up "$@"

# Stop the instance's server and services.
[positional-arguments]
down name:
    PHP={{ php }} {{ linker_local }} down "$@"

# Delete the instance's database and files, then build it again.
[positional-arguments]
reset name *options: php-install
    PHP={{ php }} {{ linker_local }} reset "$@"

# Print a one-time login link: ten minutes, one use (--user <login>, default local-admin).
[positional-arguments]
login name *options:
    PHP={{ php }} {{ linker_local }} login "$@"

# List the instances.
status:
    PHP={{ php }} {{ linker_local }} status

# (Re)start the engine and Genie of the instance and write their addresses into it.
[positional-arguments]
serve name:
    PHP={{ php }} {{ linker_local }} serve "$@"

# Run WP-CLI against the instance, e.g. `just wp a plugin list`.
[positional-arguments]
wp name *args:
    PHP={{ php }} {{ linker_local }} wp "$@"

# docs/specs/10-knowledge-index.md; `just index --help` lists the options.
# Build Genie's document index on this Mac: hosted PDFs, Docling, chunks, vectors, SQLite.
[working-directory("services/genie")]
index *args:
    uv run --locked --group index python -m index.build {{ args }}

# Score the latest index build on the golden set: recall@5 and citation page accuracy.
[working-directory("services/genie")]
eval *args:
    uv run --locked --group index python -m index.eval.run {{ args }}

# Install LiveCanvas templates and Additional CSS tokens into an instance (idempotent).
[positional-arguments]
present name:
    PHP={{ php }} {{ linker_local }} wp "{{ name }}" linker-commerce present --user=1

# Recompile an instance's WindPress cache through its admin — the only compile
# that exists (Tailwind v4 has no server-side build): one-time login, WindPress
# → Settings → Performance → Generate, the stored cache must be newer than the
# one from before, and the templates' anchor classes must be in the product.
# `just windpress-compile <instance>` after every content-changing round.
[positional-arguments]
windpress-compile name *options:
    #!/usr/bin/env bash
    set -euo pipefail
    name="$1"; shift
    user=""
    for option in "$@"; do
        case "$option" in
            --user=*) user="${option#--user=}" ;;
            *) echo "unknown option: $option (supported: --user=<login>)" >&2; exit 2 ;;
        esac
    done
    if [ -z "$user" ]; then
        user="$(PHP={{ php }} {{ linker_local }} wp "$name" user list --role=administrator --field=user_login | tail -n 1 | head -n 1)"
        if [ -z "$user" ]; then
            echo "no administrator found on $name" >&2
            exit 1
        fi
    fi
    cache_php='echo (int) @filemtime( wp_upload_dir()["basedir"] . "/windpress/cache/tailwind.css" );'
    before="$(PHP={{ php }} {{ linker_local }} wp "$name" eval "$cache_php" | tail -n 1)"
    login_url="$(PHP={{ php }} {{ linker_local }} login "$name" --user="$user" | tail -n 1)"
    echo "windpress: compiling through the admin (user: $user, cache mtime before: $before)"
    # The compile runs in WindPress's browser-side worker; the recipe drives the
    # full chromium build (the headless shell alone is not what the admin ships).
    (cd "{{ justfile_directory() }}/plugins/linker-tools" && npx playwright install chromium)
    node "{{ justfile_directory() }}/tools/windpress-compile.mjs" "$login_url" "$before"
    after="$(PHP={{ php }} {{ linker_local }} wp "$name" eval "$cache_php" | tail -n 1)"
    if [ -z "$after" ] || [ "$after" -le "$before" ]; then
        echo "windpress: the cache file did not get newer ($before -> $after)" >&2
        exit 1
    fi
    # The anchor-class check is the plugin's own (WindPressCache::missing_anchor_classes),
    # so the recipe fails on exactly the classes the templates need.
    missing="$(PHP={{ php }} {{ linker_local }} wp "$name" eval 'echo json_encode( ( new Linker\Commerce\Presentation\WindPressCache() )->missing_anchor_classes( (string) @file_get_contents( wp_upload_dir()["basedir"] . "/windpress/cache/tailwind.css" ) ) );' | tail -n 1)"
    if [ "$missing" != "[]" ]; then
        echo "windpress: the compiled cache misses the templates' anchor classes: $missing" >&2
        exit 1
    fi
    echo "windpress: cache recompiled ($before -> $after), anchor classes present"

[private]
php-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! {{ php }} -r 'exit(PHP_MAJOR_VERSION === 8 && PHP_MINOR_VERSION === 3 ? 0 : 1);'; then
        echo "PHP 8.3 is required; {{ php }} is $({{ php }} -r 'echo PHP_VERSION;'). See README.md." >&2
        exit 1
    fi
    composer="$(command -v composer)"
    for project in {{ php_projects }}; do
        cd "{{ justfile_directory() }}/$project"
        # `composer install` only warns about a composer.lock that no longer
        # matches composer.json; `validate` fails, as `npm ci` and `uv --locked` do.
        {{ php }} "$composer" validate --no-check-publish
        {{ php }} "$composer" install --no-interaction --no-progress --quiet
    done

[private]
php-check: php-install
    #!/usr/bin/env bash
    set -euo pipefail
    for project in {{ php_projects }}; do
        echo "== $project: PHPCS, PHPStan"
        cd "{{ justfile_directory() }}/$project"
        {{ php }} vendor/bin/phpcs -q
        # PHP's default 128 MB is too small once the WordPress stubs load; the
        # PHPStan worker peaked at 270 MB on 2026-10-09, so the limit is lifted.
        {{ php }} vendor/bin/phpstan analyse --no-progress --memory-limit=-1
    done

[private]
php-test: php-install
    #!/usr/bin/env bash
    set -euo pipefail
    for project in {{ php_projects }}; do
        # tools/local has no PHPUnit suite: its mu-plugins are tested on real
        # instances by its pytest stack tests. Every other project must have one.
        if [ "$project" = tools/local ]; then continue; fi
        echo "== $project: PHPUnit"
        cd "{{ justfile_directory() }}/$project"
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
    for project in {{ py_projects }}; do
        echo "== $project: Ruff, mypy"
        cd "{{ justfile_directory() }}/$project"
        uv run --locked ruff check .
        uv run --locked ruff format --check .
        uv run --locked mypy .
    done

[private]
py-test:
    #!/usr/bin/env bash
    set -euo pipefail
    for project in {{ py_projects }}; do
        echo "== $project: pytest"
        cd "{{ justfile_directory() }}/$project"
        # tools/local's stack tests build real instances with this PHP.
        PHP={{ php }} uv run --locked pytest
    done
