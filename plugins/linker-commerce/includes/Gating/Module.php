<?php
/**
 * Hooks of the gating module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Gating;

/**
 * Hidden prices, addable products, price texts and the Store API.
 */
final class Module {

	/**
	 * Price getters filtered for visibility: simple products and variations.
	 */
	private const PRICE_FILTERS = array(
		'woocommerce_product_get_price',
		'woocommerce_product_get_regular_price',
		'woocommerce_product_get_sale_price',
		'woocommerce_product_variation_get_price',
		'woocommerce_product_variation_get_regular_price',
		'woocommerce_product_variation_get_sale_price',
	);

	/**
	 * Sets up the module.
	 *
	 * @param PriceDisplay   $display The price display.
	 * @param DraftSummary   $summary The solution draft summary.
	 * @param StoreApiPrices $api     The Store API filter.
	 * @param CatalogSorting $sorting Sorting without prices for guests.
	 */
	public function __construct(
		private readonly PriceDisplay $display,
		private readonly DraftSummary $summary,
		private readonly StoreApiPrices $api,
		private readonly CatalogSorting $sorting
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		foreach ( self::PRICE_FILTERS as $filter ) {
			add_filter( $filter, array( $this->display, 'price' ), 10, 2 );
		}
		add_filter( 'woocommerce_get_variation_prices_hash', array( $this->display, 'variation_prices_hash' ) );
		add_filter( 'woocommerce_is_purchasable', array( $this->display, 'purchasable' ), 10, 2 );
		add_filter( 'woocommerce_empty_price_html', array( $this->display, 'empty_price_html' ), 10, 2 );
		add_filter( 'woocommerce_cart_item_price', array( $this->display, 'cart_item_price' ), 10, 2 );
		add_filter( 'woocommerce_cart_item_subtotal', array( $this->display, 'cart_item_price' ), 10, 2 );
		add_filter( 'woocommerce_cart_subtotal', array( $this->display, 'cart_subtotal' ) );
		add_action( 'woocommerce_checkout_create_order_line_item', array( $this->display, 'remember_line_reason' ), 10, 3 );
		add_filter( 'woocommerce_order_formatted_line_subtotal', array( $this->display, 'order_line_subtotal' ), 10, 2 );
		add_filter( 'woocommerce_hidden_order_itemmeta', array( $this->display, 'hidden_item_meta' ) );
		add_action( 'woocommerce_cart_collaterals', array( $this->summary, 'guest_totals' ), 5 );
		add_action( 'woocommerce_cart_totals_after_order_total', array( $this->summary, 'unpriced_note' ) );
		add_action( 'woocommerce_review_order_after_order_total', array( $this->summary, 'unpriced_note' ) );
		add_action( 'woocommerce_order_details_after_order_table', array( $this->summary, 'inquiry_note' ), 1 );
		add_action( 'woocommerce_email_after_order_table', array( $this->summary, 'inquiry_note' ), 10, 3 );
		add_filter( 'woocommerce_catalog_orderby', array( $this->sorting, 'options' ) );
		add_filter( 'woocommerce_get_catalog_ordering_args', array( $this->sorting, 'ordering' ), 10, 2 );
		add_filter( 'rest_request_after_callbacks', array( $this->api, 'filter' ), 10, 3 );
	}
}
