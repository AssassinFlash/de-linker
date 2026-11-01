"""Select and audit CI package lanes from the actual Git diff."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

LANES = (
    "presentation",
    "php",
    "js",
    "python",
    "content",
    "build",
    "commerce",
    "native",
    "planner",
    "engine",
    "genie",
)
FULL_LANES = (
    "php",
    "js",
    "python",
    "content",
    "build",
    "native",
    "planner",
    "engine",
    "genie",
)
WORKFLOW = ".github/workflows/check.yml"

# Modules name complete package checks, not individual assertions. PHP clients
# retain native authority checks; compiled JS is reproduced only for JS inputs.
PHP_PROJECTS = {
    "commerce": "plugins/linker-commerce",
    "tools": "plugins/linker-tools",
    "i18n": "plugins/linker-i18n",
    "mu": "mu-plugins",
    "local": "tools/local",
}
PYTHON_PROJECTS = {
    "local": "tools/local",
    "migrate": "tools/migrate",
    "pull": "tools/pull",
    "cutover": "tools/cutover",
}
NATIVE_GROUPS = ("core", "mail", "inquiry", "inventory", "runtime", "admin")
MODULE_COMMANDS = {
    **{
        f"php:{name}": ("just", "ci-php-package", path)
        for name, path in PHP_PROJECTS.items()
    },
    **{
        f"js:{name}": ("just", "ci-js-package", name)
        for name in ("commerce", "tools", "e2e")
    },
    **{
        f"python:{name}": ("just", "ci-python-package", path)
        for name, path in PYTHON_PROJECTS.items()
    },
    "python:harnesses": ("just", "ci-python-harnesses"),
    **{
        f"build:{name}": ("just", "ci-build-package", name)
        for name in ("commerce", "tools")
    },
    **{
        f"native:{name}": ("just", "ci-native", name, "smoke") for name in NATIVE_GROUPS
    },
    **{
        name: ("just", "ci-" + name)
        for name in ("content", "presentation", "planner", "engine", "genie")
    },
}
FULL_MODULES = tuple(module for module in MODULE_COMMANDS if module != "presentation")
# Presentation still lacks a reconstructed diff-condition proof. Planner
# additionally verifies its native merge parents and conditional PHP check.
DIFF_GUARDED_MODULES = {"presentation"}
CONTROL_INPUTS = (
    WORKFLOW,
    "justfile",
    "tools/build.just",
    "tools/checks/ci_scope.py",
    "tools/checks/ci_preflight.py",
    "tools/checks/ci_phase.sh",
    "tools/checks/test_ci_scope.py",
    "tools/checks/test_ci_preflight.py",
    ".gitattributes",
    ".gitmodules",
    ".editorconfig",
)

# Docs are inputs only where a current check actually opens them. Reports and
# guidance must not invalidate an otherwise identical successful package run.
ENGINE_DOC_INPUTS = (
    "docs/research/2026-10-23-pv-inputs/raw/",
    "docs/research/2026-10-24-pv-generation/raw/",
)
GENIE_DOC_INPUTS = (
    "docs/research/2026-10-17-deepseek-flash-vision/raw/datasheet-probe.pdf",
    "docs/research/2026-10-20-campaign-330/harness/regrade.py",
    "docs/research/2026-10-20-campaign-330/harness/summary.py",
    "docs/research/2026-10-20-campaign-330/harness/fixtures/339/manifest.json",
    "docs/research/2026-10-20-campaign-330/harness/fixtures/certificate/esa-5-30kw-rated-output.txt",
    "docs/research/2026-10-20-campaign-330/round3-runs.jsonl",
    "docs/research/2026-10-20-campaign-330/verdicts.jsonl",
    "docs/research/2026-10-20-campaign-334/harness/grade.py",
    "docs/research/2026-10-20-campaign-334/harness/poison.py",
    "docs/acceptance/2026-10-20/339/case-map.md",
    "docs/acceptance/2026-10-20/405/cases.md",
)
HARNESS_EXTERNAL_INPUTS = (
    "docs/research/2026-10-20-campaign-330/verdicts.jsonl",
    "docs/research/2026-10-20-campaign-330/round3-runs.jsonl",
    "docs/research/2026-10-20-campaign-332/verdicts.jsonl",
    "docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png",
    "services/genie/eval/attachments/photos/goodwe-gw10k-et.jpg",
)
MIGRATE_DOC_INPUTS = (
    "docs/faq/goodwe-gw60k-sts-g10.json",
    "docs/debt/DE-PARITY-2026-10-13.md",
)
# local's real release test imports this current, stdlib-only engine guard.
LOCAL_ENGINE_INPUTS = (
    "services/engine/src/linker_engine/__init__.py",
    "services/engine/src/linker_engine/planning/__init__.py",
    "services/engine/src/linker_engine/planning/project_input_floor.py",
    "services/engine/src/linker_engine/planning/project_input_contracts.py",
)
LOCAL_PREFLIGHT_INPUTS = (
    "tools/local/src/linker_local/__init__.py",
    "tools/local/src/linker_local/instance.py",
    "tools/local/src/linker_local/registry.py",
    "tools/local/src/linker_local/processes.py",
)

# Engine's browser contract tests execute Planner domain/data modules via Node;
# npm ci also runs the package's postinstall. Keep those inputs in both the
# selection and proof, alongside the schemas and shared fixture families.
ENGINE_PLANNER_INPUTS = (
    "apps/planner/src/domain/",
    "apps/planner/src/data/",
    "apps/planner/src/contracts/",
    "apps/planner/tests/fixtures/",
    "apps/planner/package.json",
    "apps/planner/package-lock.json",
    "apps/planner/bin/echarts-types.mjs",
)
ENGINE_PUBLICATION_INPUTS = (
    "plugins/linker-commerce/includes/Products/Publication.php",
    "plugins/linker-commerce/includes/Products/Publication/",
)
GENIE_COMMERCE_INPUTS = (
    "plugins/linker-commerce/includes/Abilities/",
    "plugins/linker-commerce/includes/Products/SelectionFacts.php",
    *ENGINE_PUBLICATION_INPUTS,
)
CABLE_ADOPTION = "plugins/linker-commerce/data/cable-references.json"
COMMERCE_COMPATIBILITY = "plugins/linker-commerce/data/compatibility.json"
PLANNER_CHUNK = re.compile(
    r"plugins/linker-tools/build/planner/assets/([A-Za-z0-9_-]+)-[A-Za-z0-9_-]{8}\.js"
)
ENGINE_TOOLS_SCHEMAS = "plugins/linker-tools/src/configurator/schema/"


def under(path, roots):
    return any(
        path == root or path.startswith(root.rstrip("/") + "/") for root in roots
    )


def engine_planner_input(path):
    # Engine invokes specific runtime modules with Node, not Planner's separate
    # `node --test` entrypoints. Keep the naming rule shared by picker/proof.
    if path.startswith("apps/planner/src/") and re.search(
        r"\.test\.[cm]?[jt]sx?$", path
    ):
        return False
    return under(path, ENGINE_PLANNER_INPUTS)


def local_test_module(path):
    return (
        path.startswith("tools/local/tests/")
        and path.rsplit("/", 1)[-1].startswith("test_")
        and path.endswith(".py")
    )


def commerce_migration_input(path):
    # PHP analyzers visit migration PHP and the Commerce fixture reads migration
    # data; the Python CLI and its tests have their own migration lane.
    return path.startswith("tools/migrate/") and not path.endswith(".py")


def fixture_consumers(path):
    modules: set[str] = set()
    if under(path, ENGINE_DOC_INPUTS):
        modules.update(("engine", "planner"))
    if under(path, GENIE_DOC_INPUTS):
        modules.add("genie")
    if under(path, MIGRATE_DOC_INPUTS):
        modules.add("python:migrate")
    if under(path, HARNESS_EXTERNAL_INPUTS):
        modules.add("python:harnesses")
    # These existing Python packages also exercise their own harness sources.
    if re.match(
        r"docs/research/2026-10-20-campaign-\d+/harness/", path
    ) and not path.endswith((".md", ".rst", ".txt")):
        modules.add("python:harnesses")
    return modules


def non_runtime_path(path):
    return (document(path) or acceptance_record(path)) and not fixture_consumers(path)


def module_lane(module):
    return module.split(":", 1)[0]


def selected_modules(changes, base="", head=""):
    """Known package/dependency union; None means shared/structural fallback."""
    if not changes or any(status not in {"A", "M", "D"} for status, _ in changes):
        return None
    if any(
        not (
            non_runtime_change(status, path, base, head)
            if document(path) or acceptance_record(path)
            else regular_change(status, path, base, head)
        )
        for status, path in changes
    ):
        return None
    runtime = [(status, path) for status, path in changes if not non_runtime_path(path)]
    if not runtime:
        return []
    if all(status == "M" and presentation(path) for status, path in runtime):
        return ["presentation"]
    selected = set()
    native = {"native:" + name for name in NATIVE_GROUPS}
    planner_changed = any(
        path.startswith(("apps/planner/", "plugins/linker-tools/build/planner/"))
        for _, path in runtime
    )
    for _status, path in runtime:
        consumers = fixture_consumers(path)
        selected.update(consumers)
        if consumers and path.startswith("docs/"):
            continue
        if path in CONTROL_INPUTS or path.startswith(".github/"):
            return None
        if path.startswith(("apps/planner/", "plugins/linker-tools/build/planner/")):
            selected.add("planner")
            # Native Engine contracts read browser schemas and shared fixtures
            # directly, beyond the solar preparation-flow fixture family.
            if engine_planner_input(path):
                selected.add("engine")
        elif path == "plugins/linker-tools/build/manifest.json":
            if planner_changed and planner_manifest_isolated(base, head):
                if not tools_manifest_matches_changes(changes, base, head):
                    return None
                continue
            if not tools_manifest_matches_changes(changes, base, head):
                return None
            # The Tools build lane independently checks and reproduces its
            # committed manifest. Keep the same consumers as other Tools builds.
            selected.update(("js:tools", "build:tools", "php:tools"))
            selected.update(native)
        elif path.startswith("services/engine/"):
            selected.add("engine")
            if under(path, LOCAL_ENGINE_INPUTS):
                selected.add("python:local")
            if path.startswith("services/engine/tests/fixtures/"):
                selected.update(("genie", "php:commerce", "php:tools"))
            if path.startswith("services/engine/schemas/"):
                selected.add("planner")
            if path.endswith("/assistant_context.py"):
                selected.add("genie")
        elif path.startswith("services/genie/"):
            selected.add("genie")
            if path.startswith("services/genie/tests/fixtures/"):
                selected.update(("php:commerce", "php:tools"))
            if path == "services/genie/tests/page_cache_probe.py":
                selected.add("native:inquiry")
        elif path.startswith("fixtures/planning/") or path.startswith(
            (
                "docs/research/2026-10-23-pv-inputs/raw/",
                "docs/research/2026-10-24-pv-generation/raw/",
            )
        ):
            selected.update(("engine", "planner"))
        elif path.startswith("tools/local/"):
            selected.add("python:local")
            if not local_test_module(path):
                selected.update(("python:pull", "python:cutover"))
                selected.update(native)
                if path in LOCAL_PREFLIGHT_INPUTS:
                    selected.add("content")
            if path.endswith(".php") or path.split("/")[-1].startswith(
                ("composer", "phpstan", "phpcs")
            ):
                selected.add("php:local")
                selected.update(native)
        elif path.startswith(("tools/migrate/", "tools/pull/", "tools/cutover/")):
            selected.add("python:" + path.split("/")[1])
            if commerce_migration_input(path):
                selected.add("php:commerce")
        elif path.startswith("tools/faq/") or re.match(
            r"docs/research/2026-10-20-campaign-\d+/harness/", path
        ):
            selected.add("python:harnesses")
        elif path.startswith("tests/e2e/"):
            selected.add("js:e2e")
        elif path.startswith("mu-plugins/"):
            selected.add("php:mu")
            selected.update(native)
        elif path == CABLE_ADOPTION:
            # The CLI reads this once for adoption. Engine/Genie consume Woo
            # publications, never this input file as a runtime data source.
            selected.update(("php:commerce", "content"))
        elif path.startswith("plugins/"):
            parts = path.split("/")
            package = parts[1]
            if package not in {"linker-commerce", "linker-tools", "linker-i18n"}:
                return None
            name = package.removeprefix("linker-")
            relative = "/".join(parts[2:])
            if (
                relative.startswith(
                    ("src/", "assets/", "build/", "tests/js/", "tests/e2e/")
                )
                or path.endswith((".ts", ".tsx", ".mjs", ".cjs", ".mts"))
                or parts[-1] in {"package.json", "package-lock.json", "tsconfig.json"}
            ):
                if name == "i18n":
                    return None
                selected.update(("js:" + name, "build:" + name, "php:" + name))
                selected.update(native)
                if under(path, (ENGINE_TOOLS_SCHEMAS,)):
                    selected.add("engine")
                if name == "tools" and relative.startswith("src/genie/"):
                    selected.add("genie")
            elif (
                path.endswith(".php")
                or path == COMMERCE_COMPATIBILITY
                or relative.startswith(("content/", "languages/", "tests/php/"))
                or parts[-1].startswith(("composer.", "phpunit", "phpstan", "phpcs"))
            ):
                selected.add("php:" + name)
                selected.update(native)
                if name in {"commerce", "i18n"}:
                    selected.add("php:tools")
                if name == "i18n":
                    selected.add("php:commerce")
                if not relative.startswith("tests/"):
                    selected.add("content")
                if path == COMMERCE_COMPATIBILITY:
                    selected.update(("engine", "python:migrate"))
                if name == "commerce" and relative.startswith(
                    "includes/Products/Publication"
                ):
                    selected.update(("engine", "genie"))
                if name == "commerce" and under(path, GENIE_COMMERCE_INPUTS):
                    selected.add("genie")
                # Outbox scheduling is a native PHP/AS contract; neither the
                # engine nor the frontend recipe reads this implementation.
                if (
                    name == "tools"
                    and relative.startswith("includes/Planner/")
                    and relative != "includes/Planner/ClaimOutbox.php"
                ):
                    selected.update(("engine", "planner"))
                if name == "tools" and relative.startswith(
                    ("includes/Genie/", "includes/Protection/")
                ):
                    selected.add("genie")
            else:
                return None
        else:
            return None
    return [module for module in MODULE_COMMANDS if module in selected]


def modules_for_lanes(lanes, changes, base="", head=""):
    if not lanes:
        return []
    if lanes == list(FULL_LANES):
        return list(FULL_MODULES)
    modules = selected_modules(changes, base, head)
    return list(FULL_MODULES) if modules is None else modules


def module_project(module):
    kind, _, name = module.partition(":")
    if kind == "php":
        return PHP_PROJECTS[name]
    if kind == "python":
        return PYTHON_PROJECTS.get(name, "harnesses")
    return name


def module_matrix(modules, lane):
    # A skipped job still gets a nonempty valid matrix expression.
    return [
        module_project(module) for module in modules if module_lane(module) == lane
    ] or ["none"]


def module_job_name(module):
    lane = module_lane(module)
    prefix = {
        "php": "php-lane",
        "js": "js-lane",
        "python": "python-lane",
        "native": "mu-smoke",
    }.get(lane, lane)
    return prefix + " (" + module_project(module) + ")" if ":" in module else prefix


def module_inputs(module):
    """Complete packages plus explicit inputs read across package boundaries.

    PHP contracts intentionally retain their coupled companion includes/fixture
    roots; native loads the installed plugins and Genie's real page-cache probe.
    Neither uses all services/tools/docs as a substitute for those dependencies.
    """
    lane = module_lane(module)
    shared = CONTROL_INPUTS
    commerce = "plugins/linker-commerce/"
    tools = "plugins/linker-tools/"
    i18n = "plugins/linker-i18n/"
    php_shared = "tools/php/"
    engine_feed = "services/engine/tests/fixtures/feed.json"
    size_hint = "services/genie/tests/fixtures/size-hint-urls.json"
    if lane == "php":
        name = module.split(":", 1)[1]
        dependencies = {
            "commerce": (
                tools + "includes/Genie/",
                i18n + "includes/",
                i18n + "tests/fixtures/live/",
                "tools/migrate/",
                "tools/faq/wordpress.php",
                engine_feed,
                size_hint,
            ),
            "tools": (commerce, i18n + "includes/"),
            "i18n": (commerce + "includes/Digest/Block.php",),
            "mu": (),
            "local": (),
        }
        return (*shared, PHP_PROJECTS[name], php_shared, *dependencies[name])
    if lane == "native":
        return (
            *shared,
            commerce,
            tools,
            i18n,
            "mu-plugins/",
            "tools/local/",
            "tools/checks/",
            "tests/e2e/fixtures/",
            *(("services/genie/",) if module == "native:inquiry" else ()),
        )
    if lane in {"presentation", "content"}:
        # Catalog/source scanners inspect all plugin surfaces. CI runner tests
        # also import linker-local; no acceptance report is scanner input.
        return (
            *shared,
            commerce,
            tools,
            i18n,
            "tools/checks/",
            "tools/local/",
            "apps/planner/src/",
        )
    if lane in {"js", "build"}:
        name = module.split(":", 1)[1]
        if name == "e2e":
            return (*shared, "tests/e2e/")
        if name == "commerce":
            return (
                *shared,
                commerce,
                tools + "bin/build-manifest.mjs",
                tools + "package.json",
                tools + "package-lock.json",
            )
        return (*shared, tools, "apps/planner/", "fixtures/planning/")
    if lane == "planner":
        return (
            *shared,
            "apps/planner/",
            "fixtures/planning/",
            tools + "bin/",
            tools + "build/",
            tools + "tests/php/Unit/PlannerApplicationTest.php",
            tools + "composer.json",
            tools + "composer.lock",
            php_shared,
        )
    if lane == "engine":
        return (
            *shared,
            "services/engine/",
            *ENGINE_PLANNER_INPUTS,
            "fixtures/planning/",
            COMMERCE_COMPATIBILITY,
            *ENGINE_PUBLICATION_INPUTS,
            ENGINE_TOOLS_SCHEMAS,
            *ENGINE_DOC_INPUTS,
        )
    if lane == "genie":
        return (
            *shared,
            "services/genie/",
            "services/engine/tests/fixtures/",
            *GENIE_COMMERCE_INPUTS,
            "services/engine/src/linker_engine/planning/assistant_context.py",
            tools + "includes/Genie/",
            tools + "includes/Protection/",
            tools + "src/genie/",
            tools + "tests/php/Integration/PageCacheChainTest.php",
            *GENIE_DOC_INPUTS,
        )
    name = module.split(":", 1)[1]
    if name == "harnesses":
        return (
            *shared,
            "tools/faq/",
            *HARNESS_EXTERNAL_INPUTS,
            *(
                f"docs/research/2026-10-20-campaign-{number}/harness/"
                for number in (330, 332, 333, 334, 335)
            ),
        )
    if name == "migrate":
        return (
            *shared,
            "tools/migrate/",
            "tools/checks/",
            commerce,
            tools + "includes/",
            i18n,
            *MIGRATE_DOC_INPUTS,
        )
    # Pull/cutover depend on linker-local and test installing a checkout's real
    # plugins. Keep that explicit companion scope, not unrelated migration/docs.
    return (
        *shared,
        PYTHON_PROJECTS[name],
        "tools/local/",
        "tools/checks/",
        commerce,
        tools,
        i18n,
        "mu-plugins/",
        *LOCAL_ENGINE_INPUTS,
        *(("services/genie/ops/",) if name == "cutover" else ()),
    )


class ProofCache:
    """Bounded, invocation-local memoization of immutable Git proof inputs."""

    def __init__(self):
        # One head and one prior candidate; the API searches at most ten runs.
        # A pair's module hashes need at most two complete module sets.
        self.tree = lru_cache(maxsize=2)(
            lambda commit: git("ls-tree", "-r", "-z", commit)
        )
        self.pair = lru_cache(maxsize=10)(proof_increment_known)
        self.fingerprint = lru_cache(maxsize=2 * len(MODULE_COMMANDS))(
            lambda commit, module: _module_fingerprint(commit, module, self)
        )


def immutable_commit(commit):
    return isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) is not None


def module_input_path(module, path, paths):
    if module == "engine" and path.startswith("apps/planner/"):
        if not engine_planner_input(path):
            return False
    # These Python test entrypoints are run only by linker-local's own pytest;
    # companion consumers use its runtime, PHP, config, and test fixtures.
    if local_test_module(path) and (
        module
        in {"php:local", "presentation", "content", "python:pull", "python:cutover"}
        or module.startswith("native:")
    ):
        return False
    # Commerce PHPCS/PHPStan analyze migration PHP; its product fixture reads
    # 7-facts.json. The migration Python CLI and pytest are separate consumers.
    if (
        module == "php:commerce"
        and path.startswith("tools/migrate/")
        and not commerce_migration_input(path)
    ):
        return False
    return under(path, paths) and not non_runtime_path(path)


def module_fingerprint(commit, module, cache=None):
    if cache is not None and immutable_commit(commit):
        return cache.fingerprint(commit, module)
    return _module_fingerprint(commit, module, None)


def _module_fingerprint(commit, module, cache):
    paths = module_inputs(module)
    if cache is not None:
        tree = cache.tree(commit)
    else:
        tree = git("ls-tree", "-r", "-z", commit)
    entries = tree.split(b"\0")
    selected = []
    for entry in entries:
        if not entry:
            continue
        path = entry.split(b"\t", 1)[1].decode()
        if module_input_path(module, path, paths):
            selected.append(entry)
    return hashlib.sha256(module.encode() + b"\0" + b"\0".join(selected)).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)


def document(path):
    return path in {"AGENTS.md", "CLAUDE.md", "CONTEXT.md", "README.md"} or (
        path.startswith("docs/") and path.endswith((".md", ".rst", ".txt"))
    )


def acceptance_record(path):
    return path.startswith("docs/acceptance/") and path.endswith(
        (".json", ".png", ".pdf", ".jpg", ".jpeg")
    )


def regular_file(commit, path):
    if not commit:
        file = Path(path)
        return (
            file.is_file() and not file.is_symlink() and not file.stat().st_mode & 0o111
        )
    entries = git("ls-tree", commit, "--", path).split()
    return bool(entries) and entries[0] == b"100644"


def file_content(commit, path):
    return git("show", f"{commit}:{path}") if commit else Path(path).read_bytes()


def non_runtime_file(commit, path):
    if not regular_file(commit, path):
        return False
    content = file_content(commit, path)
    if acceptance_record(path):
        if path.endswith(".png"):
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if path.endswith((".jpg", ".jpeg")):
            return content.startswith(b"\xff\xd8\xff")
        if path.endswith(".pdf"):
            return content.startswith(b"%PDF-")
        json.loads(content)
        return True
    if b"\0" in content:
        return False
    content.decode("utf-8")
    return True


def regular_change(status, path, base, head):
    revisions = {"M": (base, head), "A": (head,), "D": (base,)}.get(status, ())
    return bool(revisions) and all(regular_file(rev, path) for rev in revisions)


def non_runtime_change(status, path, base, head):
    revisions = {"M": (base, head), "A": (head,), "D": (base,)}.get(status, ())
    return bool(revisions) and all(non_runtime_file(rev, path) for rev in revisions)


def presentation(path):
    return (
        bool(
            re.fullmatch(
                r"plugins/linker-commerce/content/(livecanvas/(de/)?[a-z0-9_-]+[.]html|windpress/[a-z0-9_-]+[.]css)",
                path,
            )
        )
        or path
        == "plugins/linker-commerce/tests/php/Unit/Presentation/TemplatesTest.php"
    )


def manifest_entries(commit):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate Tools manifest entry")
            result[key] = value
        return result

    value = json.loads(
        file_content(commit, "plugins/linker-tools/build/manifest.json"),
        object_pairs_hook=unique_pairs,
    )
    if not isinstance(value, dict) or set(value) != {"sources", "build"}:
        raise ValueError("Unexpected Tools manifest")
    for section in value.values():
        if not isinstance(section, dict) or not all(
            isinstance(path, str)
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            for path, digest in section.items()
        ):
            raise ValueError("Invalid Tools manifest entries")
    return value


def planner_manifest_isolated(base, head):
    if not base:
        return False
    try:
        before = manifest_entries(base)
        after = manifest_entries(head)
    except (OSError, subprocess.SubprocessError, TypeError, ValueError):
        return False
    if before["sources"] != after["sources"]:
        return False
    for entries in (before["build"], after["build"]):
        if not any(path.startswith("build/planner/") for path in entries):
            return False
    before_other = {
        path: digest
        for path, digest in before["build"].items()
        if not path.startswith("build/planner/")
    }
    after_other = {
        path: digest
        for path, digest in after["build"].items()
        if not path.startswith("build/planner/")
    }
    return before_other == after_other


def tools_manifest_matches_changes(changes, base, head):
    """Prove each manifest digest change belongs to an actual Tools file change."""
    if not base:
        return False
    try:
        before, after = manifest_entries(base), manifest_entries(head)
        required = {
            "package.json",
            "package-lock.json",
            "webpack.config.js",
            "project-input-contracts.json",
        }
        for manifest in (before, after):
            if not required <= manifest["sources"].keys() or not manifest["build"]:
                return False
            for section, entries in manifest.items():
                for path in entries:
                    if (
                        "\\" in path
                        or any(part in {"", ".", ".."} for part in path.split("/"))
                        or (
                            section == "sources"
                            and path not in required
                            and path != "bin/build.cjs"
                            and (
                                not path.startswith("src/")
                                or re.search(r"\.(?:test|stories)\.[jt]sx?$", path)
                            )
                        )
                        or (
                            section == "build"
                            and (
                                not path.startswith("build/")
                                or path == "build/manifest.json"
                            )
                        )
                    ):
                        return False
        statuses = {path: status for status, path in changes}
        prefix = "plugins/linker-tools/"
        for path, status in statuses.items():
            if not path.startswith(prefix):
                continue
            name = path.removeprefix(prefix)
            if name in required or (
                name.startswith("src/")
                and not re.search(r"\.(?:test|stories)\.[jt]sx?$", name)
            ):
                section = "sources"
            elif name.startswith("build/") and name != "build/manifest.json":
                section = "build"
            else:
                continue
            left, right = before[section], after[section]
            expected = (
                "M"
                if name in left and name in right
                else "D"
                if name in left
                else "A"
                if name in right
                else ""
            )
            if status != expected or left.get(name) == right.get(name):
                return False
        modified = False
        for section in ("sources", "build"):
            left, right = before[section], after[section]
            for name in left.keys() | right.keys():
                if left.get(name) == right.get(name):
                    continue
                modified = True
                path = prefix + name
                expected = (
                    "M"
                    if name in left and name in right
                    else "D"
                    if name in left
                    else "A"
                )
                if statuses.get(path) != expected:
                    return False
                for revision, entries in ((base, left), (head, right)):
                    if (
                        name in entries
                        and hashlib.sha256(file_content(revision, path)).hexdigest()
                        != entries[name]
                    ):
                        return False
        return modified
    except (OSError, subprocess.SubprocessError, TypeError, ValueError):
        return False


def classify(changes, base="", head=""):
    modules = selected_modules(changes, base, head)
    if modules is None:
        return list(FULL_LANES)
    lanes = {module_lane(module) for module in modules}
    return [lane for lane in LANES if lane in lanes]


def diff_changes(base, head):
    def records(*options):
        raw = git(
            "diff",
            "--name-status",
            "-z",
            *options,
            base,
            *([head] if head else []),
            "--",
        )
        if not raw:
            return []
        fields = raw.decode(errors="surrogateescape").split("\0")
        if fields[-1]:
            raise ValueError("Incomplete Git name-status record")
        fields = fields[:-1]
        changes = []
        while fields:
            status = fields.pop(0)
            if not fields:
                raise ValueError("Missing path in Git name-status record")
            path = fields.pop(0)
            if status.startswith(("R", "C")):
                if not fields:
                    raise ValueError("Missing destination in Git structural record")
                destination = fields.pop(0)
                old_chunk = PLANNER_CHUNK.fullmatch(path)
                new_chunk = PLANNER_CHUNK.fullmatch(destination)
                if (
                    status.startswith("R")
                    and old_chunk
                    and new_chunk
                    and old_chunk[1] == new_chunk[1]
                ):
                    # Vite changed the content hash of this generated bundle.
                    # The no-renames diff retains both paths and Planner rebuilds them.
                    continue
            changes.append((status, path))
        return changes

    changes = records("--no-renames")
    structural = [
        (status, path)
        for status, path in records("--find-renames", "--find-copies")
        if status not in {"A", "M", "D"}
    ]
    return structural + changes


def change_flags(changes):
    """Guards consumed by the same local and hosted recipes."""
    paths = [path for _, path in changes]
    return {
        "catalog_changed": any(
            path.startswith("plugins/linker-commerce/content/livecanvas/")
            for path in paths
        ),
        "php_test_changed": (
            "plugins/linker-commerce/tests/php/Unit/Presentation/TemplatesTest.php"
            in paths
        ),
        "planner_build_changed": any(
            path.startswith("plugins/linker-tools/build/planner/") for path in paths
        ),
    }


def api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def latest_run(sha, event=""):
    repo = os.environ["REPOSITORY"]
    endpoint = (
        f"repos/{repo}/actions/workflows/check.yml/runs?head_sha={sha}&per_page=100"
    )
    if event:
        endpoint += "&event=" + event
    runs = api(endpoint)["workflow_runs"]
    runs = [
        run
        for run in runs
        if run["head_sha"] == sha
        and run["path"] == WORKFLOW
        and run["event"] in {"pull_request", "push", "workflow_dispatch"}
        and (not event or run["event"] == event)
    ]
    return max(
        runs, key=lambda run: (run["run_number"], run["run_attempt"]), default=None
    )


def validated_scope(run):
    if not run or run["status"] != "completed" or run["conclusion"] != "success":
        return None
    repo = os.environ["REPOSITORY"]
    jobs = api(
        f"repos/{repo}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100"
    )["jobs"]
    for job in jobs:
        for step in job.get("steps", []):
            marker = re.fullmatch(
                r"Record (?:validation|validated) scope \((docs|full|scoped|commerce|presentation|reuse)\)",
                step["name"],
            )
            if marker and step.get("conclusion") == "success":
                return marker.group(1)
    return None


def checked_run(run, commit, *, full=False, docs_only=False):
    if not run or run["status"] != "completed" or run["conclusion"] != "success":
        return False
    if git("rev-parse", f"{commit}:{WORKFLOW}") != git("rev-parse", f"HEAD:{WORKFLOW}"):
        return False
    marker = re.fullmatch(
        r"check #[^\n]+ [|] tree-ref=([0-9a-f]{40})",
        run.get("display_title", ""),
    )
    if not marker:
        return False
    tested = marker.group(1)
    try:
        tree = git("rev-parse", tested + "^{tree}").decode().strip()
    except subprocess.CalledProcessError:
        repo = os.environ["REPOSITORY"]
        tree = api(f"repos/{repo}/git/commits/{tested}")["tree"]["sha"]
    if tree != git("rev-parse", commit + "^{tree}").decode().strip():
        return False
    scope = validated_scope(run)
    if full:
        return scope == "full"
    if docs_only:
        return scope == "docs"
    return scope in {"docs", "full", "scoped", "commerce", "presentation", "reuse"}


def checked_pr_tree(commit, *, full=False):
    parents = git("rev-list", "--parents", "-n", "1", commit).decode().split()
    if len(parents) >= 3:
        source = parents[2]
    else:
        repo = os.environ["REPOSITORY"]
        pulls = api(f"repos/{repo}/commits/{commit}/pulls")
        merged = [pull for pull in pulls if pull.get("merge_commit_sha") == commit]
        if not merged:
            return None
        source = merged[0]["head"]["sha"]
    run = latest_run(source, "pull_request")
    return run if checked_run(run, commit, full=full) else None


def checked_base(commit):
    seen = set()
    while commit not in seen:
        seen.add(commit)
        run = latest_run(commit)
        if checked_run(run, commit, full=True):
            return True
        if checked_run(run, commit, docs_only=True):
            try:
                parent = git("rev-parse", commit + "^1").decode().strip()
            except subprocess.CalledProcessError:
                git("fetch", "--deepen=1", "origin", commit)
                parent = git("rev-parse", commit + "^1").decode().strip()
            changes = diff_changes(parent, commit)
            if classify(changes, parent, commit) or not all(
                non_runtime_change(status, path, parent, commit)
                for status, path in changes
            ):
                return False
            commit = parent
            continue
        if (
            run
            and run["status"] == "completed"
            and run["conclusion"] == "success"
            and validated_scope(run) == "reuse"
        ):
            original = checked_pr_tree(commit)
            return validated_scope(original) in {"full", "scoped"}
        if run and (run["status"] != "completed" or run["conclusion"] != "cancelled"):
            return False
        original = checked_pr_tree(commit)
        return validated_scope(original) in {"full", "scoped"}
    return False


def tested_commit(run):
    marker = re.fullmatch(
        r"check #[^\n]+ [|] tree-ref=([0-9a-f]{40})", run.get("display_title", "")
    )
    return marker.group(1) if marker else None


def run_module_jobs(run):
    value = api(
        f"repos/{os.environ['REPOSITORY']}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100"
    )
    jobs = value.get("jobs", [])
    if value.get("total_count", len(jobs)) > len(jobs):
        raise ValueError("module job proof is incomplete")
    return jobs


MODULE_PHASE_STEPS = {
    "engine": ("Planner dependencies", "Check", "Test"),
    "genie": ("Check", "Test"),
    "planner": (
        "Verify Planner invocation",
        "Planner dependencies",
        "Check",
        "Test",
        "Build",
    ),
}


def successful_module_job(job, module, *, planner_build_changed=None):
    if job.get("name") != module_job_name(module) or job.get("conclusion") != "success":
        return False
    steps = job.get("steps", [])
    required = MODULE_PHASE_STEPS.get(module, ("Validate module",))
    if not all(
        any(step.get("name") == name for step in steps)
        and all(
            step.get("conclusion") == "success"
            for step in steps
            if step.get("name") == name
        )
        for name in required
    ):
        return False
    if module == "planner":
        if planner_build_changed is None:
            return False
        # Native merge evidence determines whether this conditional phase ran.
        expected = "success" if planner_build_changed else "skipped"
        php_steps = [step for step in steps if step.get("name") == "Planner PHP"]
        return bool(php_steps) and all(
            step.get("conclusion") == expected for step in php_steps
        )
    return True


def proof_increment_known(before, head):
    try:
        git("cat-file", "-e", before + "^{commit}")
    except subprocess.CalledProcessError:
        git("fetch", "--depth=1", "origin", before)
    changes = diff_changes(before, head)
    # A module fingerprint covers declared inputs, not an unknown new root or
    # structural change. Classify the proof-to-head increment independently of
    # the cumulative PR diff, which can remain full after an earlier workflow.
    if changes and selected_modules(changes, before, head) is None:
        return False
    return True


def same_module_inputs(before, head, module, cache=None):
    if cache is not None and immutable_commit(before) and immutable_commit(head):
        known = cache.pair(before, head)
    else:
        known = proof_increment_known(before, head)
    if not known:
        return False
    return module_fingerprint(before, module, cache) == module_fingerprint(
        head, module, cache
    )


def planner_build_flag(commit, *, source=None, base=None):
    """Reconstruct a CI merge's flag only from available native Git evidence."""
    try:
        try:
            git("cat-file", "-e", commit + "^{commit}")
        except subprocess.CalledProcessError:
            git("fetch", "--depth=1", "origin", commit)
        headers = git("cat-file", "commit", commit).split(b"\n\n", 1)[0]
        parents = [
            line.removeprefix(b"parent ").decode("ascii")
            for line in headers.splitlines()
            if line.startswith(b"parent ")
        ]
        if (
            len(parents) != 2
            or parents[0] == parents[1]
            or any(re.fullmatch(r"[0-9a-f]{40}", parent) is None for parent in parents)
            or (source is not None and parents[1] != source)
            or (base is not None and parents[0] != base)
        ):
            return None
        # cat-file reads actual parent headers even at a shallow boundary;
        # rev-list can silently present that same merge as a root commit.
        for parent in parents:
            git("cat-file", "-e", parent + "^{commit}")
        return change_flags(diff_changes(parents[0], commit))["planner_build_changed"]
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return None


