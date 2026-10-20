/**
 * What the page tells the configurator through its mount point.
 *
 * The PHP that prints `<div data-linker-app="configurator">` sets:
 * - `data-engine-url`: base URL of the Solution Configurator engine;
 * - `data-rest-url`: the WordPress REST root (Store API and linker/v1);
 * - `data-rest-nonce`: a `wp_rest` nonce for linker/v1/solutions;
 * - `data-step="roof"`: optional, opens the roof step first
 *   (/solution-configurator/?step=roof, docs/specs/12-site-chrome.md).
 * - size-hint fields the address already names, and only when they differ
 *   from the residential form's empty defaults (Mount.php; the keys are the
 *   ones SizeHint::execute writes): `data-pv-kwp`, `data-annual-kwh`,
 *   `data-phase` (`1` only; `3` is the default), `data-backup` (`needed` or
 *   `needed_accessory_ok`; `none` is the default), `data-plz`.
 * The language follows the page's `lang` attribute.
 */

/**
 * Internal dependencies
 */
import type { Locale } from './types';
import type { ResidentialValues } from './residential/ResidentialForm';

export interface Config {
	engineUrl: string;
	restUrl: string;
	restNonce: string;
	locale: Locale;
	openRoof: boolean;
	/**
	 * Residential fields carried from a size-hint address. Absent keys keep
	 * the form's empty defaults, including phase `3` and backup `none`.
	 */
	defaults?: Partial< ResidentialValues >;
}

export function pageLocale( doc: Document = document ): Locale {
	return doc.documentElement.lang.toLowerCase().startsWith( 'de' )
		? 'de'
		: 'en';
}

export function readConfig( element: HTMLElement ): Config {
	const data = element.dataset;
	return {
		engineUrl: ( data.engineUrl ?? '' ).replace( /\/$/, '' ),
		restUrl: ( data.restUrl ?? '/wp-json/' ).replace( /\/?$/, '/' ),
		restNonce: data.restNonce ?? '',
		locale: pageLocale( element.ownerDocument ),
		openRoof: data.step === 'roof',
		defaults: sizeHintDefaults( data ),
	};
}

/**
 * Maps the mount's size-hint attributes onto the residential form.
 * A value equal to the empty default is left out, so it does not count as a prefill.
 *
 * @param data The mount element's dataset.
 */
function sizeHintDefaults( data: DOMStringMap ): Partial< ResidentialValues > {
	const defaults: Partial< ResidentialValues > = {};
	const pv = positiveDecimal( data.pvKwp );
	if ( pv ) {
		defaults.pv_kwp = pv;
	}
	const annual = positiveDecimal( data.annualKwh );
	if ( annual ) {
		defaults.annual_kwh = annual;
	}
	if ( data.phase === '1' ) {
		defaults.phase = '1';
	}
	if ( data.backup === 'needed' || data.backup === 'needed_accessory_ok' ) {
		defaults.backup = data.backup;
	}
	if ( data.plz && /^[0-9]{5}$/.test( data.plz ) ) {
		defaults.plz = data.plz;
	}
	return defaults;
}

/**
 * A positive decimal in the spelling SizeHint writes (`10`, `10.5`), or nothing.
 *
 * @param value The attribute text, when the mount printed one.
 */
function positiveDecimal( value: string | undefined ): string | undefined {
	if ( ! value || ! /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test( value ) ) {
		return undefined;
	}
	const number = Number( value );
	if ( ! Number.isFinite( number ) || number <= 0 ) {
		return undefined;
	}
	return value;
}
