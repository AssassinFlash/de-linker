# de-linker tasks. Toolchains, versions and setup: README.md.

set shell := ["bash", "-euo", "pipefail", "-c"]

# `just build` and `just build::check`.
mod build "tools/build.just"

# Composer projects: the plugins, the production mu-plugins, and tools/local for
# its local mu-plugins and router.
js_projects := "plugins/linker-tools plugins/linker-commerce"

php_projects := "plugins/linker-commerce plugins/linker-i18n plugins/linker-tools mu-plugins tools/local"

# uv projects: the services, tools/local (linker-local), the data migrations (tools/migrate),
# the FAQ tooling, and the campaign harnesses (each its own uv project, package = false).
py_projects := "services/genie services/engine tools/local tools/migrate tools/faq docs/research/2026-10-20-campaign-330/harness docs/research/2026-10-20-campaign-332/harness docs/research/2026-10-20-campaign-333/harness docs/research/2026-10-20-campaign-334/harness docs/research/2026-10-20-campaign-335/harness"

# `just pull` takes a snapshot of the live site; `just pull load|diff|scan|…`
# (tools/pull/pull.just, docs/specs/6-live-pull.md).
mod pull "tools/pull/pull.just"

# `just cutover …` is the one-time switch onto the new tree, and `just cutover
# drill <instance>` rehearses it locally (tools/cutover/cutover.just,
# docs/specs/17-cutover.md).
mod cutover "tools/cutover/cutover.just"

# The PHP tools run on PHP 8.3, the production host's version
# (docs/research/2026-10-09/framework-choice.md §2): Homebrew's php@8.3 when it
# is installed, otherwise `php` on PATH (CI). `PHP=/path/to/php just …` wins.
php := env("PHP", if path_exists("/opt/homebrew/opt/php@8.3/bin/php") == "true" { "/opt/homebrew/opt/php@8.3/bin/php" } else { "php" })

# List the recipes.
default:
    @just --list --list-submodules

# Lint and static analysis of every chain, and the build/ manifest.
check: php-check js-check e2e-check py-check pull::check cutover::check german-copy internal-home-urls i18n-coverage i18n-validity build::check

# Unit tests of every chain and the end-to-end tests.
test: php-test js-test py-test pull::test cutover::test

# The regression suite of the review site (tests/e2e, docs/specs/16-review-acceptance.md):
# Playwright over a running instance — `just e2e <name>` after `just up <name>`,
# the snapshot and `just serve <name>`. Extra arguments go to `playwright test`.
[positional-arguments]
e2e name *args:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}/tests/e2e"
    if [ ! -d node_modules ]; then npm ci --no-audit --no-fund; fi
    # positional-arguments leaves the instance name in $1; only the rest is a filter.
    LINKER_E2E_INSTANCE="{{ name }}" npx playwright test "${@:2}"

# Local WordPress instances (docs/local-stack.md): `up` creates the instance on
# first use, then (re)starts it with this checkout's plugins.
linker_local := "uv run --locked --project tools/local linker-local"

# Create the instance if needed, then (re)start it; --snapshot <dir> installs a snapshot's plugins and uploads.
[positional-arguments]
up name *options: php-install
    PHP={{ php }} {{ linker_local }} up "$@"

# One command from live to a local instance (#252, docs/specs/6-live-pull.md):
# create or restart <name> with this checkout, take a fresh snapshot of
# de-linker.com and load it — licences applied, the snapshot's time in
# `just status`. Extra options go to `just pull load` (e.g. --live-code).
[positional-arguments]
sync name *options:
    #!/usr/bin/env bash
    set -euo pipefail
    just up "$1"
    just pull
    just pull load "$@" latest

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

