// In-memory fixed-pin loading only. No app/test files are changed or copied.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { resolve as pathResolve } from "node:path";
import { fileURLToPath } from "node:url";
const app = process.cwd();
const root = pathResolve(app, "../..");
const pin = "786d0db99203d35010b6a7fdc38dc984b3058606";
const require = createRequire(pathResolve(app, "package.json"));
const ts = require("typescript");
const frozen = (path) => execFileSync("git", ["show", `${pin}:apps/planner/${path}`], { cwd: app, encoding: "utf8" });
const frozenBuild = (path) => execFileSync("git", ["show", `${pin}:plugins/linker-tools/build/planner/${path}`], { cwd: app, encoding: "utf8", maxBuffer: 16 * 1024 * 1024 });
export async function resolve(specifier, context, nextResolve) {
  try {
    const url = new URL(specifier, context.parentURL);
    if (url.protocol === "file:" && fileURLToPath(url).startsWith(root + "/plugins/linker-tools/build/planner/"))
      return { url: url.href, shortCircuit: true };
  } catch {}
  return nextResolve(specifier, context);
}
export async function load(url, context, nextLoad) {
  if (!url.startsWith("file:")) return nextLoad(url, context);
  const path = fileURLToPath(url);
  const buildPrefix = root + "/plugins/linker-tools/build/planner/";
  if (path.startsWith(buildPrefix)) {
    return { format: "module", shortCircuit: true, source: frozenBuild(path.slice(buildPrefix.length)) };
  }
  const relative = path.startsWith(app + "/") ? path.slice(app.length + 1) : null;
  if (relative === "tests/map-roof-workspace.test.mjs" && new URL(url).searchParams.has("review_harness")) {
    // Export the existing fixture, without running its registered tests.
    const source = frozen(relative).replace('import test from "node:test";', 'const test = () => undefined;') + "\nexport { rig, geometry, button };\n";
    return { format: "module", shortCircuit: true, source };
  }
  if (relative?.startsWith("tests/") && relative.endsWith(".mjs")) {
    let source = frozen(relative);
    if (relative === "tests/built-modules.mjs") {
      const replaced = source.replace(/const manifest = JSON\.parse\(\s*await readFile\(new URL\("vite-manifest\.json", directory\), "utf8"\),?\s*\);/, "const manifest = " + frozenBuild("vite-manifest.json") + ";");
      if (replaced === source) throw new Error("pinned manifest fixture marker changed");
      source = replaced;
    }
    return { format: "module", shortCircuit: true, source };
  }
  if (relative?.startsWith("src/") && /\.tsx?$/.test(relative)) {
    return {
      format: "module", shortCircuit: true,
      source: ts.transpileModule(frozen(relative), {
        compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2024 },
      }).outputText,
    };
  }
  return nextLoad(url, context);
}
