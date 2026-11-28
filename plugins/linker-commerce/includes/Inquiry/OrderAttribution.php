<?php
/**
 * Marketing consent and first-party source data for customer inquiries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Automattic\WooCommerce\Vendor\Detection\MobileDetect;
use WC_Order;

/** Applies Woo's source fields at the same boundary as the inquiry's first save. */
final class OrderAttribution {

	/** Woo fields and their corresponding Sourcebuster cookie keys. */
	private const SOURCES = array(
		'sbjs_current'     => array(
			'typ' => 'source_type',
			'src' => 'utm_source',
			'mdm' => 'utm_medium',
			'cmp' => 'utm_campaign',
			'cnt' => 'utm_content',
			'id'  => 'utm_id',
			'trm' => 'utm_term',
			'plt' => 'utm_source_platform',
			'fmt' => 'utm_creative_format',
			'tct' => 'utm_marketing_tactic',
		),
		'sbjs_current_add' => array(
			'ep' => 'session_entry',
			'rf' => 'referrer',
			'fd' => 'session_start_time',
		),
		'sbjs_session'     => array( 'pgs' => 'session_pages' ),
		'sbjs_udata'       => array(
			'vst' => 'session_count',
			'uag' => 'user_agent',
		),
	);

	/** Woo initializes existing forms. A planning form can also mount later. */
	public static function register(): void {
		add_action( 'wp_enqueue_scripts', array( self::class, 'hydrate_planner' ), 99 );
	}

	/** Read the existing page's tracking data without counting another page view. */
	public static function hydrate_planner(): void {
		// WordPress checks the consent bridge as a dependent of the attribution scripts.
		foreach ( array( 'sourcebuster-js', 'wc-order-attribution', 'wp-consent-api-integration' ) as $handle ) {
			if ( wp_script_is( $handle, 'enqueued' ) ) {
				wp_script_add_data( $handle, 'strategy', 'defer' );
			}
		}
		if ( wp_script_is( 'wc-order-attribution', 'enqueued' ) ) {
			wp_add_inline_script(
				'wc-order-attribution',
				"document.addEventListener('linker:inquiry-form-mounted',function(event){const fields=event.target.querySelector('wc-order-attribution-inputs');const woo=window.wc_order_attribution;if(fields && woo?.params.allowTracking && woo.getAttributionData){fields.values=woo.getAttributionData();}});",
				'before'
			);
		}
	}

	/** Whether the visitor explicitly allowed marketing attribution on this request. */
	public static function tracking_allowed(): bool {
		// phpcs:disable WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Only exact CMP consent flags are compared.
		$cmp    = isset( $_COOKIE['cookieyes-consent'] ) ? wp_unslash( $_COOKIE['cookieyes-consent'] ) : null;
		$bridge = isset( $_COOKIE['wp_consent_marketing'] ) ? wp_unslash( $_COOKIE['wp_consent_marketing'] ) : null;
		// phpcs:enable
		if ( null !== $cmp ) {
			$choices = is_string( $cmp ) ? explode( ',', $cmp ) : array();
			if ( ! in_array( 'advertisement:yes', $choices, true ) || in_array( 'advertisement:no', $choices, true ) || in_array( 'consent:no', $choices, true ) ) {
				return false;
			}
		}
		if ( null !== $bridge ) {
			return 'allow' === $bridge && function_exists( 'wp_has_consent' ) && wp_has_consent( 'marketing' );
		}
		// Direct REST and admin-post requests can carry the CMP cookie before the bridge cookie exists.
		return null !== $cmp;
	}