def verify_planner_invocation():
    """Reject a PR job whose actual recipe flag differs from its Git diff."""
    if os.environ.get("EVENT_NAME") != "pull_request":
        print("Planner invocation verification is only required for PR reuse.")
        return
    base = os.environ.get("BASE_SHA", "")
    head = os.environ.get("HEAD_SHA", "")
    declared = os.environ.get("PLANNER_BUILD_CHANGED", "")
    if any(
        re.fullmatch(r"[0-9a-f]{40}", value) is None for value in (base, head)
    ) or declared not in {"true", "false"}:
        raise SystemExit("Planner invocation condition evidence is incomplete.")
    actual = planner_build_flag(head, base=base)
    if actual is None or declared != str(actual).lower():
        raise SystemExit(
            "Planner invocation flag does not match the verified PR merge."
        )
    print(f"Verified Planner invocation: planner_build_changed={declared}.")


def same_module_conditions(run, commit, head, module):
    if module != "planner":
        return True
    source = run.get("head_sha", "")
    base = os.environ.get("BASE_SHA", "")
    if any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None
        for value in (source, base)
    ):
        return False
    before = planner_build_flag(commit, source=source)
    current = planner_build_flag(head, base=base)
    return before is not None and current is not None and before == current


def reusable_modules(modules, head):
    """Only completed successful module jobs on identical declared inputs.

    A failed overall run can contain a green independent module. Search only
    this PR's recent runs; cancellation/failure/skipped work is never a proof.
    The final gate independently reads the same immutable attempt and inputs.
    """
    number = os.environ.get("PR_NUMBER", "")
    if os.environ.get("EVENT_NAME") != "pull_request" or not number.isdecimal():
        return {}
    runs = api(
        f"repos/{os.environ['REPOSITORY']}/actions/workflows/check.yml/runs?event=pull_request&per_page=10"
    )["workflow_runs"]
    proofs = {}
    cache = ProofCache()
    for run in runs:
        if (
            run.get("status") != "completed"
            or run.get("event") != "pull_request"
            or run.get("path") != WORKFLOW
            or run.get("head_sha") == os.environ.get("HEAD_SHA")
            or not any(
                str(pull.get("number")) == number
                for pull in run.get("pull_requests", [])
            )
        ):
            continue
        commit = tested_commit(run)
        if commit is None:
            continue
        jobs = run_module_jobs(run)
        for module in modules:
            if module in proofs or module in DIFF_GUARDED_MODULES:
                continue
            planner_flag = (
                planner_build_flag(commit, source=run.get("head_sha"))
                if module == "planner"
                else None
            )
            job = next(
                (
                    job
                    for job in jobs
                    if successful_module_job(
                        job, module, planner_build_changed=planner_flag
                    )
                ),
                None,
            )
            if (
                job is not None
                and same_module_conditions(run, commit, head, module)
                and same_module_inputs(commit, head, module, cache)
            ):
                proofs[module] = {
                    "run": run["id"],
                    "attempt": run["run_attempt"],
                    "job": job["id"],
                    "commit": commit,
                    "inputs": module_fingerprint(head, module, cache),
                }
        if len(proofs) == len(modules):
            break
    return proofs


