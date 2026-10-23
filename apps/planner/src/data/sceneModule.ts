import type SceneViewport from "../components/design/SceneViewport.tsx";

type SceneModule = { default: typeof SceneViewport };
const loaders = new Map<string | null, () => Promise<SceneModule>>();

/** A browser can cache a failed module URL. React.lazy alone cannot clear it.
 * Retain a successful/in-flight module across view changes; each explicit retry
 * after rejection uses a fresh URL from the native reviewed build manifest. */
export function loadSceneModule(
	moduleUrl: string | null,
): Promise<SceneModule> {
	let load = loaders.get(moduleUrl);
	if (!load) {
		let attempt = 0;
		let pending: Promise<SceneModule> | null = null;
		load = () => {
			if (pending) return pending;
			const index = attempt++;
			const request =
				index === 0
					? import("../components/design/SceneViewport.tsx")
					: moduleUrl === null
						? Promise.reject(new Error("scene_module_url_missing"))
						: (() => {
								const url = new URL(moduleUrl);
								url.searchParams.set("planner_retry", String(index));
								return import(
									/* @vite-ignore */ url.href
								) as Promise<SceneModule>;
							})();
			const current = request.catch((error: unknown) => {
				if (pending === current) pending = null;
				throw error;
			});
			pending = current;
			return current;
		};
		loaders.set(moduleUrl, load);
	}
	return load();
}
