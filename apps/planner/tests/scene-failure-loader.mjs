// Test-only network/module failure at the actual lazy boundary, not a substitute UI.
export async function load(url, context, nextLoad) {
	const path = new URL(url).pathname;
	const view = path.endsWith("/components/design/SceneViewport.tsx")
		? "3d"
		: path.endsWith("/components/design/MapViewport.tsx")
			? "map"
			: null;
	if (view !== null)
		return {
			format: "module",
			shortCircuit: true,
			source: `throw Object.assign(new Error("synthetic_${view}_chunk_unavailable"), { moduleUrl: import.meta.url });`,
		};
	return nextLoad(url, context);
}
