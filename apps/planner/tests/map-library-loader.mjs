export async function resolve(specifier, context, nextResolve) {
	if (specifier === "maplibre-gl")
		return {
			url: new URL("./map-library-fixture.mjs", import.meta.url).href,
			shortCircuit: true,
		};
	return nextResolve(specifier, context);
}
