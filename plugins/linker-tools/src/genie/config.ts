/**
 * What the dock tells the Genie app through its mount point.
 *
 * PHP prints `<div data-linker-app="genie" …>` (includes/Genie/Entries.php):
 * - `data-locale`: `en` or `de`;
 * - `data-page-type`: category | product | draft | account | other;
 * - `data-turn-url`: the REST proxy route (linker-ai/v1/genie/turn);
 * - `data-thread-url`: the route that reads the stored thread back
 *   (linker-ai/v1/genie/conversation);
 * - `data-vote-url`: the proxy's vote route base (…/genie/turn/<id>/vote);
 * - `data-rest-url`: the WordPress REST root (Store API, linker/v1);
 * - `data-rest-nonce`: a `wp_rest` nonce for the proxy and linker/v1;
 * - `data-disclosure`: the AI disclosure sentence, spoken once;
 * - `data-account-url`: the account page (view_inquiry links here);
 * - `data-prompts`: JSON list of opening prompts for the page type.
 *
 * The catalogue search box's Ask Genie chip (assets/search-ask.js) leaves the
 * text it was clicked for on this mount as `data-pending-ask` before it boots
 * the app: the app picks it up on its first mount and clears it.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../configurator/types';

export interface GenieConfig {
	locale: Locale;
	pageType: string;
	turnUrl: string;
	threadUrl: string;
	voteUrl: string;
	restUrl: string;
	restNonce: string;
	disclosure: string;
	accountUrl: string;
	prompts: string[];
	pendingAsk: string;
}

export function readConfig( element: HTMLElement ): GenieConfig {
	const data = element.dataset;
	const pendingAsk = data.pendingAsk ?? '';
	if ( '' !== pendingAsk ) {
		delete element.dataset.pendingAsk;
	}
	return {
		locale: data.locale === 'de' ? 'de' : 'en',
		pageType: data.pageType ?? 'other',
		turnUrl: data.turnUrl ?? '/wp-json/linker-ai/v1/genie/turn',
		threadUrl: data.threadUrl ?? '/wp-json/linker-ai/v1/genie/conversation',
		voteUrl: data.voteUrl ?? '/wp-json/linker-ai/v1/genie/turn',
		restUrl: ( data.restUrl ?? '/wp-json/' ).replace( /\/?$/, '/' ),
		restNonce: data.restNonce ?? '',
		disclosure: data.disclosure ?? '',
		accountUrl: data.accountUrl ?? '',
		prompts: data.prompts ? JSON.parse( data.prompts ) : [],
		pendingAsk,
	};
}
