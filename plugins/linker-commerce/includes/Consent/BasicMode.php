<?php
/**
 * Connects the native CMP blocker to Site Kit's Basic consent mode.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Consent;

/**
 * Leaves the banner, preference storage and Woo attribution to their plugins.
 */
final class BasicMode {

	/** Registers the gaps verified against CookieYes 3.5.7 / Site Kit 1.189.0. */
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_withdrawal' ), 0 );
		add_filter( 'wp_get_consent_type', array( $this, 'opt_in' ) );
		add_filter( 'script_loader_tag', array( $this, 'hold_google_tag' ), 30, 2 );
		add_filter( 'googlesitekit_consent_defaults', array( $this, 'deny_everywhere' ) );
		add_filter( 'googlesitekit_consent_category_map', array( $this, 'without_ads' ) );
	}

	/** CookieYes's Site Kit branch skips its first empty choice event.
	 * Define opt-in on the server before Woo evaluates initial attribution.
	 *
	 * @param string $type Existing consent mode.
	 * @return string
	 */
	public function opt_in( string $type ): string {
		return defined( 'CLI_VERSION' ) ? 'optin' : $type;
	}

	/** Enqueues before Site Kit's consent-update listener. */
	public function enqueue_withdrawal(): void {
		if ( ! defined( 'WP_CONSENT_API_VERSION' ) || ! defined( 'CLI_VERSION' ) ) {
			return;
		}
		wp_enqueue_script(
			'linker-consent-withdrawal',
			plugins_url( 'assets/consent.js', dirname( __DIR__, 2 ) . '/linker-commerce.php' ),
			array( 'wp-consent-api' ),
			(string) filemtime( dirname( __DIR__, 2 ) . '/assets/consent.js' ),
			false
		);
		$settings = get_option( 'googlesitekit_analytics-4_settings', array() );
		$id       = is_array( $settings ) && is_string( $settings['measurementID'] ?? null ) ? $settings['measurementID'] : '';
		wp_add_inline_script( 'linker-consent-withdrawal', 'window.linkerConsentMeasurementID = ' . wp_json_encode( $id ) . ';', 'before' );
	}

	/**
	 * Parser-inert Google tag. CookieYes owns releasing this tag after opt-in;
	 * its MutationObserver alone cannot prevent a parser-started request.
	 *
	 * @param string $tag Enqueued script markup.
	 * @param string $handle Script handle.
	 * @return string
	 */
	public function hold_google_tag( string $tag, string $handle ): string {
		if ( 'google_gtagjs' !== $handle || ! defined( 'CLI_VERSION' ) ) {
			return $tag;
		}
		$html = new \WP_HTML_Tag_Processor( $tag );
		if ( $html->next_tag( array( 'tag_name' => 'script' ) ) ) {
			$html->set_attribute( 'type', 'text/plain' );
			$html->set_attribute( 'data-cookieyes', 'cookieyes-analytics' );
		}
		return $html->get_updated_html();
	}

	/**
	 * Site Kit's regional defaults otherwise leave visitors outside Europe
	 * without a denied default. The same opt-in contract applies worldwide.
	 *
	 * @param array<string, mixed> $defaults Site Kit defaults.
	 * @return array<string, mixed>
	 */
	public function deny_everywhere( array $defaults ): array {
		unset( $defaults['region'] );
		foreach ( array( 'analytics_storage', 'ad_storage', 'ad_user_data', 'ad_personalization' ) as $key ) {
			$defaults[ $key ] = 'denied';
		}
		return $defaults;
	}

	/**
	 * Woo's marketing category means local order-source attribution here.
	 * It does not authorize Google advertising features, which this site
	 * does not use. Statistics continues to control analytics_storage.
	 *
	 * @param array<string, string[]> $map Consent categories.
	 * @return array<string, string[]>
	 */
	public function without_ads( array $map ): array {
		unset( $map['marketing'] );
		return $map;
	}
}
