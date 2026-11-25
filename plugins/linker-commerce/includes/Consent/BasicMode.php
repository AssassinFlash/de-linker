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

	/** WooCommerce log source when the barrier cannot see the handle it knows. */
	public const LOG_SOURCE = 'linker-consent';

	/** Site Kit 1.189.0 prints the Google tag on this handle. */
	public const GOOGLE_HANDLE = 'google_gtagjs';

	/**
	 * One warning per request; deploy verify is what fails the batch.
	 *
	 * @var bool
	 */
	private bool $alerted = false;

	/** One conversion carried across its native form's success redirect. */
	private const FLASH = 'linker_analytics_conversion';

	/**
	 * Dispatch the consented conversion once on its redirected browser page.
	 *
	 * @var string
	 */
	private string $conversion_script = '';

	/** Registers the gaps verified against CookieYes 3.5.7 / Site Kit 1.189.0. */
	public function register(): void {
		add_action( 'template_redirect', array( $this, 'read_conversion' ), 99 );
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_withdrawal' ), 0 );
		add_filter( 'seopress_clarity_tracking_js', array( $this, 'clarity_project' ) );
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

	/**
	 * Keep only the successful action and its categorical dimensions in the Woo session.
	 *
	 * @param string               $name Conversion name.
	 * @param array<string,string> $params Server-validated event dimensions.
	 */
	public static function remember_conversion( string $name, array $params ): void {
		if ( ! self::statistics_allowed() ) {
			return;
		}
		WC()->initialize_session();
		WC()->session->set(
			self::FLASH,
			array(
				'name'   => $name,
				'params' => $params,
			)
		);
		if ( WC()->session instanceof \WC_Session_Handler ) {
			WC()->session->set_customer_session_cookie( true );
		}
	}

	/** Consume the event on its confirmation page before Site Kit prints its opt-out. */
	public function read_conversion(): void {
		if ( ! function_exists( 'WC' ) ) {
			return;
		}
		$session = WC()->session;
		if ( ! $session instanceof \WC_Session_Handler ) {
			return;
		}
		$event = $session->get( self::FLASH );
		if ( ! is_array( $event ) ) {
			return;
		}
		$session->set( self::FLASH, null );
		if ( ! self::statistics_allowed() ) {
			return;
		}
		$this->conversion_script = 'document.addEventListener("DOMContentLoaded", function () { window.linkerTrack(' . wp_json_encode( $event['name'] ) . ', ' . wp_json_encode( $event['params'] ) . '); }, { once: true });';
		\Linker\Commerce\Cache\DynamicHtml::forbid( 'conversion confirmation' );
		// Woo signs the new partner in before redirecting; Site Kit normally opts logged-in users out.
		if ( 'sign_up' === $event['name'] ) {
			add_filter( 'googlesitekit_analytics_tracking_disabled', '__return_false' );
		}
	}

	/** CookieYes stores comma-separated categories in the same first-party cookie on every page. */
	private static function statistics_allowed(): bool {
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Comparing an exact CMP category; no request text is stored or printed.
		$choice = isset( $_COOKIE['cookieyes-consent'] ) && is_string( $_COOKIE['cookieyes-consent'] ) ? wp_unslash( $_COOKIE['cookieyes-consent'] ) : '';
		return in_array( 'analytics:yes', explode( ',', $choice ), true );
	}

	/** Supply SEOPress's enabled project to the consent bridge without starting its tracker. */
	public function clarity_project(): string {
		$options = get_option( 'seopress_google_analytics_option_name', array() );
		$id      = $options['seopress_google_analytics_clarity_project_id'] ?? '';
		return 'window.linkerClarityProject = ' . wp_json_encode( $id, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT ) . ';';
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
		if ( '' !== $this->conversion_script ) {
			wp_add_inline_script( 'linker-consent-withdrawal', $this->conversion_script );
		}
	}

	/**
	 * Parser-inert Google tag. CookieYes owns releasing this tag after analytics
	 * consent; its MutationObserver alone cannot prevent a parser-started request.
	 * Withdrawal re-blocks by reloading into this held markup (assets/consent.js).
	 *
	 * A renamed Site Kit handle is still held when the tag URL is Google's, and
	 * that fallback is logged. Without CookieYes (no CLI_VERSION) the tag is left
	 * unchanged, because nothing would release a held tag, and the same request
	 * logs the gap. Deploy verify fails closed in both cases.
	 *
	 * @param string $tag Enqueued script markup.
	 * @param string $handle Script handle.
	 * @return string
	 */
	public function hold_google_tag( string $tag, string $handle ): string {
		$google = self::GOOGLE_HANDLE === $handle || str_contains( $tag, 'googletagmanager.com/gtag/js' );
		if ( ! $google ) {
			return $tag;
		}
		if ( ! defined( 'CLI_VERSION' ) ) {
			$this->alert( 'CookieYes is inactive (CLI_VERSION absent) while a Google tag is printed and analytics consent is denied; the barrier did not hold it.' );
			return $tag;
		}
		if ( self::GOOGLE_HANDLE !== $handle ) {
			$this->alert( 'Site Kit handle "' . $handle . '" is not google_gtagjs while analytics consent is denied; holding the Google tag by URL.' );
		}
		$html = new \WP_HTML_Tag_Processor( $tag );
		if ( $html->next_tag( array( 'tag_name' => 'script' ) ) ) {
			$html->set_attribute( 'type', 'text/plain' );
			$html->set_attribute( 'data-cookieyes', 'cookieyes-analytics' );
		}
		return $html->get_updated_html();
	}

	/**
	 * Logs the gap once per request.
	 *
	 * @param string $message Warning text for the WooCommerce log.
	 */
	private function alert( string $message ): void {
		if ( $this->alerted ) {
			return;
		}
		$this->alerted = true;
		wc_get_logger()->warning( $message, array( 'source' => self::LOG_SOURCE ) );
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