def validate_module_reuse(proofs, required, head):
    if (
        not isinstance(proofs, dict)
        or set(proofs) - set(required)
        or set(proofs) & DIFF_GUARDED_MODULES
    ):
        return False
    runs = {}
    cache = ProofCache()
    for module, proof in proofs.items():
        if not isinstance(proof, dict) or set(proof) != {
            "run",
            "attempt",
            "job",
            "commit",
            "inputs",
        }:
            return False
        key = proof["run"]
        if key not in runs:
            run = api(f"repos/{os.environ['REPOSITORY']}/actions/runs/{key}")
            if (
                run.get("status") != "completed"
                or run.get("path") != WORKFLOW
                or run.get("event") != "pull_request"
                or run.get("run_attempt") != proof["attempt"]
                or tested_commit(run) != proof["commit"]
            ):
                return False
            if not any(
                str(pull.get("number")) == os.environ.get("PR_NUMBER")
                for pull in run.get("pull_requests", [])
            ):
                return False
            runs[key] = run, run_module_jobs(run)
        run, jobs = runs[key]
        if proof["attempt"] != run["run_attempt"] or proof["commit"] != tested_commit(
            run
        ):
            return False
        planner_flag = (
            planner_build_flag(proof["commit"], source=run.get("head_sha"))
            if module == "planner"
            else None
        )
        if not any(
            job.get("id") == proof["job"]
            and successful_module_job(job, module, planner_build_changed=planner_flag)
            for job in jobs
        ):
            return False
        if (
            not same_module_conditions(run, proof["commit"], head, module)
            or proof["inputs"] != module_fingerprint(head, module, cache)
            or not same_module_inputs(proof["commit"], head, module, cache)
        ):
            return False
    return True


