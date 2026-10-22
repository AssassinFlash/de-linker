import { readObject } from "./readProtocol.ts";

export interface Configuration {
	readonly baseUrl: string;
	readonly nonceUrl: string;
	readonly locale: string;
	readonly countries: Readonly<Record<string, string>>;
}
export function readConfiguration(element: HTMLElement): Configuration {
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
	return {
		baseUrl: data.base_url,
		nonceUrl: data.nonce_url,
		locale: data.locale.replaceAll("_", "-").replace("-formal", ""),
		countries: countries as Record<string, string>,
	};
}