# The mock ERP (ticket #69, docs/specs/69-stock.md): sets a fresh push key on
# the instance, picks two stock-managed products with SKUs, and drives the
# scripted push sequence (normal / out of stock / recovery) at
# linker/v1/stock, asserting the visible chain: the catalogue's in-stock
# badge, the in-stock-only listing and the solution draft gate. Needs the
# instance up with the live snapshot (`just pull load <name> … --live-code`).
# Re-runnable; it leaves the products in stock and the channel dormant: the
# key it set is removed again at the end.
[positional-arguments]
mock-erp name:
    #!/usr/bin/env bash
    set -euo pipefail
    name="$1"
    port="$(awk -v name="$name" '$0 == "[" name "]" { seen = 1; next } seen && $1 == "port" { print $3; exit }' "$HOME/de-linker-local/instances.toml")"
    if [ -z "$port" ]; then
        echo "no instance '$name' in ~/de-linker-local/instances.toml: just up $name first" >&2
        exit 1
    fi
    base="http://127.0.0.1:${port}"
    if ! curl -fsS -o /dev/null --max-time 5 "$base/wp-json/"; then
        echo "$base does not answer: just up $name first" >&2
        exit 1
    fi
    admin="$(PHP={{ php }} {{ linker_local }} wp "$name" user list --role=administrator --field=user_login | tail -n 1)"
    key="$(openssl rand -hex 32)"
    PHP={{ php }} {{ linker_local }} wp "$name" linker-commerce stock-key --set="$key" --user="$admin"
    payload="$(PHP={{ php }} {{ linker_local }} wp "$name" eval '
        // Bind two subjects of one small product category: the ERP pushes
        // quantities, and WooCommerce carries quantities only on products
        // with managed stock (the endpoint answers not_stock_managed
        // otherwise). Local instance, so the write is the mock world'"'"'s
        // own. The category is the assertion'"'"'s catalogue page: at most
        // sixteen products, so the archive shows them all on one page.
        $best = null;
        foreach ( get_terms( array( "taxonomy" => "product_cat", "hide_empty" => true ) ) as $term ) {
            if ( is_wp_error( $term ) || (int) $term->count < 2 || (int) $term->count > 16 ) { continue; }
            if ( null === $best || (int) $term->count < (int) $best->count ) { $best = $term; }
        }
        if ( null === $best ) { echo json_encode( array( "products" => array() ) ); return; }
        $listing = is_string( get_term_link( $best ) ) ? get_term_link( $best ) : wc_get_page_permalink( "shop" );
        $products = array();
        foreach ( get_posts( array( "post_type" => "product", "post_status" => "publish", "posts_per_page" => 2, "fields" => "ids", "orderby" => "menu_order title", "order" => "ASC", "tax_query" => array( array( "taxonomy" => "product_cat", "field" => "term_id", "terms" => $best->term_id ) ) ) ) as $product_id ) {
            $product = wc_get_product( $product_id );
            $sku = $product ? $product->get_sku() : "";
            if ( "" === $sku ) { continue; }
            if ( ! $product->managing_stock() ) {
                $product->set_manage_stock( true );
                $product->set_stock_quantity( 7 );
                $product->save();
            }
            $products[ $sku ] = array( "id" => $product->get_id(), "url" => $product->get_permalink(), "listing" => $listing );
        }
        echo json_encode( array( "products" => $products ) );
    ')"
    # The channel ships dormant and the mock's key was this run's alone:
    # take it back out even when the mock fails, so the instance is left
    # exactly as the cutover finds it.
    cleanup() {
        PHP={{ php }} {{ linker_local }} wp "$name" linker-commerce stock-key --clear --user="$admin"
    }
    trap cleanup EXIT
    python3 "{{ justfile_directory() }}/tools/mock_erp.py" --base "$base" --key "$key" --payload "$payload"

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
# one from before, and the templates' and the entries' anchor classes must be in
# the product. `just windpress-compile <instance>` after every content-changing
# round.
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
    # The anchor-class check is the plugins' own (WindPressCache::missing_anchor_classes
    # for the templates, Linker\Tools\Genie\WindPress::missing_anchor_classes for the
    # entries' ask chip), so the recipe fails on exactly the classes they need.
    missing="$(PHP={{ php }} {{ linker_local }} wp "$name" eval '$css = (string) @file_get_contents( wp_upload_dir()["basedir"] . "/windpress/cache/tailwind.css" ); echo json_encode( array_merge( ( new Linker\Commerce\Presentation\WindPressCache() )->missing_anchor_classes( $css ), ( new Linker\Tools\Genie\WindPress() )->missing_anchor_classes( $css ) ) );' | tail -n 1)"
    if [ "$missing" != "[]" ]; then
        echo "windpress: the compiled cache misses the templates' or the entries' anchor classes: $missing" >&2
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
        # instances by its pytest stack tests. Every other project must have one
        # (mu-plugins' smoke test runs against an instance, LINKER_MU_WP).
        if [ "$project" = tools/local ]; then continue; fi
        echo "== $project: PHPUnit"
        cd "{{ justfile_directory() }}/$project"
        {{ php }} vendor/bin/phpunit
    done

# The must-use plugins' smoke suite against a real instance (`just up <name>`
# first): the guards' headers and closed REST user list, the recorder's file,
# the engine pin's installation. LINKER_MU_WP is wired to the repo's WP-CLI
# entry, `just wp <name>`; CI runs this recipe against an instance it builds
# (.github/workflows/check.yml, the mu-smoke job).
[positional-arguments]
mu-smoke name:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}/mu-plugins"
    LINKER_MU_WP="just wp {{ name }}" PHP={{ php }} {{ php }} vendor/bin/phpunit --testsuite integration

