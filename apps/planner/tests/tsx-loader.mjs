import { readFile } from "node:fs/promises";
import ts from "typescript";

// Node strips erasable .ts; this test-only loader compiles React's .tsx entry
// without substituting either React or the application under examination.
export async function load(url, context, nextLoad) {
	if (!url.endsWith(".tsx")) return nextLoad(url, context);
	return {
		format: "module",
		shortCircuit: true,
		source: ts.transpileModule(await readFile(new URL(url), "utf8"), {
			compilerOptions: {
				jsx: ts.JsxEmit.ReactJSX,
				module: ts.ModuleKind.ESNext,
				target: ts.ScriptTarget.ES2024,
			},
		}).outputText,
	};
}
