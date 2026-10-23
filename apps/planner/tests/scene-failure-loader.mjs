// Test-only network/module failure at the actual lazy boundary, not a substitute UI.
export async function load(url, context, nextLoad) {
	if (url.endsWith("/components/design/SceneViewport.tsx"))
		return {
			format: "module",
			shortCircuit: true,
			source: 'throw new Error("synthetic_3d_chunk_unavailable");',
		};
	return nextLoad(url, context);
}