def write_output(name, value):
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"{name}={value}\n")


def plan():
    event = os.environ["EVENT_NAME"]
    head = os.environ["HEAD_SHA"]
    base = os.environ.get("BASE_SHA", "")
    changes = []
    candidate = list(FULL_LANES)
    mode = "full"
    reason = "The complete package and native integration checks are required."
    error = ""
    if base and set(base) != {"0"}:
        try:
            try:
                git("cat-file", "-e", base + "^{commit}")
            except subprocess.CalledProcessError:
                git("fetch", "--depth=1", "origin", base)
            formatting = subprocess.run(["git", "diff", "--check", base, head])
            if formatting.returncode:
                raise SystemExit(formatting.returncode)
            changes = diff_changes(base, head)
            candidate = classify(changes, base, head)
            if event == "pull_request":
                if not candidate:
                    mode = "docs"
                    reason = "Documentation and acceptance records only."
                elif candidate != list(FULL_LANES):
                    try:
                        proven = checked_base(base)
                    except (OSError, subprocess.SubprocessError, KeyError, ValueError):
                        proven = False
                    if proven:
                        mode = "scoped"
                        reason = "Only declared package inputs changed on a fully checked base."
                    else:
                        reason = (
                            "No fully checked base; narrow selection is not allowed."
                        )
        except (
            OSError,
            subprocess.SubprocessError,
            UnicodeError,
            KeyError,
            ValueError,
            IndexError,
        ) as exception:
            error = f"{type(exception).__name__}: {exception}"
            candidate = list(FULL_LANES)
            mode = "full"
            reason = "The complete diff could not be proven; the final gate will reject an incomplete ledger."
    if event == "push":
        if not candidate and changes and not error:
            mode = "docs"
            reason = "Documentation and acceptance records only."
        else:
            mode = "full"
            try:
                run = checked_pr_tree(head)
                if run:
                    mode = "reuse"
                    reason = f"Identical Git tree already checked by pull-request run {run['id']}."
            except (OSError, subprocess.SubprocessError, KeyError, ValueError):
                reason = "No proven successful check for this tree; complete checks required."
    selected = (
        []
        if mode in {"docs", "reuse"}
        else list(FULL_LANES)
        if mode == "full"
        else candidate
    )
    required_modules = modules_for_lanes(selected, changes, base, head)
    reused = {}
    if mode in {"scoped", "full"}:
        try:
            reused = reusable_modules(required_modules, head)
        except (OSError, subprocess.SubprocessError, KeyError, ValueError):
            # No proof means execute, never silently skip the affected module.
            reused = {}
    executed_modules = [module for module in required_modules if module not in reused]
    selected = [
        lane
        for lane in LANES
        if any(module_lane(module) == lane for module in executed_modules)
    ]
    ledger = {
        "base": base,
        "head": head,
        "mode": mode,
        "candidate": candidate,
        "lanes": selected,
        "modules": required_modules,
        "reused": reused,
        "changes": [{"status": status, "path": path} for status, path in changes],
    }
    if error:
        ledger["error"] = error
    write_output("mode", mode)
    write_output("ledger", json.dumps(ledger, separators=(",", ":")))
    for lane in LANES:
        write_output(lane, str(lane in selected).lower())
    for lane in ("php", "js", "python", "build", "native"):
        write_output(
            lane + "_matrix",
            json.dumps(module_matrix(executed_modules, lane), separators=(",", ":")),
        )
    for name, changed in change_flags(changes).items():
        write_output(name, str(changed).lower())
    lines = [
        f"### Validation scope: {mode}",
        "",
        reason,
        "",
        "| Status | Path | Package lane |",
        "| --- | --- | --- |",
    ]
    for status, path in changes:
        isolated = classify([(status, path)], base, head) if base else FULL_LANES
        lanes = ", ".join(isolated) if isolated != FULL_LANES else "full"
        lines.append(f"| {status} | `{path.replace('|', chr(92) + '|')}` | {lanes} |")
    lines.extend(
        ["", "| Module | Actual command / proven prior job |", "| --- | --- |"]
    )
    for module in required_modules:
        proof = reused.get(module)
        detail = " ".join(MODULE_COMMANDS[module])
        if proof:
            detail = f"reuse run {proof['run']} attempt {proof['attempt']} job {proof['job']}; same inputs {proof['inputs']}"
        lines.append(f"| {module} | `{detail}` |")
    if error:
        lines.extend(["", f"Ledger error: `{error}`"])
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def audit_gate(ledger, results, changes):
    errors = []
    if results.get("plan", {}).get("result") != "success":
        return ["plan did not succeed"]
    if ledger.get("error"):
        errors.append(f"plan could not prove the complete diff: {ledger['error']}")
    if ledger.get("base") != os.environ.get("BASE_SHA", "") or ledger.get(
        "head"
    ) != os.environ.get("HEAD_SHA"):
        errors.append("plan and gate use different commits")
    recorded = [(item["status"], item["path"]) for item in ledger.get("changes", [])]
    if recorded != changes:
        errors.append("the changed-path ledger is incomplete or different")
    candidate = classify(changes, ledger.get("base", ""), ledger.get("head", ""))
    if ledger.get("candidate") != candidate:
        errors.append("the independently recomputed package selection differs")
    mode = ledger.get("mode")
    event = os.environ.get("EVENT_NAME", "")
    selected = ledger.get("lanes")
    if mode not in {"docs", "full", "scoped", "reuse"}:
        errors.append("unrecognized validation mode")
    if (
        not isinstance(selected, list)
        or set(selected) - set(LANES)
        or len(selected) != len(set(selected))
    ):
        errors.append("invalid lane list")
        selected = []
    if mode in {"docs", "reuse"} and selected:
        errors.append("a documentation or reused run cannot execute package jobs")
    if mode == "docs" and (candidate or event not in {"pull_request", "push"}):
        errors.append("documentation scope requires only non-runtime changes")
    if mode == "reuse" and event != "push":
        errors.append("identical-tree reuse is only valid for a main push")
    required_lanes = (
        candidate if mode == "scoped" else list(FULL_LANES) if mode == "full" else []
    )
    required = modules_for_lanes(
        required_lanes, changes, ledger.get("base", ""), ledger.get("head", "")
    )
    if ledger.get("modules") != required:
        errors.append("the independently recomputed module selection differs")
    reused = ledger.get("reused", {})
    if (
        not isinstance(reused, dict)
        or set(reused) - set(required)
        or (reused and mode not in {"scoped", "full"})
    ):
        errors.append("invalid module reuse ledger")
        reused = {}
    expected_lanes = [
        lane
        for lane in LANES
        if any(
            module_lane(module) == lane for module in required if module not in reused
        )
    ]
    if selected != expected_lanes:
        errors.append("executed lanes differ from required modules and explicit reuse")
    if mode == "scoped" and (
        not candidate or candidate == list(FULL_LANES) or event != "pull_request"
    ):
        errors.append("invalid scoped validation mode")
    for lane in LANES:
        actual = results.get(lane, {}).get("result")
        expected = "success" if lane in selected else "skipped"
        if actual != expected:
            errors.append(f"{lane}: expected {expected}, got {actual}")
    return errors


