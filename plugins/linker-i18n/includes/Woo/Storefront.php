<?php
/**
 * The shop in German: pages, product names and the cart.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Woo;

use Linker\I18n\Languages;

/**
 * Lets a German visitor shop with English products shown in German.
 *
 * The cart holds English products only: adding a German product adds its
 * English product, so price, stock and purchasability are decided on the one
 * record the ERP writes. In a German request the English product is shown
 * with the German name and link, and WooCommerce's pages (shop, cart,
 * checkout, account) are their German versions
 * (docs/research/2026-10-09/i18n-opensource-replication.md §6.2).
 */
final class Storefront {

	/**
	 * Sets up the storefront filters.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * The English product of a product being added to the cart (filter
	 * `woocommerce_add_to_cart_product_id`).
	 *
	 * @param int|string $product_id Product ID.
	 * @return int|string
	 */
	public function cart_product( $product_id ) {
		return $this->languages->source_post( (int) $product_id ) ?? $product_id;
	}

	/**
	 * The English product whose facts answer for a product (filter
	 * `linker_commerce_facts_product_id`): the selection facts live on the
	 * English record only, so a German product is asked through its English
	 * twin — the same swap the cart makes, so it delegates to cart_product().
	 *
	 * @param int|string $product_id Product ID.
	 * @return int|string
	 */
	public function facts_product_id( $product_id ) {
		return $this->cart_product( $product_id );
	}

	/**
	 * The same for the Store API (filter `woocommerce_store_api_add_to_cart_data`).
	 *
	 * @param array<string, mixed> $data Cart item data; `id` is the product.
	 * @return array<string, mixed>
	 */
	public function store_cart_product( array $data ): array {
		if ( isset( $data['id'] ) && is_numeric( $data['id'] ) ) {
			$data['id'] = $this->cart_product( (int) $data['id'] );
		}
		return $data;
	}

	/**
	 * The German name of an English product in a German request (filter
	 * `woocommerce_product_get_name`): in the cart, the mini cart, the Store
	 * API and the order lines WooCommerce writes from it.
	 *
	 * @param mixed $name    Product name.
	 * @param mixed $product Product.
	 * @return mixed
	 */
	public function name( $name, $product ) {
		$german = $this->german_of( $product );
		return null === $german ? $name : get_post_field( 'post_title', $german );
	}

	/**
	 * The German name in the quotes of WooCommerce's add-to-cart message
	 * (filter `woocommerce_add_to_cart_item_name_in_quotes`): the message
	 * takes its name from `get_the_title()`, which the `get_name()` filter
	 * does not reach, so a German request's notice would name the English
	 * product. The wrapper is WooCommerce's own string, so its quotes follow
	 * the locale (German „…“).
	 *
	 * @param string     $quoted     The item name in quotes.
	 * @param int|string $product_id Product ID.
	 * @return string
	 */
	public function quoted_item_name( $quoted, $product_id = 0 ): string {
		$german = $this->german_of_id( is_numeric( $product_id ) ? (int) $product_id : 0 );
		if ( null === $german ) {
			return $quoted;
		}
		/* translators: %s: product name */
		return sprintf( _x( '&ldquo;%s&rdquo;', 'Item name in quotes', 'woocommerce' ), wp_strip_all_tags( (string) get_the_title( $german ) ) );
	}

	/**
	 * The German link of an English product in the cart of a German request
	 * (filter `woocommerce_cart_item_permalink`, used by the cart template and
	 * the Store API).
	 *
	 * @param mixed                $permalink Product link.
	 * @param array<string, mixed> $cart_item Cart item.
	 * @return mixed
	 */
	public function cart_item_permalink( $permalink, array $cart_item ) {
		$product = $cart_item['data'] ?? null;
		$german  = $this->german_of( $product );
		if ( null === $german ) {
			return $permalink;
		}
		$link = get_permalink( $german );
		return false === $link ? $permalink : $link;
	}

	/**
	 * The English SKU on a German product (filter `woocommerce_product_get_sku`):
	 * the German product stores none, so a SKU names one product, and shows
	 * the one it shares.
	 *
	 * @param mixed $sku     SKU.
	 * @param mixed $product Product.
	 * @return mixed
	 */
	public function sku( $sku, $product ) {
		if ( '' !== $sku || ! $product instanceof \WC_Product || Languages::TARGET !== $this->languages->of_post( $product->get_id() ) ) {
			return $sku;
		}
		$source = $this->languages->post_translation( $product->get_id(), Languages::SOURCE );
		return null === $source ? $sku : (string) get_post_meta( $source, '_sku', true );
	}

	/**
	 * The German version of a WooCommerce page in a German request (filters
	 * `woocommerce_get_{shop,cart,checkout,myaccount,terms}_page_id`).
	 *
	 * @param int|string $page_id Page ID.
	 * @return int|string
	 */
	public function page_id( $page_id ) {
		if ( ! $this->german_request() ) {
			return $page_id;
		}
		return $this->languages->post_translation( (int) $page_id, Languages::TARGET ) ?? $page_id;
	}

	/**
	 * The German product of an English product, in a German front-end or REST
	 * request; null otherwise.
	 *
	 * @param mixed $product Product.
	 */
	private function german_of( $product ): ?int {
		if ( ! $product instanceof \WC_Product ) {
			return null;
		}
		return $this->german_of_id( $product->get_id() );
	}

	/**
	 * The German product of an English product ID, in a German front-end or
	 * REST request; null otherwise.
	 *
	 * @param int $product_id Product ID.
	 */
	private function german_of_id( int $product_id ): ?int {
		if ( ! $this->german_request() || Languages::SOURCE !== $this->languages->of_post( $product_id ) ) {
			return null;
		}
		return $this->languages->post_translation( $product_id, Languages::TARGET );
	}

	/**
	 * Whether the request is a German one outside the admin screens.
	 */
	private function german_request(): bool {
		return ! is_admin() && Languages::TARGET === $this->languages->current();
	}
}
