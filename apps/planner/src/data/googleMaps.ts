import type { Brief } from "../domain/brief.ts";
import type { Configuration } from "./config.ts";
export interface LatLngLiteral {
	lat: number;
	lng: number;
}

export interface LatLngAltitudeLiteral extends LatLngLiteral {
	altitude?: number;
}

export interface Map3DElementInstance extends HTMLElement {
	center: LatLngAltitudeLiteral;
	range: number;
	tilt: number;
	heading: number;
	mode: "SATELLITE" | "HYBRID" | "ROADMAP";
	gestureHandling?: "AUTO" | "COOPERATIVE" | "GREEDY";
	defaultUIHidden?: boolean;
	flyCameraTo?: (options: {
		endCamera: {
			center?: LatLngAltitudeLiteral;
			range?: number;
			tilt?: number;
			heading?: number;
		};
		durationMillis?: number;
	}) => void;
}

export interface Polygon3DElementInstance extends HTMLElement {
	path?: Iterable<LatLngAltitudeLiteral | LatLngLiteral>;
	innerPaths?: Iterable<Iterable<LatLngAltitudeLiteral | LatLngLiteral>>;
	altitudeMode?:
		"ABSOLUTE" | "CLAMP_TO_GROUND" | "RELATIVE_TO_GROUND" | "RELATIVE_TO_MESH";
	extruded?: boolean;
	drawsOccludedSegments?: boolean;
	fillColor?: string;
	strokeColor?: string;
	strokeWidth?: number;
	zIndex?: number;
}

export interface Marker3DElementInstance extends HTMLElement {
	position?: LatLngAltitudeLiteral | LatLngLiteral;
	altitudeMode?:
		"ABSOLUTE" | "CLAMP_TO_GROUND" | "RELATIVE_TO_GROUND" | "RELATIVE_TO_MESH";
	label?: string;
}

export interface Maps3DLibrary {
	Map3DElement: new (options?: {
		center?: LatLngAltitudeLiteral;
		range?: number;
		tilt?: number;
		heading?: number;
		mode?: "SATELLITE" | "HYBRID" | "ROADMAP";
		gestureHandling?: "AUTO" | "COOPERATIVE" | "GREEDY";
		defaultUIHidden?: boolean;
	}) => Map3DElementInstance;
	Polygon3DElement: new (options?: {
		altitudeMode?: Polygon3DElementInstance["altitudeMode"];
		extruded?: boolean;
		drawsOccludedSegments?: boolean;
		fillColor?: string;
		strokeColor?: string;
		strokeWidth?: number;
		zIndex?: number;
	}) => Polygon3DElementInstance;
	Polygon3DInteractiveElement: new (options?: {
		altitudeMode?: Polygon3DElementInstance["altitudeMode"];
		extruded?: boolean;
		drawsOccludedSegments?: boolean;
		fillColor?: string;
		strokeColor?: string;
		strokeWidth?: number;
		zIndex?: number;
	}) => Polygon3DElementInstance;
	Marker3DElement: new (options?: {
		position?: LatLngAltitudeLiteral | LatLngLiteral;
		altitudeMode?: Marker3DElementInstance["altitudeMode"];
		label?: string;
	}) => Marker3DElementInstance;
}

interface GoogleMapsApi {
	importLibrary(name: "maps3d"): Promise<Maps3DLibrary>;
}

declare global {
	interface Window {
		google?: {
			maps?: GoogleMapsApi;
		};
	}
}

const LOAD_TIMEOUT_MS = 15_000;
let loadedKey: string | null = null;
let loadingPromise: Promise<GoogleMapsApi> | null = null;

