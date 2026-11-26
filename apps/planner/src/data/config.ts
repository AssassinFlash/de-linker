import { readObject } from "./readProtocol.ts";

export interface Configuration {
	readonly baseUrl: string;
	readonly nonceUrl: string;
	readonly locale: string;
	readonly hasWorkspaceSession?: boolean;
	readonly inquiryUrl?: string | null;
	readonly contactMailbox?: string | null;
	readonly whatsappUrl?: string | null;
	readonly mapStyleUrl?: string | null;
	readonly countries: Readonly<Record<string, string>>;
	readonly sceneModuleUrl?: string | null;
	readonly mapModuleUrl?: string | null;
	readonly googleMapsApiKey?: string | null;
}
export function readConfiguration(
	element: HTMLElement,
	entryModuleUrl: string,
): Configuration {
	const data = readObject(JSON.parse(element.dataset.plannerConfig ?? "null"));
	if (
		typeof data.base_url !== "string" ||
		// Absent for a guest: the endpoint only answers a signed-in cookie, so
		// the server does not offer it. A guest that carries one anyway is
		// still valid — the client handles the `400`/`0` answer.
		(data.nonce_url !== null &&
			data.nonce_url !== undefined &&
			typeof data.nonce_url !== "string") ||
		typeof data.locale !== "string"
	)
		throw new Error("invalid_planner_configuration");
	const rawGoogleKey = data.google_maps_api_key;
	if (
		rawGoogleKey !== undefined &&
		rawGoogleKey !== null &&
		typeof rawGoogleKey !== "string"
	)
		throw new Error("invalid_planner_configuration");
	const googleMapsApiKey =
		typeof rawGoogleKey === "string" &&
		/^[A-Za-z0-9_-]{20,80}$/.test(rawGoogleKey.trim())
			? rawGoogleKey.trim()
			: null;
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
		nonceUrl: typeof data.nonce_url === "string" ? data.nonce_url : "",
		locale: data.locale.replaceAll("_", "-").replace("-formal", ""),
		hasWorkspaceSession: data.has_workspace_session === true,
		inquiryUrl: typeof data.inquiry_url === "string" ? data.inquiry_url : null,
		contactMailbox:
			typeof data.contact_mailbox === "string" ? data.contact_mailbox : null,
		whatsappUrl:
			typeof data.whatsapp_url === "string" ? data.whatsapp_url : null,
		mapStyleUrl:
			typeof data.map_style_url === "string" ? data.map_style_url : null,
		countries: countries as Record<string, string>,
		sceneModuleUrl: reviewedModule("scene", "SceneViewport"),
		mapModuleUrl: reviewedModule("map", "MapViewport"),
		googleMapsApiKey,
	};
}
