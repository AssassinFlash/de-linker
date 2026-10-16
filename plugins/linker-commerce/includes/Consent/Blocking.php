<?php
/**
 * Holds Site Kit's Google tag until the visitor consents to statistics.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Consent;

/**
 * Turns the consent banner's Google path into Consent Mode "Basic": before the
 * visitor answers the banner, the browser loads nothing from Google and sends
 * Google nothing (docs/specs/201-consent-ga4.md).
 *
 * WHY CODE. The carrier is official plugins — Site Kit prints the Google tag
 * and the consent defaults, Complianz shows the banner and blocks scripts until
 * consent, WP Consent API passes the answer between them — and none of them
 * reaches Basic on its own. Complianz's Site Kit integration puts the tag's
 * script ids on its blocker's whitelist (integrations/plugins/google-site-kit.php,
 * cmplz_google_site_kit_whitelisted_script_tags), and a whitelist entry wins over
 * every block rule (class-cookie-blocker.php checks it first), so no Script
 * Center setting can hold gtag.js back; measured on the review instance, the
 * tag loaded and sent a page_view before any click. Complianz's free settings
 * have no switch for it and Site Kit has none either: these three filters on
 * the two plugins' own hooks are the smallest change that gets there. Nothing
 * here decides how anything looks.
 */
final class Blocking {

	/**
	 * The script ids Complianz's Site Kit integration whitelists: the tag
	 * itself and the inline config call printed after it.
	 */
	private const SITE_KIT_TAG_IDS = array( 'google_gtagjs-js', 'google_gtagjs-js-after' );

	/**
	 * The inline consent-default snippet Site Kit prints before the tag. It
	 * must run before the banner (it holds every Google purpose at denied), and
	 * the whitelist matches by substring, so it keeps its own exact entry.
	 */
	public const CONSENT_DEFAULT_ID = 'google_gtagjs-js-consent-mode-data-layer';


	/**
	 * WP Consent API's script handle; the cookie cleanup runs after it.
	 */
	public const CONSENT_API_HANDLE = 'wp-consent-api';

	/**
	 * Deletes Google Analytics' own cookies (`_ga`, `_ga_<stream>`) whenever
	 * the visitor's statistics answer is not "allow": on the change event, and
	 * on every page load (a revocation made in another tab). Complianz free
	 * deletes only cookies in its cookie database, which its cloud scan or its
	 * per-service mode fills; WooCommerce clears its own `sbjs_*` itself.
	 * GA4 writes its cookies on the registrable domain (".de-linker.com"), so
	 * every parent of the host is tried, with and without a leading dot.
	 */
	public const CLEAR_ANALYTICS_COOKIES = <<<'JS'
( function () {
	function clear() {
		var host = location.hostname.split( '.' );
		document.cookie.split( '; ' ).forEach( function ( pair ) {
			var name = pair.split( '=' )[ 0 ];
			if ( ! /^_ga(_|$)/.test( name ) ) {
				return;
			}
			var gone = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
			document.cookie = gone;
			for ( var i = 0; i < host.length - 1; i++ ) {
				var domain = host.slice( i ).join( '.' );
				document.cookie = gone + '; domain=' + domain;
				document.cookie = gone + '; domain=.' + domain;
			}
		} );
	}
	function denied() {
		return typeof window.wp_has_consent === 'function' && ! window.wp_has_consent( 'statistics' );
	}
	document.addEventListener( 'wp_listen_for_consent_change', function ( event ) {
		if ( event.detail && event.detail.statistics && event.detail.statistics !== 'allow' ) {
			clear();
		}
	} );
	document.addEventListener( 'wp_consent_type_defined', function () {
		if ( denied() ) {
			clear();
		}
	} );
}() );
JS;

	/**
	 * Adds the three filters and the cookie cleanup.
	 */
	public function register(): void {
		// After Complianz's integration (priority 10) has added its entries.
		add_filter( 'cmplz_whitelisted_script_tags', array( $this, 'block_site_kit_tag' ), 20 );
		add_filter( 'googlesitekit_consent_defaults', array( $this, 'deny_everywhere' ) );
		add_filter( 'googlesitekit_consent_category_map', array( $this, 'statistics_only' ) );
		// After WP Consent API enqueues its script, at PHP_INT_MAX - 100
		// (wp-consent-api/inc/api-functions.php).
		add_action( 'wp_enqueue_scripts', array( $this, 'add_cookie_cleanup' ), PHP_INT_MAX );
	}

	/**
	 * Attaches the cleanup to WP Consent API's script, so it runs wherever
	 * that script runs and never without it.
	 */
	public function add_cookie_cleanup(): void {
		if ( wp_script_is( self::CONSENT_API_HANDLE, 'enqueued' ) ) {
			wp_add_inline_script( self::CONSENT_API_HANDLE, self::CLEAR_ANALYTICS_COOKIES );
		}
	}

	/**
	 * Takes the Google tag off Complianz's whitelist, so its blocker holds the
	 * tag (as type="text/plain", category statistics) until consent, and keeps
	 * the consent-default snippet on it.
	 *
	 * @param mixed $tags The whitelist: substrings of script tags the blocker skips.
	 * @return list<string>
	 */
	public function block_site_kit_tag( $tags ): array {
		$tags = array_values(
			array_filter(
				(array) $tags,
				static fn ( $tag ): bool => is_string( $tag ) && ! in_array( $tag, self::SITE_KIT_TAG_IDS, true )
			)
		);
		if ( ! in_array( self::CONSENT_DEFAULT_ID, $tags, true ) ) {
			$tags[] = self::CONSENT_DEFAULT_ID;
		}
		return $tags;
	}

	/**
	 * Applies the denied defaults to every visitor. Site Kit scopes them to a
	 * list of European regions; outside it Google treats every purpose as
	 * granted — measured from this machine (outside the list): `_ga` cookies
	 * and a page_view before any click. TDDDG §25 asks consent of every
	 * visitor of this site, wherever they are.
	 *
	 * @param mixed $defaults Site Kit's consent defaults.
	 * @return array<string, mixed>
	 */
	public function deny_everywhere( $defaults ): array {
		$defaults = (array) $defaults;
		unset( $defaults['region'] );
		return $defaults;
	}

	/**
	 * Lets only the statistics answer reach Google. The site has no Google
	 * advertising tag; its marketing category is WooCommerce's own order
	 * source (WooCommerce files it there, WPConsentAPI::$consent_category), so
	 * a yes to marketing grants Google nothing: ad_storage, ad_user_data and
	 * ad_personalization stay at their denied default.
	 *
	 * @param mixed $map Site Kit's map of WP Consent API categories to Google purposes.
	 * @return array<string, list<string>>
	 */
	public function statistics_only( $map ): array {
		$map              = (array) $map;
		$map['marketing'] = array();
		return $map;
	}
}
