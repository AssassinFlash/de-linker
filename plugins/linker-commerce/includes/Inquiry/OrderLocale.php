<?php
/**
 * The language of an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Mail\LocaleSwitch;
use WC_Order;

/**
 * Records the language the customer used when sending the inquiry; the
 * customer's emails and the Proforma use it.
 */
final class OrderLocale {


	/**
	 * Order meta: locale of the inquiry.
	 */
	public const META = '_linker_locale';

	/**
	 * The language of an inquiry; inquiries without one use the site's default.
	 *
	 * @param WC_Order $order Order.
	 */
	public static function of( WC_Order $order ): string {
		$locale = $order->get_meta( self::META );
		return is_string( $locale ) && '' !== $locale ? $locale : LocaleSwitch::site_default();
	}

	/**
	 * The locale of the current request: the language the checkout form posted
	 * first (its AJAX address ?wc-ajax=checkout names no language, so Polylang
	 * answers with the default one there; the form's own "lang" field,
	 * Checkout::language_field(), is the customer's page), then Polylang's
	 * current language, and WordPress's own answer when neither does.
	 *
	 * @param  string|null $language Explicit form language for non-global callers.
	 * @return string A WordPress locale.
	 */
	public static function current( ?string $language = null ): string {
		// The whole POST carries WooCommerce's checkout nonce (verified before any order is created).
		// phpcs:ignore WordPress.Security.NonceVerification.Missing
		$posted = $language ?? ( isset( $_POST['lang'] ) ? sanitize_key( wp_unslash( $_POST['lang'] ) ) : '' );
		if ( '' !== $posted && function_exists( 'PLL' ) ) {
			$language = PLL()->model->get_language( $posted );
			if ( false !== $language ) {
				$locale = $language->get_prop( 'locale' );
				if ( is_string( $locale ) && '' !== $locale ) {
					return $locale;
				}
			}
		}
		if ( function_exists( 'pll_current_language' ) ) {
			$locale = pll_current_language( 'locale' );
			if ( is_string( $locale ) && '' !== $locale ) {
				return $locale;
			}
		}
		return determine_locale();
	}

	/**
	 * Stores the current language on a new inquiry; runs on woocommerce_checkout_create_order.
	 *
	 * @param WC_Order $order Order being created.
	 */
	public function remember( WC_Order $order ): void {
		$order->update_meta_data( self::META, self::current() );
	}
}
