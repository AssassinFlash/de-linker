/**
 * What the dock tells the Genie app through its mount point.
 *
 * PHP prints `<div data-linker-app="genie" …>` (includes/Genie/Entries.php):
 * - `data-locale`: `en` or `de`;
 * - `data-surface`: `helper` in the dock, `workspace` on /linker-advisor/;
 * - `data-page-type`: category | product | draft | account | other;
 * - `data-product-id`: the product page's id, 0 elsewhere;
 * - `data-turn-url`: the REST proxy route (linker-ai/v1/genie/turn);
 * - `data-thread-url`: the route that reads the stored thread back
 *   (linker-ai/v1/genie/conversation);
 * - `data-conversations-url`: the history rail
 *   (linker-ai/v1/genie/conversations);
 * - `data-workspace-url`: the advisor page, where the helper continues;
 * - `data-vote-url`: the proxy's vote route base (…/genie/turn/<id>/vote);
 * - `data-rest-url`: the WordPress REST root (Store API, linker/v1);
 * - `data-rest-nonce`: a `wp_rest` nonce for the proxy and linker/v1;
 * - `data-disclosure`: the AI disclosure sentence, spoken once;
 * - `data-account-url`: the account page (view_inquiry links here);
 * - `data-prompts`: JSON list of opening prompts for the page type.
 *
 * Opening and pending questions use the dock loader's ready/open handshake,
 * not configuration read from the mount.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../configurator/types';

export interface GenieConfig {
	surface: 'helper' | 'workspace';
	locale: Locale;
	pageType: string;
	productId: number;
	turnUrl: string;
	threadUrl: string;
	conversationsUrl: string;
	voteUrl: string;
	restUrl: string;
	restNonce: string;
	disclosure: string;
	accountUrl: string;
	workspaceUrl: string;
	prompts: string[];
}

export function readConfig( element: HTMLElement ): GenieConfig {
	const data = element.dataset;
	return {
		surface: data.surface === 'workspace' ? 'workspace' : 'helper',
		locale: data.locale === 'de' ? 'de' : 'en',
		pageType: data.pageType ?? 'other',
		productId: Number( data.productId ) || 0,
		turnUrl: data.turnUrl ?? '/wp-json/linker-ai/v1/genie/turn',
		threadUrl: data.threadUrl ?? '/wp-json/linker-ai/v1/genie/conversation',
		conversationsUrl:
			data.conversationsUrl ??
			'/wp-json/linker-ai/v1/genie/conversations',
		voteUrl: data.voteUrl ?? '/wp-json/linker-ai/v1/genie/turn',
		restUrl: ( data.restUrl ?? '/wp-json/' ).replace( /\/?$/, '/' ),
		restNonce: data.restNonce ?? '',
		disclosure: data.disclosure ?? '',
		accountUrl: data.accountUrl ?? '',
		workspaceUrl: data.workspaceUrl ?? '/linker-advisor/',
		prompts: data.prompts ? JSON.parse( data.prompts ) : [],
	};
}
