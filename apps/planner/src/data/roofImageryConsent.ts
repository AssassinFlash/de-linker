import { imagerySourceKey, type PlaceImagery } from "../domain/place.ts";

const storageKey = "linker-roof-imagery-choice";

export function allowRoofImagery(
	projectId: string,
	source: PlaceImagery,
): void {
	try {
		window.sessionStorage.setItem(
			storageKey,
			JSON.stringify([projectId, imagerySourceKey(source)]),
		);
	} catch {
		// A browser that blocks storage can offer the source again inside the map.
	}
}

export function clearRoofImageryConsent(): void {
	try {
		window.sessionStorage.removeItem(storageKey);
	} catch {
		// No stored permission is available in this browser.
	}
}

export function takeRoofImageryConsent(
	projectId: string,
	source: PlaceImagery,
): boolean {
	try {
		const choice = window.sessionStorage.getItem(storageKey);
		window.sessionStorage.removeItem(storageKey);
		return choice === JSON.stringify([projectId, imagerySourceKey(source)]);
	} catch {
		return false;
	}
}
