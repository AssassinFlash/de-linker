# Front-end build of plugins/linker-tools. build/ is committed together with
# build/manifest.json, the SHA-256 of each source it was built from and of each
# file it produced.

set shell := ["bash", "-euo", "pipefail", "-c"]
set ignore-comments := true

tools_dir := justfile_directory() / "plugins/linker-tools"

# Build the apps into plugins/linker-tools/build/ and write its manifest.
[default]
all:
    # A module recipe cannot depend on a recipe of the parent justfile (just 1.58
    # rejects `super::js-install` as an unknown dependency), so it calls just.
    {{ just_executable() }} --justfile {{ justfile() }} js-install
    cd {{ tools_dir }} && npm run build

# Fail if a source or a built file changed since the last `just build`.
check:
    cd {{ tools_dir }} && npm run --silent build:check
