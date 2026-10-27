interface Disposable {
	dispose: () => Promise<void>;
}
interface UnownedRenderer extends Disposable {
	readonly initialized: boolean;
	readonly backend: object;
}

/** The locked runtime implements Backend.dispose; its published base declaration
 * omits it. Check the actual public method instead of disabling library checks. */
export async function releaseBackend(backend: object): Promise<void> {
	const dispose = Reflect.get(backend, "dispose");
	if (typeof dispose !== "function")
		throw new Error("renderer_backend_disposal_unavailable");
	await dispose.call(backend);
}

/** Renderer.dispose only releases its backend after initialized=true in the
 * locked Three runtime. Before R3F receives it, this factory owns both attempted
 * backends, including one replaced by automatic WebGL fallback. Cleanup errors
 * must not replace the original initialisation failure. */
export async function releaseUnownedRenderer(
	renderer: UnownedRenderer,
	initialBackend: object | null,
): Promise<void> {
	const current = renderer.backend;
	const separate = new Set<object>();
	if (!renderer.initialized) separate.add(current);
	if (initialBackend && initialBackend !== current)
		separate.add(initialBackend);
	await Promise.allSettled([...separate].map(releaseBackend));
	try {
		await renderer.dispose();
	} catch {
		/* Original renderer failure remains authoritative. */
	}
}
