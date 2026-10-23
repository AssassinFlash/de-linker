// Test-only network/module failure at the actual lazy boundary, not a substitute UI.
export async function load(url, context, nextLoad) {
	if (new URL(url).pathname.endsWith("/components/design/SceneViewport.tsx"))
		return {
			format: "module",
			shortCircuit: true,
			source: 'throw Object.assign(new Error("synthetic_3d_chunk_unavailable"), { moduleUrl: import.meta.url });',
		};
	return nextLoad(url, context);
}
