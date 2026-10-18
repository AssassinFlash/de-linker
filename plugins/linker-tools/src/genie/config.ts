/**
 * What the dock tells the Genie app through its mount point.
 *
 * PHP prints `<div data-linker-app="genie" …>` (includes/Genie/Entries.php):
 * - `data-locale`: `en` or `de`;
 * - `data-surface`: `helper` in the dock, `workspace` on /genie/;
 * - `data-page-type`: home | product | category | solution | blog | faq |
 *   draft | account | other;
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
 * - `data-prompts`: JSON list of opening prompts for the page;
 * - `data-page`: JSON page context (type, url, title and the IDs of what the
 *   page shows), sent back with every turn (#234, PageContext.php);
 * - `data-signed-in`: `1` for a signed-in visitor, whose conversation is
 *   emailed to the account's address (no address field);
 * - `data-retention-days`: how long a guest's conversations are kept
 *   (Retention::RETENTION_DAYS), named under a guest's list;
 * - `data-mail-started`, `data-mail-started-nonce`: the signed time the page
 *   was made, a guest's bot guard for "email me" (ConversationMail::stamp()).
 * - `data-contact-url`: the contact card's route
 *   (linker-ai/v1/genie/contact, #243).
 * - `data-inquiry-url`: the inquiry confirmation card's route
 *   (linker-ai/v1/genie/inquiry, #250).
 *
 * Opening and pending questions use the dock loader's ready/open handshake,
 * not configuration read from the mount.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../configurator/types';
import type { PageContext } from './api/turn';

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
	/** The page context the turn carries; the proxy checks it key by key. */
	page: PageContext;
	signedIn: boolean;
	retentionDays: number;
	mailStarted: string;
	mailStartedNonce: string;
	/** The contact card's route ("Let Linker contact me", #243). */
	contactUrl: string;
	/** The inquiry confirmation card's route (#250). */
	inquiryUrl: string;
}

function readPage(
	raw: string | undefined,
	pageType: string,
	productId: number
): PageContext {
	const fallback: PageContext = {
		type: pageType,
		...( productId > 0 ? { product_id: productId } : {} ),
	};
	if ( ! raw ) {
		return fallback;
	}
	try {
		const parsed: unknown = JSON.parse( raw );
		return parsed && typeof parsed === 'object' && 'type' in parsed
			? ( parsed as PageContext )
			: fallback;
	} catch {
		return fallback;
	}
}

export function readConfig( element: HTMLElement ): GenieConfig {
	const data = element.dataset;
	const pageType = data.pageType ?? 'other';
	const productId = Number( data.productId ) || 0;
	return {
		surface: data.surface === 'workspace' ? 'workspace' : 'helper',
		locale: data.locale === 'de' ? 'de' : 'en',
		pageType,
		productId,
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
		workspaceUrl: data.workspaceUrl ?? '/genie/',
		prompts: data.prompts ? JSON.parse( data.prompts ) : [],
		page: readPage( data.page, pageType, productId ),
		signedIn: data.signedIn === '1',
		// Only the page names the days (Retention::RETENTION_DAYS); a
		// mount without them names none, and the note stays away.
		retentionDays: Number( data.retentionDays ) || 0,
		mailStarted: data.mailStarted ?? '',
		mailStartedNonce: data.mailStartedNonce ?? '',
		contactUrl: data.contactUrl ?? '/wp-json/linker-ai/v1/genie/contact',
		inquiryUrl: data.inquiryUrl ?? '/wp-json/linker-ai/v1/genie/inquiry',
	};
}
