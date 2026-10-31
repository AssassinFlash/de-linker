# de-linker tasks. Toolchains, versions and setup: README.md.

set shell := ["bash", "-euo", "pipefail", "-c"]

# `just build` and `just build::check`.
mod build "tools/build.just"

# Composer projects: the plugins, the production mu-plugins, and tools/local for
# its local mu-plugins and router.
js_projects := "plugins/linker-tools plugins/linker-commerce apps/planner"

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

# CI's strict commerce scope reuses a proven unchanged base. This recipe keeps
# the entire commerce source/unit surface, rather than selecting assertions.
commerce-check: german-copy internal-home-urls i18n-coverage i18n-validity
    #!/usr/bin/env bash
    set -euo pipefail
    python3 -m unittest discover -s "{{ justfile_directory() }}/tools/checks" -p "test_ci_*.py"
    cd "{{ justfile_directory() }}/plugins/linker-commerce"
    {{ php }} "$(command -v composer)" validate --no-check-publish
    {{ php }} "$(command -v composer)" install --no-interaction --no-progress --quiet
    {{ php }} vendor/bin/phpcs -q
    {{ php }} vendor/bin/phpstan analyse --no-progress --memory-limit=-1
    {{ php }} vendor/bin/phpunit
    npm ci --no-audit --no-fund
    npm run lint:js
    npm run lint:types
    npm run lint:format
    npm run test:unit
    # Existing plain-script tests resolve jsdom from linker-tools explicitly.
    (cd ../linker-tools && npm ci --no-audit --no-fund)
    node --test tests/js/*.test.mjs

# CI's presentation scope: existing presentation surfaces only. The workflow
# and the local preflight call this same recipe, so both apply the same guards.
ci-presentation:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}/plugins/linker-commerce"
    {{ php }} "$(command -v composer)" validate --no-check-publish
    {{ php }} "$(command -v composer)" install --no-interaction --no-progress --quiet
    if [ "${PHP_TEST_CHANGED:-false}" = true ]; then
        {{ php }} vendor/bin/phpcs -q tests/php/Unit/Presentation/TemplatesTest.php
        {{ php }} vendor/bin/phpstan analyse --no-progress --memory-limit=-1 tests/php/Unit/Presentation/TemplatesTest.php
    fi
    {{ php }} vendor/bin/phpunit tests/php/Unit/Presentation
    if [ "${CATALOG_CHANGED:-false}" = true ]; then
        python3 "{{ justfile_directory() }}/tools/checks/german-copy.py"
        python3 "{{ justfile_directory() }}/tools/checks/internal-home-urls.py" --root "{{ justfile_directory() }}"
        (cd "{{ justfile_directory() }}" && python3 tools/checks/i18n-coverage.py)
    fi

# Fast, source-only gates shared by CI and the local preflight.
ci-content:
    python3 -m unittest discover -s "{{ justfile_directory() }}/tools/checks" -p "test_ci_*.py"
    just --justfile "{{ justfile() }}" pull::check
    just --justfile "{{ justfile() }}" cutover::check
    just --justfile "{{ justfile() }}" german-copy
    just --justfile "{{ justfile() }}" internal-home-urls
    just --justfile "{{ justfile() }}" i18n-coverage
    just --justfile "{{ justfile() }}" i18n-validity

# Reproduce the affected CI lanes locally before a push. Runtime changes also
# run the complete native set against the reusable `ci_preflight` instance.
[group('check')]
ci-preflight *args:
    python3 "{{ justfile_directory() }}/tools/checks/ci_preflight.py" {{ args }}

# A fresh build must reproduce the committed artifacts byte for byte.
ci-build:
    just --justfile "{{ justfile() }}" js-install
    just --justfile "{{ justfile() }}" build::check
    just --justfile "{{ justfile() }}" build
    git status --porcelain -- plugins/linker-tools/build plugins/linker-commerce/build
    test -z "$(git status --porcelain -- plugins/linker-tools/build plugins/linker-commerce/build)"

# Shared package lanes keep local preflight and hosted CI on the same commands.
ci-planner: ci-planner-deps
    #!/usr/bin/env bash
    set -euo pipefail
    root="{{ justfile_directory() }}"
    cd "$root/apps/planner"
    npm run lint:js
    npm run lint:types
    npm run lint:format
    npm test
    npm run build
    node ../../plugins/linker-tools/bin/build-manifest.mjs write
    git diff --exit-code -- ../../plugins/linker-tools/build/planner ../../plugins/linker-tools/build/manifest.json
    npm run build:check
    node ../../plugins/linker-tools/bin/build-manifest.mjs check
    if [ "${PLANNER_BUILD_CHANGED:-false}" = true ]; then
        cd "$root/plugins/linker-tools"
        {{ php }} "$(command -v composer)" validate --no-check-publish
        {{ php }} "$(command -v composer)" install --no-interaction --no-progress --quiet
        {{ php }} vendor/bin/phpunit tests/php/Unit/PlannerApplicationTest.php
    fi

ci-engine: ci-planner-deps
    just --justfile "{{ justfile() }}" ci-service engine

[private]
[working-directory("apps/planner")]
ci-planner-deps:
    if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ] || [ package.json -nt node_modules/.package-lock.json ]; then npm ci --no-audit --no-fund; fi

ci-genie:
    just --justfile "{{ justfile() }}" ci-service genie

[private]
ci-service service:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}/services/{{ service }}"
    uv run --locked ruff check .
    uv run --locked ruff format --check .
    uv run --locked mypy .
    uv run --locked pytest

# Native integration groups. CI runs one group per matrix job; the local
# preflight runs them in sequence against its one reusable instance.
[positional-arguments]
ci-native groups name:
    #!/usr/bin/env bash
    set -euo pipefail
    root="{{ justfile_directory() }}"
    groups="$1"
    name="$2"
    wordpress="$HOME/de-linker-local/$name/wordpress"
    export PHP="{{ php }}"
    ensure_i18n() {
        just --justfile "$root/justfile" wp "$name" linker-i18n setup --user=local-admin
    }
    run_core() {
        just --justfile "$root/justfile" mu-smoke "$name"
        just --justfile "$root/justfile" genie-concurrency "$name"
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter 'ReviewReminderTest|PublicationHooksTest|MailBudgetRollbackTest|MailBudgetTest|InternalSmtpTest|NotificationRoutingTest|MailRetryTest|DigestTest|HealthMonitorTest|LanguageLinksInMailTest|MessageIdWitnessTest')
    }
    run_mail() {
        local filter='GlobalBusinessCapacityTest|SummaryEnvelopeTest|BusinessDispositionTest|MailCapacityTest|AtomicMailConnectionTest|ConnectionFenceTest|CriticalNotificationCapacityTest|VatNotificationCapacityTest|ConversationConfirmationCapacityTest|RegistrationCapacityTest|PreSendAuthorizationTest|ReviewReminderTest'
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter "$filter")
        just --justfile "$root/justfile" wp "$name" wc hpos sync --user=1
        just --justfile "$root/justfile" wp "$name" option update woocommerce_custom_orders_table_enabled yes
        just --justfile "$root/justfile" wp "$name" option update woocommerce_hpos_datastore_caching_enabled yes
        just --justfile "$root/justfile" wp "$name" option update woocommerce_feature_product_instance_caching_enabled yes
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter "$filter")
    }
    run_inquiry() {
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter 'PublicControllerTest|PublicLedgerTest|PublicVerificationTest|PublicProofTest|PublicAdmissionOwnersTest|BusinessPolicyTest|BusinessAdmissionTest')
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter InquiryStatusRestTest)
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter ReadSolutionRestTest)
        just --justfile "$root/justfile" page-cache-chain "$name"
        (cd "$root/plugins/linker-tools" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter DynamicPageCacheTest)
        if ! command -v pdftotext >/dev/null; then
            echo "pdftotext is required for the Proforma price-gate test" >&2
            exit 1
        fi
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter ProformaPriceGateTest)
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter GenieInquiryTest)
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter 'PreSendAuthorizationTest|InquiryAssessmentTest|CustomerEvidenceTest|CustomerReviewTest|NotificationHoldTest|AssessmentAsyncTest|SafeIntakeTest')
    }
    run_inventory() {
        cd "$root"
        uv run --locked --project tools/local ruff check --config tools/local/pyproject.toml tools/checks/inventory-access.py
        uv run --locked --project tools/local ruff format --check --config tools/local/pyproject.toml tools/checks/inventory-access.py
        uv run --locked --project tools/local mypy --strict tools/checks/inventory-access.py
        just --justfile "$root/justfile" inventory-access "$name"
    }
    run_runtime() {
        if ! just --justfile "$root/justfile" wp "$name" config get LINKER_GENIE_SERVICE_TOKEN --type=constant >/dev/null; then
            just --justfile "$root/justfile" wp "$name" config set LINKER_GENIE_SERVICE_TOKEN "$({{ php }} -r 'echo bin2hex(random_bytes(32));')" --type=constant --quiet
        fi
        just --justfile "$root/justfile" wp "$name" option update linker_engine_url http://127.0.0.1:9
        just --justfile "$root/justfile" wp "$name" option update linker_genie_url http://127.0.0.1:9
        (cd "$root/plugins/linker-tools" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter ResourceAdmissionTest)
        (cd "$root/plugins/linker-commerce" && LINKER_WP_ROOT="$wordpress" {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist --filter PublicationPreparationRecipeTest)
    }
    run_admin() {
        cd "$root"
        if ! command -v msgcat >/dev/null; then
            echo "gettext is required for the administrator MFA test" >&2
            exit 1
        fi
        uv run --locked --project tools/local ruff check --config tools/local/pyproject.toml tools/checks/admin-mfa.py
        uv run --locked --project tools/local ruff format --check --config tools/local/pyproject.toml tools/checks/admin-mfa.py
        uv run --locked --project tools/local mypy --strict tools/checks/admin-mfa.py
        # Offline MFA regressions already run in the Python tools lane.
        {{ php }} plugins/linker-commerce/vendor/bin/phpcs --standard=plugins/linker-commerce/phpcs.xml.dist tests/e2e/fixtures/admin-mfa.php tests/e2e/fixtures/admin-mfa-public.php
        just --justfile "$root/justfile" admin-mfa "$name" --prepare
    }
    ensure_i18n
    case "$groups" in
        all) run_core; run_mail; run_inquiry; run_inventory; run_runtime; run_admin ;;
        core) run_core ;;
        mail) run_mail ;;
        inquiry) run_inquiry ;;
        inventory) run_inventory ;;
        runtime) run_runtime ;;
        admin) run_admin ;;
        *) echo "unknown native group: $groups (expected all|core|mail|inquiry|inventory|runtime|admin)" >&2; exit 2 ;;
    esac

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

# Permanent retirement is read-only by default; pass --write after evidence decisions.
[positional-arguments]
retire name *options:
    PHP={{ php }} {{ linker_local }} retire "$@"

# Print a one-time login link: ten minutes, one use (--user <login>, default local-admin).
[positional-arguments]
login name *options:
    PHP={{ php }} {{ linker_local }} login "$@"

# List the instances.
status:
    PHP={{ php }} {{ linker_local }} status

# (Re)start owned services; --service engine leaves Genie running.
[positional-arguments]
serve name *options:
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

# Native administrator MFA acceptance with synthetic identities and local mail.
# --prepare installs/verifies the pinned official plugin and German language pack.
[positional-arguments]
admin-mfa name *options:
    PHP={{ php }} uv run --locked --project tools/local python tools/checks/admin-mfa.py "$@"
# Native synthetic credential authentication and complete inventory pagination.
[positional-arguments]
inventory-access name *options:
    PHP={{ php }} uv run --locked --project tools/local python tools/checks/inventory-access.py "$@"

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
    if [ "${LINKER_CI_PHP_READY:-false}" = true ]; then exit 0; fi
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

# Genie concurrency on a real instance (`just up <name>` first): two processes
# commit one conversation, and two cold entry-context callers converge on one
# browser scope under a held lock. CI runs this in the mu-smoke job.
[positional-arguments]
genie-concurrency name:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}/plugins/linker-tools"
    LINKER_WP_ROOT="$HOME/de-linker-local/{{ name }}/wordpress" \
        {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist \
        --filter 'ConversationConcurrencyTest|EntryScopeConcurrencyTest'

# A save drops the cached page on a real instance (`just up <name>` first):
# wp_update_post through wp_remote_post, the gate, and the next read, for a
# product, a blog post, and each German twin (#405, registered for #339).
# CI runs this in the mu-smoke job. The recipe configures Polylang when the
# instance does not have en and de yet.
[positional-arguments]
page-cache-chain name:
    #!/usr/bin/env bash
    set -euo pipefail
    # PageCache reads LINKER_GENIE_SERVICE_TOKEN when WordPress loads. `just up`
    # does not write it; `just serve` does. Make it here so the chain does not skip.
    if ! PHP={{ php }} {{ linker_local }} wp "$1" config get LINKER_GENIE_SERVICE_TOKEN --type=constant >/dev/null; then
        PHP={{ php }} {{ linker_local }} wp "$1" config set LINKER_GENIE_SERVICE_TOKEN "$({{ php }} -r 'echo bin2hex(random_bytes(32));')" --type=constant --quiet
    fi
    PHP={{ php }} {{ linker_local }} wp "$1" linker-i18n setup --user=local-admin
    cd "{{ justfile_directory() }}/plugins/linker-tools"
    LINKER_WP_ROOT="$HOME/de-linker-local/$1/wordpress" \
        {{ php }} vendor/bin/phpunit -c phpunit.integration.xml.dist \
        --filter PageCacheChainTest

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
    # Unit tests also launch Chromium; install before the first consumer.
    npx playwright install --only-shell chromium
    npm run test:unit
    cd "{{ justfile_directory() }}/plugins/linker-commerce" && npm run test:unit
    cd "{{ justfile_directory() }}/apps/planner" && npm test
    # The commerce plugins' script tests are plain node:test files (jsdom
    # resolves through this project's node_modules); this gate is what runs
    # them in CI.
    node --test "../../plugins/linker-commerce/tests/js/*.test.mjs"
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
[positional-arguments]
py-test-group group:
    #!/usr/bin/env bash
    set -euo pipefail
    case "$1" in
        genie) projects=(services/genie) ;;
        engine) projects=(services/engine) ;;
        tools) projects=(tools/local tools/migrate) ;;
        harnesses) projects=(tools/faq docs/research/2026-10-20-campaign-330/harness docs/research/2026-10-20-campaign-332/harness docs/research/2026-10-20-campaign-333/harness docs/research/2026-10-20-campaign-334/harness docs/research/2026-10-20-campaign-335/harness) ;;
        *) echo "unknown Python test group: $1" >&2; exit 2 ;;
    esac
    for project in "${projects[@]}"; do
        echo "== $project: pytest"
        cd "{{ justfile_directory() }}/$project"
        # tools/local's stack tests build real instances with this PHP.
        PHP={{ php }} uv run --locked pytest
    done

[private]
py-test:
    just --justfile "{{ justfile() }}" py-test-group genie
    just --justfile "{{ justfile() }}" py-test-group engine
    just --justfile "{{ justfile() }}" py-test-group tools
    just --justfile "{{ justfile() }}" py-test-group harnesses

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
    python3 -m unittest discover -s "{{ justfile_directory() }}/tools/checks" -p test_i18n_sources.py
    PHP={{ php }} python3 "{{ justfile_directory() }}/tools/checks/i18n-coverage.py"

# Rebuild commerce catalogs from PHP/JS/build and live catalog strings in LC
# fragments, retaining the explicitly listed published identifiers. Code and
# fragments are extracted fresh; no previous generated POT is merged.
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
    msgcat --use-first --sort-by-file "$extraction/code.pot" "$extraction/fragments.pot" \
        "$plugin/languages/linker-commerce-published.pot" -o "$catalogs.pot"
    msgmerge --update --backup=none --no-fuzzy-matching "$catalogs-de_DE_formal.po" "$catalogs.pot"
    {{ php }} "$(command -v wp)" i18n make-json "$catalogs-de_DE_formal.po" --no-purge
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