# Two processes commit one Genie conversation on a real instance
# (`just up <name>` first). The overlap case asserts the lock intervals,
# not only the final transcript (#373). CI runs this in the mu-smoke job.
[positional-arguments]
genie-concurrency name:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}/plugins/linker-tools"
    LINKER_WP_ROOT="$HOME/de-linker-local/{{ name }}/wordpress" \
        {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist \
        --filter ConversationConcurrencyTest

# Installs node_modules from package-lock.json, unless the last install is newer than the lock file.
[private]
js-install:
    #!/usr/bin/env bash
    set -euo pipefail
    for project in {{ js_projects }}; do
        cd "{{ justfile_directory() }}/$project"
        if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then npm ci --no-audit --no-fund; fi
    done

# The regression suite's own package: types and formatting. Its tests need a
# live instance, so they are not part of `just check`; this is what CI can run.
[private]
[working-directory("tests/e2e")]
e2e-install:
    if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then npm ci --no-audit --no-fund; fi

[private]
e2e-check: e2e-install
    cd "{{ justfile_directory() }}/tests/e2e" && npm run lint:types && npm run lint:format

[private]
js-check: js-install
    #!/usr/bin/env bash
    set -euo pipefail
    for project in {{ js_projects }}; do
        cd "{{ justfile_directory() }}/$project"
        npm run lint:js
        npm run lint:types
        npm run lint:format
    done

[private]
[working-directory("plugins/linker-tools")]
js-test: js-install
    npm run test:unit
    cd "{{ justfile_directory() }}/plugins/linker-commerce" && npm run test:unit
    # The commerce plugins' script tests are plain node:test files (jsdom
    # resolves through this project's node_modules); this gate is what runs
    # them in CI.
    node --test "../../plugins/linker-commerce/tests/js/*.test.mjs"
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
    # #297: the SMTP sink is a PHP integration fixture, so include it explicitly.
    cd "{{ justfile_directory() }}/tools/local"
    uv run --locked ruff check ../../plugins/linker-commerce/tests/fixtures/smtp_sink.py
    uv run --locked ruff format --check ../../plugins/linker-commerce/tests/fixtures/smtp_sink.py
    uv run --locked mypy --strict ../../plugins/linker-commerce/tests/fixtures/smtp_sink.py

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

# German copy gate (#265, owner rulings): the banned-word vocabulary (one
# list, plugins/linker-i18n/data/banned-de.json — the same list the
# auto-translation enforces on database content), the du form, English date
# formats and the blog "Artikel" word, over every German surface the
# repository ships: .po msgstr, generated JSON, German LiveCanvas exports
# and the reviewed journal titles. Absorbs the old inline catalogue grep
# (tools/checks/german-copy.py).
[group('check')]
german-copy:
    python3 "{{ justfile_directory() }}/tools/checks/german-copy.py"

# No plugin writes an English address of this site into its own markup
# (#263): home_url( '/…' ) is the root of H1/H5/M9; the language-aware entry
# point is PageUrls. Since #265 the same gate keeps the German LiveCanvas
# exports' literal hrefs German (/de/…) — audit M2 (tools/checks/
# internal-home-urls.py).
[group('check')]
internal-home-urls:
    python3 "{{ justfile_directory() }}/tools/checks/internal-home-urls.py" --root "{{ justfile_directory() }}"

# German formal catalogs: untranslated entries minus the developer-facing
# exemption list must be zero. linker-tools also checks source coverage and
# byte-for-byte JSON reproduction via WP-CLI (tools/checks/i18n-coverage.py).
[group('check')]
i18n-coverage:
    PHP={{ php }} python3 "{{ justfile_directory() }}/tools/checks/i18n-coverage.py"

# Rebuild commerce catalogs from PHP/JS/build and live catalog strings in LC
# fragments. Both input POTs are extracted fresh; no previous POT is merged.
[positional-arguments]
i18n-commerce name:
    #!/usr/bin/env bash
    set -euo pipefail
    plugin="{{ justfile_directory() }}/plugins/linker-commerce"
    catalogs="$plugin/languages/linker-commerce"
    extraction="$(mktemp -d)"
    trap 'rm -rf "$extraction"' EXIT
    PHP={{ php }} {{ linker_local }} wp "$1" i18n make-pot "$plugin" "$extraction/code.pot" \
        --domain=linker-commerce --include=linker-commerce.php,includes,templates,src,build \
        --exclude=vendor,node_modules,tests --skip-audit
    python3 "{{ justfile_directory() }}/tools/checks/i18n_sources.py" "$plugin" "$extraction/fragments.pot"
    msgcat --use-first --sort-by-file "$extraction/code.pot" "$extraction/fragments.pot" -o "$catalogs.pot"
    msgmerge --update --backup=none --no-fuzzy-matching "$catalogs-de_DE_formal.po" "$catalogs.pot"
    msgfmt --check "$catalogs-de_DE_formal.po" -o "$catalogs-de_DE_formal.mo"

# #302: the PO remains the authority for both scripts; no instance is needed.
# --no-purge preserves JS messages for subsequent extraction and regeneration.
[group('build')]
i18n-tools:
    {{ php }} "$(command -v wp)" i18n make-json "{{ justfile_directory() }}/plugins/linker-tools/languages/linker-tools-de_DE_formal.po" --no-purge
    msgfmt --check "{{ justfile_directory() }}/plugins/linker-tools/languages/linker-tools-de_DE_formal.po" -o "{{ justfile_directory() }}/plugins/linker-tools/languages/linker-tools-de_DE_formal.mo"

# Every catalog compiles: msgfmt --check over each plugin's .po and .pot
# (tools/checks/i18n-validity.py). The coverage gate above reads the German
# catalogs only, so a template catalog that lost a msgstr section or repeats
# a msgid would reach the trunk silently.
[group('check')]
i18n-validity:
    python3 "{{ justfile_directory() }}/tools/checks/i18n-validity.py"
