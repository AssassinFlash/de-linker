/** Keep one successful module identity; a rejected browser URL needs a new
 * explicit retry URL. Callers supply only native, validated build metadata. */
export function retryableModule<T>(initial: () => Promise<T>) {
	const loaders = new Map<string | null, () => Promise<T>>();
	return (moduleUrl: string | null): Promise<T> => {
		let load = loaders.get(moduleUrl);
		if (!load) {
			let attempt = 0;
			let pending: Promise<T> | null = null;
			load = () => {
				if (pending) return pending;
				const index = attempt++;
				const request =
					index === 0
						? initial()
						: moduleUrl === null
							? Promise.reject(new Error("viewport_module_url_missing"))
							: (() => {
									const url = new URL(moduleUrl);
									url.searchParams.set("planner_retry", String(index));
									return import(/* @vite-ignore */ url.href) as Promise<T>;
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
	};
}
