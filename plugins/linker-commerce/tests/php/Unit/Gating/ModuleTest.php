<?php
/**
 * Tests for the gating module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\ProductSorting;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\DraftSummary;
use Linker\Commerce\Gating\Module;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Gating\StoreApiPrices;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Gating\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * Every price getter, the purchasable rule, the texts and the Store API filter are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$state   = $this->approved_state();
		$display = new PriceDisplay( $state );
		$summary = new DraftSummary( $state, $display );
		$api     = new StoreApiPrices( $state );
		$sorting = new ProductSorting( $state );

		foreach ( array( 'woocommerce_product_get_price', 'woocommerce_product_get_regular_price', 'woocommerce_product_get_sale_price', 'woocommerce_product_variation_get_price', 'woocommerce_product_variation_get_regular_price', 'woocommerce_product_variation_get_sale_price' ) as $filter ) {
			WP_Mock::expectFilterAdded( $filter, array( $display, 'price' ), 10, 2 );
		}
		WP_Mock::expectFilterAdded( 'woocommerce_get_variation_prices_hash', array( $display, 'variation_prices_hash' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_is_purchasable', array( $display, 'purchasable' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_empty_price_html', array( $display, 'empty_price_html' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_cart_item_price', array( $display, 'cart_item_price' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_cart_item_subtotal', array( $display, 'cart_item_price' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_cart_subtotal', array( $display, 'cart_subtotal' ) );
		WP_Mock::expectActionAdded( 'woocommerce_checkout_create_order_line_item', array( $display, 'remember_line_reason' ), 10, 3 );
		WP_Mock::expectFilterAdded( 'woocommerce_order_formatted_line_subtotal', array( $display, 'order_line_subtotal' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_hidden_order_itemmeta', array( $display, 'hidden_item_meta' ) );
		WP_Mock::expectActionAdded( 'woocommerce_cart_collaterals', array( $summary, 'guest_totals' ), 5 );
		WP_Mock::expectActionAdded( 'woocommerce_cart_totals_after_order_total', array( $summary, 'unpriced_note' ) );
		WP_Mock::expectActionAdded( 'woocommerce_review_order_after_order_total', array( $summary, 'unpriced_note' ) );
		WP_Mock::expectActionAdded( 'woocommerce_order_details_after_order_table', array( $summary, 'inquiry_note' ), 1 );
		WP_Mock::expectActionAdded( 'woocommerce_email_after_order_table', array( $summary, 'inquiry_note' ), 10, 3 );
		WP_Mock::expectFilterAdded( 'woocommerce_catalog_orderby', array( $sorting, 'options' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_get_catalog_ordering_args', array( $sorting, 'ordering' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'rest_request_after_callbacks', array( $api, 'filter' ), 10, 3 );

		( new Module( $display, $summary, $api, $sorting ) )->register();

		$this->assertConditionsMet();
	}
}