export function loadGoogleMaps(apiKey: string): Promise<GoogleMapsApi> {
	const existing = window.google?.maps;
	if (existing && typeof existing.importLibrary === "function") {
		loadedKey = apiKey;
		return Promise.resolve(existing);
	}
	if (loadingPromise && loadedKey === apiKey) return loadingPromise;
	loadedKey = apiKey;
	loadingPromise = new Promise<GoogleMapsApi>((resolve, reject) => {
		let settled = false;
		// A script whose load/error already fired never fires either again, so a
		// failed request must remove its element: the next call appends a fresh
		// script instead of re-arming listeners on dead events.
		let script: HTMLScriptElement | null = null;
		const fail = (reason: string) => {
			if (settled) return;
			settled = true;
			clearTimeout(timer);
			script?.remove();
			loadingPromise = null;
			reject(new Error(reason));
		};
		const succeed = () => {
			if (settled) return;
			const maps = window.google?.maps;
			if (!maps || typeof maps.importLibrary !== "function") {
				fail("google_maps_unavailable");
				return;
			}
			settled = true;
			clearTimeout(timer);
			resolve(maps);
		};
		const timer = setTimeout(
			() => fail("google_maps_timeout"),
			LOAD_TIMEOUT_MS,
		);
		const prior = document.querySelector<HTMLScriptElement>(
			'script[data-linker-google-maps="1"]',
		);
		if (prior) {
			script = prior;
			prior.addEventListener("load", succeed, { once: true });
			prior.addEventListener("error", () => fail("google_maps_load_error"), {
				once: true,
			});
			return;
		}
		script = document.createElement("script");
		script.async = true;
		script.defer = true;
		script.dataset.linkerGoogleMaps = "1";
		script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&v=beta&libraries=maps3d`;
		script.addEventListener("load", succeed, { once: true });
		script.addEventListener("error", () => fail("google_maps_load_error"), {
			once: true,
		});
		document.head.append(script);
	});
	return loadingPromise;
}

export async function locateProjectSite(
	site: Brief["site"],
	config: Pick<Configuration, "googleMapsApiKey" | "locale">,
): Promise<Brief["site"] | null> {
	if (!config.googleMapsApiKey || !site.country_code) return null;
	const place = await geocodeAddress(
		config.googleMapsApiKey,
		site.location_label,
		site.country_code,
		config.locale,
	);
	return (
		place && {
			...site,
			location_label: place.formattedAddress,
			latitude: place.lat,
			longitude: place.lng,
			postal_code: place.postcode,
			coordinate_basis: "user_entered",
		}
	);
}

export interface GeocodedPlace {
	readonly lat: number;
	readonly lng: number;
	readonly postcode: string | null;
	readonly countryCode: string | null;
	readonly formattedAddress: string;
}

interface GooglePlace {
	formattedAddress?: string;
	addressComponents?: { shortText: string; types: string[] }[];
	location?: { latitude: number; longitude: number };
}

export async function geocodeAddress(
	apiKey: string,
	query: string,
	countryCode: string | undefined,
	locale: string,
): Promise<GeocodedPlace | null> {
	const trimmed = query.trim();
	if (!trimmed || !apiKey) return null;
	// Places API (New) is enabled for this site's key; Geocoding API is not.
	// https://developers.google.com/maps/documentation/places/web-service/text-search
	const response = await fetch(
		"https://places.googleapis.com/v1/places:searchText",
		{
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Goog-Api-Key": apiKey,
				"X-Goog-FieldMask":
					"places.formattedAddress,places.location,places.addressComponents",
			},
			body: JSON.stringify({
				textQuery: trimmed,
				languageCode: locale.toLowerCase().startsWith("de") ? "de" : "en",
				...(countryCode ? { regionCode: countryCode.toUpperCase() } : {}),
			}),
		},
	);
	if (!response.ok) throw new Error(`google_places_${response.status}`);
	const payload: { places?: GooglePlace[] } = await response.json();
	const places = payload.places ?? [];
	// regionCode biases the search but does not restrict the returned country.
	const first = countryCode
		? places.find((place) =>
				place.addressComponents?.some(
					(component) =>
						component.types.includes("country") &&
						component.shortText === countryCode.toUpperCase(),
				),
			)
		: places[0];
	const location = first?.location;
	if (!first || !location) return null;
	const components = first.addressComponents ?? [];
	const postcode =
		components.find((c) => c.types.includes("postal_code"))?.shortText ?? null;
	const country =
		components.find((c) => c.types.includes("country"))?.shortText ?? null;
	return {
		lat: location.latitude,
		lng: location.longitude,
		postcode,
		countryCode: country && /^[A-Z]{2}$/.test(country) ? country : null,
		formattedAddress: first.formattedAddress ?? trimmed,
	};
}
