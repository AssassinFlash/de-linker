/** One explicit fallback navigation carries only the customer's unsent text. */
const KEY = 'linker-genie-inquiry-handoff';
// #521 recovery recommendation: one navigation, no longer than the 300 s proof window.
const LIFETIME = 300_000;

/**
 * @param url     Native request page.
 * @param message Current unsent customer text.
 */
export function rememberInquiry( url: string, message: string ): void {
	try {
		const target = new URL( url, window.location.href );
		if ( target.origin !== window.location.origin || ! message.trim() ) {
			return;
		}
		window.sessionStorage.setItem(
			KEY,
			JSON.stringify( {
				path: target.pathname,
				message,
				expires: Date.now() + LIFETIME,
			} )
		);
	} catch {
		// A browser can disable storage; the original composer still retains the text.
	}
}

/** Restore once, through the existing native form's ordinary untrusted input. */
export function restoreInquiry(): void {
	const field =
		document.querySelector< HTMLTextAreaElement >( '#inquiry-message' );
	if ( ! field ) {
		return;
	}
	try {
		const raw = window.sessionStorage.getItem( KEY );
		window.sessionStorage.removeItem( KEY );
		const saved: unknown = raw ? JSON.parse( raw ) : null;
		if (
			! saved ||
			typeof saved !== 'object' ||
			! ( 'message' in saved ) ||
			typeof saved.message !== 'string' ||
			! ( 'path' in saved ) ||
			saved.path !== window.location.pathname ||
			! ( 'expires' in saved ) ||
			typeof saved.expires !== 'number' ||
			saved.expires <= Date.now() ||
			saved.expires > Date.now() + LIFETIME ||
			field.value !== field.defaultValue
		) {
			return;
		}
		field.value = saved.message;
		field.dispatchEvent( new Event( 'input', { bubbles: true } ) );
	} catch {
		// Corrupt/disabled storage does not change the native form or its controls.
	}
}
