import { readObject } from "./readProtocol.ts";

export interface Configuration {
	readonly baseUrl: string;
	readonly nonceUrl: string;
	readonly locale: string;
	readonly countries: Readonly<Record<string, string>>;
	readonly sceneModuleUrl?: string | null;
	readonly mapModuleUrl?: string | null;
}
export function readConfiguration(
	element: HTMLElement,
	entryModuleUrl: string,
): Configuration {
	const data = readObject(JSON.parse(element.dataset.plannerConfig ?? "null"));
	if (
		typeof data.base_url !== "string" ||
		typeof data.nonce_url !== "string" ||
		typeof data.locale !== "string"
	)
		throw new Error("invalid_planner_configuration");
	const countries = readObject(data.countries);
	if (
		!Object.entries(countries).every(
			([code, label]) => /^[A-Z]{2}$/.test(code) && typeof label === "string",
		)
	)
		throw new Error("invalid_planner_countries");
	function reviewedModule(field: string, prefix: string): string | null {
		const value = data[field + "_module_url"];
		if (value === undefined || value === null) return null;
		const error = "invalid_planner_" + field + "_module";
		if (typeof value !== "string") throw new Error(error);
		const asset = new URL(value, element.baseURI);
		const entryDirectory = new URL(".", entryModuleUrl);
		if (
			asset.origin !== entryDirectory.origin ||
			new URL(".", asset).href !== entryDirectory.href ||
			asset.username ||
			asset.password ||
			// Empty ?/# delimiters are also forbidden by complete URL equality.
			asset.href !== asset.origin + asset.pathname ||
			!new RegExp("^" + prefix + "-[a-zA-Z0-9_-]+\\.js$").test(
				asset.pathname.slice(entryDirectory.pathname.length),
			)
		)
			throw new Error(error);
		return asset.href;
	}

	return {
		baseUrl: data.base_url,
		nonceUrl: data.nonce_url,
		locale: data.locale.replaceAll("_", "-").replace("-formal", ""),
		countries: countries as Record<string, string>,
		sceneModuleUrl: reviewedModule("scene", "SceneViewport"),
		mapModuleUrl: reviewedModule("map", "MapViewport"),
	};
}
