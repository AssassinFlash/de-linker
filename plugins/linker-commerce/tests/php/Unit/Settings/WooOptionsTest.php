<?php
/**
 * Tests for the pinned WooCommerce options.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Settings;

use Linker\Commerce\Settings\WooOptions;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Tests for WooOptions.
 *
 * @covers \Linker\Commerce\Settings\WooOptions
 */
final class WooOptionsTest extends TestCase {

	/**
	 * The options that make WooCommerce an inquiry site read their pinned value; others pass through.
	 */
	public function test_pins_the_inquiry_settings(): void {
		$options = new WooOptions();

		$this->assertSame( 'disabled', $options->pin( false, 'woocommerce_ship_to_countries' ) );
		$this->assertSame( 'no', $options->pin( false, 'woocommerce_enable_coupons' ) );
		$this->assertSame( 'yes', $options->pin( false, 'woocommerce_enable_guest_checkout' ) );
		$this->assertSame( 'optional', $options->pin( false, 'woocommerce_checkout_company_field' ) );
		$this->assertSame( 'no_amount', $options->pin( false, 'woocommerce_stock_format' ) );
		$this->assertSame( 'yes', $options->pin( false, 'woocommerce_hide_out_of_stock_items' ) );
		$this->assertSame( 'no', $options->pin( false, 'woocommerce_enable_reviews' ) );
		$this->assertFalse( $options->pin( false, 'blogname' ) );
	}

	/**
	 * Endpoints read "inquiries", "inquiry", "company"; downloads and payment methods are gone.
	 */
	public function test_endpoint_slugs(): void {
		$vars = ( new WooOptions() )->endpoint_slugs(
			array(
				'order-received'  => 'order-received',
				'orders'          => 'orders',
				'view-order'      => 'view-order',
				'edit-address'    => 'edit-address',
				'edit-account'    => 'edit-account',
				'downloads'       => 'downloads',
				'payment-methods' => 'payment-methods',
				'lost-password'   => 'lost-password',
			)
		);

		$this->assertSame(
			array(
				'order-received' => 'inquiry-received',
				'orders'         => 'inquiries',
				'view-order'     => 'inquiry',
				'edit-address'   => 'company',
				'edit-account'   => 'edit-account',
				'lost-password'  => 'lost-password',
			),
			$vars
		);
	}

	/**
	 * The account menu sees removed endpoints as empty options, renamed ones with their new slug.
	 */
	public function test_endpoint_options(): void {
		$options = new WooOptions();

		$this->assertSame( '', $options->pin_endpoint_option( false, 'woocommerce_myaccount_downloads_endpoint' ) );
		$this->assertSame( '', $options->pin_endpoint_option( false, 'woocommerce_myaccount_payment_methods_endpoint' ) );
		$this->assertSame( 'inquiries', $options->pin_endpoint_option( false, 'woocommerce_myaccount_orders_endpoint' ) );
		$this->assertSame( 'company', $options->pin_endpoint_option( false, 'woocommerce_myaccount_edit_address_endpoint' ) );
		$this->assertFalse( $options->pin_endpoint_option( false, 'woocommerce_myaccount_edit_account_endpoint' ) );
	}

	/**
	 * Rewrite rules are rebuilt once for a new set of endpoints, not on every request.
	 */
	public function test_flushes_rewrites_once_per_endpoint_set(): void {
		$query = Mockery::mock();
		$query->allows( 'get_query_vars' )->andReturn( array( 'orders' => 'inquiries' ) );
		$woocommerce        = new \stdClass();
		$woocommerce->query = $query;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		$signature = md5( (string) json_encode( array( 'orders' => 'inquiries' ) ) );

		WP_Mock::userFunction(
			'get_option',
			array(
				'args'            => array( WooOptions::REWRITES_OPTION ),
				'return_in_order' => array( 'old', $signature ),
			)
		);
		WP_Mock::userFunction(
			'flush_rewrite_rules',
			array(
				'times' => 1,
				'args'  => array( false ),
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'times' => 1,
				'args'  => array( WooOptions::REWRITES_OPTION, $signature, false ),
			)
		);

		$options = new WooOptions();
		$options->flush_rewrites_when_endpoints_change();
		$options->flush_rewrites_when_endpoints_change();

		$this->assertConditionsMet();
	}
}