	/**
	 * Replace any attribution on a resumed order with this consented submission.
	 *
	 * @param WC_Order $order Native public inquiry, before its first save.
	 */
	public static function apply_to_order( WC_Order $order ): void {
		foreach ( $order->get_meta_data() as $meta ) {
			if ( str_starts_with( (string) $meta->key, '_wc_order_attribution_' ) ) {
				$order->delete_meta_data( $meta->key );
			}
		}
		if ( ! self::tracking_allowed() ) {
			return;
		}

		$values = array();
		foreach ( self::SOURCES as $fields ) {
			foreach ( $fields as $field ) {
				// phpcs:ignore WordPress.Security.NonceVerification.Missing, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Public handlers validate the submission. clean() only accepts scalar text.
				$value = self::clean( $field, wp_unslash( $_POST[ 'wc_order_attribution_' . $field ] ?? '' ) );
				if ( '' !== $value ) {
					$values[ $field ] = $value;
				}
			}
		}
		if ( array() === $values ) {
			$values = self::cookie_values();
		}
		if ( ! isset( $values['source_type'] ) && ( isset( $values['utm_source'] ) || isset( $values['utm_campaign'] ) ) ) {
			$values['source_type'] = 'utm';
		}
		if ( isset( $values['user_agent'] ) ) {
			$detect                = new MobileDetect( array(), $values['user_agent'] );
			$values['device_type'] = $detect->isTablet() ? 'Tablet' : ( $detect->isMobile() ? 'Mobile' : 'Desktop' );
		}
		foreach ( $values as $field => $value ) {
			$order->update_meta_data( '_wc_order_attribution_' . $field, $value );
		}
	}

	/** Read the same first-party fields when a Genie JSON request carries no form body.
	 *
	 * @return array<string,string>
	 */
	private static function cookie_values(): array {
		$values = array();
		foreach ( self::SOURCES as $cookie => $fields ) {
			// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Split the allowlisted Sourcebuster fields before sanitizing each value.
			$raw = wp_unslash( $_COOKIE[ $cookie ] ?? '' );
			if ( ! is_string( $raw ) || '' === $raw ) {
				continue;
			}
			foreach ( explode( '|||', $raw ) as $pair ) {
				$parts = explode( '=', $pair, 2 );
				if ( isset( $parts[1], $fields[ $parts[0] ] ) ) {
					$field = $fields[ $parts[0] ];
					$value = self::clean( $field, $parts[1] );
					if ( '' !== $value ) {
						$values[ $field ] = $value;
					}
				}
			}
		}
		return $values;
	}

	/**
	 * Keep campaign columns separate from landing paths, which can include account claim keys.
	 *
	 * @param string $field Allowed Woo field.
	 * @param mixed  $raw   Submitted text.
	 */
	private static function clean( string $field, $raw ): string {
		if ( ! is_string( $raw ) || '' === $raw || '(none)' === $raw ) {
			return '';
		}
		if ( 'source_type' === $field && ! in_array( $raw, array( 'utm', 'typein', 'organic', 'referral' ), true ) ) {
			return '';
		}
		$text = $raw;
		if ( 'session_entry' === $field || 'referrer' === $field ) {
			$text  = substr( $text, 0, strcspn( $text, '?#' ) );
			$parts = wp_parse_url( $text );
			if ( ! is_array( $parts ) || empty( $parts['host'] ) || isset( $parts['user'] ) || ! in_array( $parts['scheme'] ?? '', array( 'https', 'http' ), true ) ) {
				return '';
			}
			return mb_substr( esc_url_raw( $text, array( 'http', 'https' ) ), 0, 512 );
		}
		return mb_substr( sanitize_text_field( $text ), 0, 512 );
	}

	/**
	 * Woo registers anonymous attribution writers for both native admin and checkout orders.
	 * Public Sender owns those fields while it creates this inquiry, including via admin-post.
	 *
	 * @template T
	 * @param callable():T $create Customer submission.
	 * @return T
	 */
	public static function with_public_intake( callable $create ) {
		global $wp_filter;
		$removed = array();
		foreach ( array( 'woocommerce_new_order', 'woocommerce_checkout_order_created' ) as $hook ) {
			foreach ( $wp_filter[ $hook ]->callbacks ?? array() as $priority => $callbacks ) {
				foreach ( $callbacks as $entry ) {
					$callback = $entry['function'];
					if ( ! $callback instanceof \Closure || ( new \ReflectionFunction( $callback ) )->getClosureScopeClass()?->getName() !== 'Automattic\WooCommerce\Internal\Orders\OrderAttributionController' ) {
						continue;
					}
					remove_action( $hook, $callback, $priority );
					$removed[] = array( $hook, $callback, $priority, $entry['accepted_args'] );
				}
			}
		}
		try {
			return $create();
		} finally {
			foreach ( $removed as [ $hook, $callback, $priority, $args ] ) {
				add_action( $hook, $callback, $priority, $args );
			}
		}
	}
}
