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

interface GeocoderAddressComponent {
	long_name: string;
	short_name: string;
	types: string[];
}

interface GeocoderResult {
	formatted_address?: string;
	address_components?: GeocoderAddressComponent[];
	geometry?: {
		location?: {
			lat(): number;
			lng(): number;
		};
	};
}

interface GeocoderRequest {
	address: string;
	region?: string;
	componentRestrictions?: { country: string };
	fulfillOnZeroResults?: boolean;
}

interface GoogleMapsApi {
	importLibrary(name: "maps3d"): Promise<Maps3DLibrary>;
	importLibrary(name: "geocoding"): Promise<{
		Geocoder: new () => {
			geocode(request: GeocoderRequest): Promise<{
				results: GeocoderResult[];
			}>;
		};
	}>;
	Geocoder?: new () => {
		geocode(request: GeocoderRequest): Promise<{
			results: GeocoderResult[];
		}>;
	};
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
		const fail = (reason: string) => {
			if (settled) return;
			settled = true;
			clearTimeout(timer);
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
			prior.addEventListener("load", succeed, { once: true });
			prior.addEventListener("error", () => fail("google_maps_load_error"), {
				once: true,
			});
			return;
		}
		const script = document.createElement("script");
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

export interface GeocodedPlace {
	readonly lat: number;
	readonly lng: number;
	readonly postcode: string | null;
	readonly countryCode: string | null;
	readonly formattedAddress: string;
}

export async function geocodeAddress(
	apiKey: string,
	query: string,
	countryCode?: string,
): Promise<GeocodedPlace | null> {
	const trimmed = query.trim();
	if (!trimmed || !apiKey) return null;
	const maps = await loadGoogleMaps(apiKey);
	const Geocoder =
		maps.Geocoder ?? (await maps.importLibrary("geocoding")).Geocoder;
	const geocoder = new Geocoder();
	const { results } = await geocoder.geocode({
		address: trimmed,
		fulfillOnZeroResults: true,
		// Region only biases a result; the selected country must restrict it.
		// https://developers.google.com/maps/documentation/javascript/geocoding#ComponentFiltering
		...(countryCode ? { componentRestrictions: { country: countryCode } } : {}),
	});
	const first = results[0];
	const location = first?.geometry?.location;
	if (!first || !location) return null;
	const components = first.address_components ?? [];
	const postcode =
		components.find((c) => c.types.includes("postal_code"))?.short_name ?? null;
	const country =
		components.find((c) => c.types.includes("country"))?.short_name ?? null;
	if (countryCode && country !== countryCode.toUpperCase()) return null;
	return {
		lat: location.lat(),
		lng: location.lng(),
		postcode,
		countryCode: country && /^[A-Z]{2}$/.test(country) ? country : null,
		formattedAddress: first.formatted_address ?? trimmed,
	};
}
