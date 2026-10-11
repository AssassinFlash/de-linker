<?php
/**
 * WooCommerce settings this site depends on, pinned in code.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Settings;

/**
 * Pins the WooCommerce options that make the store an inquiry site, so they do
 * not depend on what someone clicks in WooCommerce → Settings: no shipping, no
 * coupons, an inquiry only with an account, registration on the account page
 * with a password the customer chooses, and endpoint URLs without "order".
 */
final class WooOptions {

	/**
	 * Option name of the endpoint set the rewrite rules were last built for.
	 */
	public const REWRITES_OPTION = 'linker_commerce_rewrites';

	/**
	 * Option values, each with the decision it implements.
	 *
	 * @return array<string, string>
	 */
	public static function pinned(): array {
		return array(
			// No shipping or delivery on the site (docs/specs/11-commerce.md, "删除/不存在").
			'woocommerce_ship_to_countries'              => 'disabled',
			// No discounts on an inquiry site (AGENTS.md §1: products → inquiry → offline).
			'woocommerce_enable_coupons'                 => 'no',
			// Sending an inquiry needs an account (docs/specs/11-commerce.md, Gating).
			'woocommerce_enable_guest_checkout'          => 'no',
			'woocommerce_enable_checkout_login_reminder' => 'yes',
			// Registration happens on the account page, with the company fields (journey step 2).
			'woocommerce_enable_signup_and_login_from_checkout' => 'no',
			'woocommerce_enable_myaccount_registration'  => 'yes',
			'woocommerce_registration_generate_username' => 'yes',
			'woocommerce_registration_generate_password' => 'no',
			// The inquiry is a company's (AGENTS.md §1: installers, EPCs, distributors); WooCommerce 11 hides the field by default.
			'woocommerce_checkout_company_field'         => 'required',
			// No product reviews or star ratings: the site's chain is products → inquiry (AGENTS.md §1).
			'woocommerce_enable_reviews'                 => 'no',
			// Stock is only ever a state, never a quantity (owner ruling 2026-10-02, AGENTS.md §2).
			'woocommerce_stock_format'                   => 'no_amount',
			// The catalogue lists only what can be asked for: a product the ERP
			// pushed out of stock leaves the shop and category pages (owner rule
			// "only show in stock", ticket #69; WooCommerce's own hiding).
			'woocommerce_hide_out_of_stock_items'        => 'yes',
		);
	}

	/**
	 * Endpoint slugs: the address bar reads "inquiries" and "company", and the
	 * endpoints the site does not offer (downloads, payment methods) do not exist.
	 *
	 * @return array<string, string> Query var → slug ('' removes the endpoint).
	 */
	public static function endpoints(): array {
		return array(
			'order-received'             => 'inquiry-received',
			'orders'                     => 'inquiries',
			'view-order'                 => 'inquiry',
			'edit-address'               => 'company',
			'downloads'                  => '',
			'payment-methods'            => '',
			'add-payment-method'         => '',
			'delete-payment-method'      => '',
			'set-default-payment-method' => '',
		);
	}

	/**
	 * The pinned value of an option; runs on pre_option_{name}.
	 *
	 * @param mixed  $pre    Value from an earlier filter, false to read the database.
	 * @param string $option Option name.
	 * @return mixed
	 */
	public function pin( $pre, string $option ) {
		return self::pinned()[ $option ] ?? $pre;
	}

	/**
	 * Applies the endpoint slugs to WooCommerce's query vars.
	 *
	 * @param array<string, string> $vars Query var → slug.
	 * @return array<string, string>
	 */
	public function endpoint_slugs( array $vars ): array {
		foreach ( self::endpoints() as $var => $slug ) {
			if ( '' === $slug ) {
				unset( $vars[ $var ] );
			} else {
				$vars[ $var ] = $slug;
			}
		}
		return $vars;
	}

	/**
	 * The account menu reads the endpoint options to decide which items exist;
	 * the removed endpoints read as empty there too. Runs on
	 * pre_option_woocommerce_myaccount_*_endpoint.
	 *
	 * @param mixed  $pre    Value from an earlier filter.
	 * @param string $option Option name.
	 * @return mixed
	 */
	public function pin_endpoint_option( $pre, string $option ) {
		$var = str_replace( array( 'woocommerce_myaccount_', '_endpoint' ), '', $option );
		$var = str_replace( '_', '-', $var );
		return array_key_exists( $var, self::endpoints() ) ? self::endpoints()[ $var ] : $pre;
	}

	/**
	 * Rebuilds the rewrite rules once whenever the set of endpoints changed, so a
	 * renamed or added endpoint answers without a visit to Settings → Permalinks.
	 * Runs on init, after WooCommerce registered its endpoints.
	 */
	public function flush_rewrites_when_endpoints_change(): void {
		$signature = md5( (string) wp_json_encode( WC()->query->get_query_vars() ) );
		if ( get_option( self::REWRITES_OPTION ) === $signature ) {
			return;
		}
		flush_rewrite_rules( false );
		update_option( self::REWRITES_OPTION, $signature, false );
	}
}
