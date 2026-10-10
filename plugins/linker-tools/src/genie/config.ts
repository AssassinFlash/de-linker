/**
 * What the dock tells the Genie app through its mount point.
 *
 * PHP prints `<div data-linker-app="genie" …>` (includes/Genie/Entries.php):
 * - `data-locale`: `en` or `de`;
 * - `data-page-type`: category | product | draft | account | other;
 * - `data-turn-url`: the REST proxy route (linker-ai/v1/genie/turn);
 * - `data-vote-url`: the proxy's vote route base (…/genie/turn/<id>/vote);
 * - `data-rest-url`: the WordPress REST root (Store API, linker/v1);
 * - `data-rest-nonce`: a `wp_rest` nonce for the proxy and linker/v1;
 * - `data-disclosure`: the AI disclosure sentence, spoken once;
 * - `data-account-url`: the account page (view_inquiry links here);
 * - `data-prompts`: JSON list of opening prompts for the page type.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../configurator/types';

export interface GenieConfig {
	locale: Locale;
	pageType: string;
	turnUrl: string;
	voteUrl: string;
	restUrl: string;
	restNonce: string;
	disclosure: string;
	accountUrl: string;
	prompts: string[];
}

export function readConfig( element: HTMLElement ): GenieConfig {
	const data = element.dataset;
	return {
		locale: data.locale === 'de' ? 'de' : 'en',
		pageType: data.pageType ?? 'other',
		turnUrl: data.turnUrl ?? '/wp-json/linker-ai/v1/genie/turn',
		voteUrl: data.voteUrl ?? '/wp-json/linker-ai/v1/genie/turn',
		restUrl: ( data.restUrl ?? '/wp-json/' ).replace( /\/?$/, '/' ),
		restNonce: data.restNonce ?? '',
		disclosure: data.disclosure ?? '',
		accountUrl: data.accountUrl ?? '',
		prompts: data.prompts ? JSON.parse( data.prompts ) : [],
	};
}
