<?php
/**
 * The account menu and its pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

/**
 * The account as the customer's workplace (docs/specs/11-commerce.md, journey
 * step 6): Overview, Inquiries, Saved solutions, Documents, Company, Account
 * details. WooCommerce's orders and address pages serve as Inquiries and
 * Company; downloads and payment methods do not exist (Settings\WooOptions).
 */
final class Menu {

	/**
	 * Endpoints this plugin adds: query var → slug.
	 */
	public const ENDPOINTS = array(
		'saved-solutions' => 'saved-solutions',
		'documents'       => 'documents',
	);

	/**
	 * Adds this plugin's endpoints to WooCommerce's query vars.
	 *
	 * @param array<string, string> $vars Query var → slug.
	 * @return array<string, string>
	 */
	public function query_vars( array $vars ): array {
		return array_merge( $vars, self::ENDPOINTS );
	}

	/**
	 * The menu, in this order; items other plugins add stay before "Log out".
	 *
	 * @param array<string, string> $items Endpoint → label.
	 * @return array<string, string>
	 */
	public function items( array $items ): array {
		$menu  = array(
			'dashboard'       => __( 'Overview', 'linker-commerce' ),
			'orders'          => __( 'Inquiries', 'linker-commerce' ),
			'saved-solutions' => __( 'Saved solutions', 'linker-commerce' ),
			'documents'       => __( 'Documents', 'linker-commerce' ),
			'edit-address'    => __( 'Company', 'linker-commerce' ),
			'edit-account'    => __( 'Account details', 'linker-commerce' ),
		);
		$known = array_merge( array_keys( $menu ), array( 'customer-logout', 'downloads', 'payment-methods' ) );
		foreach ( $items as $endpoint => $label ) {
			if ( ! in_array( $endpoint, $known, true ) ) {
				$menu[ $endpoint ] = $label;
			}
		}
		$menu['customer-logout'] = __( 'Log out', 'linker-commerce' );
		return $menu;
	}

	/**
	 * Page titles of the account endpoints; runs on woocommerce_endpoint_{endpoint}_title.
	 *
	 * @param string $title    WooCommerce's title.
	 * @param string $endpoint Endpoint.
	 */
	public function title( string $title, string $endpoint ): string {
		global $wp;
		switch ( $endpoint ) {
			case 'orders':
				return __( 'Inquiries', 'linker-commerce' );
			case 'view-order':
				$order = wc_get_order( absint( $wp->query_vars['view-order'] ?? 0 ) );
				if ( ! $order instanceof \WC_Order ) {
					return __( 'Inquiry', 'linker-commerce' );
				}
				/* translators: %s: inquiry number. */
				return sprintf( __( 'Inquiry #%s', 'linker-commerce' ), $order->get_order_number() );
			case 'saved-solutions':
				return __( 'Saved solutions', 'linker-commerce' );
			case 'documents':
				return __( 'Documents', 'linker-commerce' );
			case 'edit-address':
				return __( 'Company', 'linker-commerce' );
			case 'edit-account':
				return __( 'Account details', 'linker-commerce' );
		}
		return $title;
	}
}
