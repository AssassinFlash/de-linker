import { readObject } from "./readProtocol.ts";

export interface Configuration {
	readonly baseUrl: string;
	readonly nonceUrl: string;
	readonly locale: string;
	readonly countries: Readonly<Record<string, string>>;
	readonly sceneModuleUrl?: string | null;
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
	let sceneModuleUrl: string | null = null;
	if (data.scene_module_url !== undefined && data.scene_module_url !== null) {
		if (typeof data.scene_module_url !== "string")
			throw new Error("invalid_planner_scene_module");
		const asset = new URL(data.scene_module_url, element.baseURI);
		const entryDirectory = new URL(".", entryModuleUrl);
		if (
			asset.origin !== entryDirectory.origin ||
			new URL(".", asset).href !== entryDirectory.href ||
			asset.username ||
			asset.password ||
			asset.search ||
			asset.hash ||
			!/^SceneViewport-[a-zA-Z0-9_-]+\.js$/.test(
				asset.pathname.slice(entryDirectory.pathname.length),
			)
		)
			throw new Error("invalid_planner_scene_module");
		sceneModuleUrl = asset.href;
	}
	return {
		baseUrl: data.base_url,
		nonceUrl: data.nonce_url,
		locale: data.locale.replaceAll("_", "-").replace("-formal", ""),
		countries: countries as Record<string, string>,
		sceneModuleUrl,
	};
}
