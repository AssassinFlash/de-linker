/** One explicit fallback navigation carries only the customer's unsent text. */
import type { GenieConfig } from '../genie/config';
import { nativeScope } from '../genie/shared/nativeScope';

const PREFIX = 'linker-genie-inquiry-handoff:v2:';
// #521 recovery recommendation: one navigation, no longer than the 300 s proof window.
const LIFETIME = 300_000;
type Config = Pick< GenieConfig, 'restUrl' | 'restNonce' >;
interface Handoff {
	v: 2;
	scope: string;
	path: string;
	message: string;
	expires: number;
}

function readRecord( raw: string | null, scope: string ): Handoff | null {
	if ( ! raw ) {
		return null;
	}
	const value: unknown = JSON.parse( raw );
	if ( ! value || typeof value !== 'object' ) {
		return null;
	}
	const record = value as Partial< Handoff >;
	return record.v === 2 &&
		record.scope === scope &&
		typeof record.path === 'string' &&
		record.path.startsWith( '/' ) &&
		! record.path.startsWith( '//' ) &&
		typeof record.message === 'string' &&
		!! record.message.trim() &&
		typeof record.expires === 'number' &&
		Number.isFinite( record.expires )
		? ( record as Handoff )
		: null;
}

function nativeConfig(): Config | null {
	const mount = document.querySelector< HTMLElement >(
		'[data-linker-app="genie"]'
	);
	if ( ! mount?.dataset.restUrl || ! mount.dataset.restNonce ) {
		return null;
	}
	return {
		restUrl: mount.dataset.restUrl.replace( /\/?$/, '/' ),
		restNonce: mount.dataset.restNonce,
	};
}

/**
 * @param url     Native request page.
 * @param message Current unsent customer text.
 * @param scope   The already accepted editor's immutable native owner.
 */
export function rememberInquiry(
	url: string,
	message: string,
	scope: string
): boolean {
	if ( ! /^[a-f0-9]{64}$/.test( scope ) ) {
		return false;
	}
	try {
		const target = new URL( url, window.location.href );
		if ( target.origin !== window.location.origin ) {
			return false;
		}
		const key = PREFIX + scope;
		const storage = window.sessionStorage;
		const raw = storage.getItem( key );
		if ( raw !== null && ! readRecord( raw, scope ) ) {
			return false;
		}
		if ( ! message.trim() ) {
			if ( storage.getItem( key ) !== raw ) {
				return false;
			}
			storage.removeItem( key );
			return storage.getItem( key ) === null;
		}
		const encoded = JSON.stringify( {
			v: 2,
			scope,
			path: target.pathname,
			message,
			expires: Date.now() + LIFETIME,
		} );
		if ( storage.getItem( key ) !== raw ) {
			return false;
		}
		storage.setItem( key, encoded );
		return storage.getItem( key ) === encoded;
	} catch {
		// A browser can disable storage; the original composer still retains the text.
		return false;
	}
}

/**
 * Restore only a fresh verified owner through the native form's untrusted input.
 * @param config Native routes/nonce; the existing footer mount supplies them by default.
 */
export async function restoreInquiry( config?: Config ): Promise< void > {
	const field =
		document.querySelector< HTMLTextAreaElement >( '#inquiry-message' );
	const routes = config ?? nativeConfig();
	if ( ! field || ! routes || field.value !== field.defaultValue ) {
		return;
	}
	const initialValue = field.value;
	const initialDefault = field.defaultValue;
	const retainsSubmission = () =>
		field.form?.querySelector< HTMLInputElement >(
			'input[name="linker_inquiry_retained"]'
		)?.value === '1';
	const path = window.location.pathname;
	let edited = false;
	const onEdit = () => {
		edited = true;
	};
	field.addEventListener( 'input', onEdit );
	field.addEventListener( 'change', onEdit );
	try {
		const storage = window.sessionStorage;
		// Snapshot exact bytes without parsing foreign owners before the native await.
		// A newly created/revised slot during that await belongs to a later operation.
		const snapshot = new Map< string, string >();
		for ( let index = 0; index < storage.length; index++ ) {
			const key = storage.key( index );
			if ( key?.startsWith( PREFIX ) ) {
				const raw = storage.getItem( key );
				if ( raw !== null ) {
					snapshot.set( key, raw );
				}
			}
		}
		if ( snapshot.size === 0 ) {
			return;
		}
		const retained = retainsSubmission();
		const identity = await nativeScope( routes, true );
		const key = PREFIX + identity.scope;
		const raw = snapshot.get( key );
		if (
			! identity.persistent ||
			raw === undefined ||
			storage.getItem( key ) !== raw ||
			window.location.pathname !== path ||
			! field.isConnected ||
			document.querySelector( '#inquiry-message' ) !== field ||
			edited ||
			field.value !== initialValue ||
			field.defaultValue !== initialDefault ||
			retainsSubmission() !== retained
		) {
			return;
		}
		const saved = readRecord( raw, identity.scope );
		if ( ! saved || storage.getItem( key ) !== raw ) {
			return;
		}
		// Only the verified owner's exact navigation is consumed, including expiry
		// or a different destination. Legacy/foreign/unknown records stay untouched.
		storage.removeItem( key );
		if (
			storage.getItem( key ) !== null ||
			retained ||
			initialValue !== '' ||
			initialDefault !== '' ||
			saved.path !== path ||
			saved.expires <= Date.now() ||
			saved.expires > Date.now() + LIFETIME
		) {
			return;
		}
		field.value = saved.message;
		field.dispatchEvent( new Event( 'input', { bubbles: true } ) );
	} catch {
		// Corrupt/disabled storage does not change the native form or its controls.
	} finally {
		field.removeEventListener( 'input', onEdit );
		field.removeEventListener( 'change', onEdit );
	}
}
