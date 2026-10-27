// Read-only test probe: disable reveal only in the module loader, without
// changing any repository source, compiled artifact or dependency.
export async function load(url, context, nextLoad) {
	if (url.endsWith("/components/revealActionResult.ts")) {
		return {
			format: "module",
			shortCircuit: true,
			source: "export function revealActionResult() { return false; }",
		};
	}
	return nextLoad(url, context);
}
