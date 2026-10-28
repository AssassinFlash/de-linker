// Substitute only the canvas host so the actual renderer factory can receive a
// deterministic null WebGL context in JSDOM; no scene children are mounted.
export async function resolve(specifier, context, nextResolve) {
	if (specifier === "@react-three/fiber")
		return {
			url: new URL("./scene-renderer-fixture.mjs", import.meta.url).href,
			shortCircuit: true,
		};
	if (
		specifier === "three/webgpu" &&
		!context.parentURL.endsWith("/scene-renderer-three.mjs")
	)
		return {
			url: new URL("./scene-renderer-three.mjs", import.meta.url).href,
			shortCircuit: true,
		};
	return nextResolve(specifier, context);
}
