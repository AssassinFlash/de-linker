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

declare global {
	interface Window {
		getCkyConsent?: () => { isUserActionCompleted: boolean };
	}
}

export function onMapConsentChange(revoke: () => void): () => void {
	function cookieYesChanged() {
		// CookieYes also announces its initial defaults on every first-visit page.
		if (window.getCkyConsent?.().isUserActionCompleted !== false) revoke();
	}
	document.addEventListener("cookieyes_consent_update", cookieYesChanged);
	document.addEventListener("wp_listen_for_consent_change", revoke);
	return () => {
		document.removeEventListener("cookieyes_consent_update", cookieYesChanged);
		document.removeEventListener("wp_listen_for_consent_change", revoke);
	};
}