def gate():
    ledger = json.loads(os.environ["EXPECTED_LEDGER"])
    results = json.loads(os.environ["JOB_RESULTS"])
    if git("rev-parse", "HEAD").decode().strip() != os.environ["HEAD_SHA"]:
        raise ValueError("The gate checked out a different commit")
    base = os.environ["BASE_SHA"]
    if base and set(base) != {"0"}:
        try:
            git("cat-file", "-e", base + "^{commit}")
        except subprocess.CalledProcessError:
            git("fetch", "--depth=1", "origin", base)
        changes = diff_changes(base, os.environ["HEAD_SHA"])
    else:
        changes = []
    errors = audit_gate(ledger, results, changes)
    if not errors and ledger["mode"] in {"scoped", "reuse"}:
        try:
            proven = (
                checked_base(base)
                if ledger["mode"] == "scoped"
                else bool(checked_pr_tree(os.environ["HEAD_SHA"]))
            )
        except (OSError, subprocess.SubprocessError, KeyError, ValueError):
            proven = False
        if not proven:
            errors.append(f"the {ledger['mode']} proof could not be reproduced")
    if not errors and ledger.get("reused"):
        try:
            if not validate_module_reuse(
                ledger["reused"], ledger["modules"], os.environ["HEAD_SHA"]
            ):
                errors.append(
                    "module success/input reuse proof could not be reproduced"
                )
        except (OSError, subprocess.SubprocessError, KeyError, ValueError):
            errors.append("module success/input reuse proof unavailable")
    for lane in LANES:
        print(f"{lane}: {results.get(lane, {}).get('result')}")
    if errors:
        for error in errors:
            print(f"GATE FAILURE: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"Validated {ledger['mode']}: every selected job succeeded; every other job was skipped."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("plan", "classify", "gate", "verify-planner")
    )
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    if args.command == "plan":
        plan()
    elif args.command == "gate":
        gate()
    elif args.command == "verify-planner":
        verify_planner_invocation()
    else:
        changes = diff_changes(args.base, args.head)
        print(
            json.dumps(
                {"changes": changes, "lanes": classify(changes, args.base, args.head)},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
