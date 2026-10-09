/**
 * What the page tells the configurator through its mount point.
 *
 * The PHP that prints `<div data-linker-app="configurator">` sets:
 * - `data-engine-url`: base URL of the Solution Configurator engine;
 * - `data-rest-url`: the WordPress REST root (Store API and linker/v1);
 * - `data-rest-nonce`: a `wp_rest` nonce for linker/v1/solutions;
 * - `data-step="roof"`: optional, opens the roof step first
 *   (/linker-planner/?step=roof, docs/specs/12-site-chrome.md).
 * The language follows the page's `lang` attribute.
 */

/**
 * Internal dependencies
 */
import type { Locale } from './types';

export interface Config {
	engineUrl: string;
	restUrl: string;
	restNonce: string;
	locale: Locale;
	openRoof: boolean;
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
	};
}
