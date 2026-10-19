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
 *
 * The Store API product `permalink` is that German link (#413). Genie asks
 * for the English ids (`include=`), and RestLang leaves a query by id on
 * those records, so `lang=de` was already making the price copy German while
 * `permalink` stayed `get_permalink()` of the English product (`/product/…`).
 * {@see self::store_product_links()} replaces it with the German twin's
 * permalink: `pll_get_post` through {@see Languages::post_translation()}, then
 * `get_permalink` (`/de/produkt/…`). The card, the configurator and the hero
 * read that field and do not resolve a second URL. English requests keep
 * `/product/…`.
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
	 * The German permalink on a Store API product (filter
	 * `rest_request_after_callbacks`).
	 *
	 * Priority 9, while RestLang still holds the request language. See the
	 * class note for why the link is resolved here and not in the card.
	 *
	 * @param mixed                $response Response so far.
	 * @param array<string, mixed> $handler  Route handler.
	 * @param mixed                $request  Request.
	 * @return mixed
	 */
	public function store_product_links( $response, array $handler, $request ) {
		unset( $handler );
		if ( ! $response instanceof \WP_REST_Response || ! $request instanceof \WP_REST_Request ) {
			return $response;
		}
		// 400 is the first HTTP client error: an error body is not a product
		// payload, so its permalink is left as WooCommerce wrote it.
		if ( ! $this->store_product_route( (string) $request->get_route() ) || ! $this->german_request() || 400 <= $response->get_status() ) {
			return $response;
		}
		$data = $response->get_data();
		if ( ! is_array( $data ) ) {
			return $response;
		}
		$response->set_data( $this->german_product_links( $data ) );
		return $response;
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

	/**
	 * A Store API product route: the collection, or one product by id or slug.
	 *
	 * @param string $route REST route.
	 */
	private function store_product_route( string $route ): bool {
		if ( '/wc/store/v1/products' === $route ) {
			return true;
		}
		return 1 === preg_match( '#^/wc/store/v1/products/(?!categories$|tags$|attributes$|brands$|collection-data$|reviews$)[^/]+$#', $route );
	}

	/**
	 * Product payloads with the German permalink of each English product.
	 *
	 * @param array<mixed> $data One product or a list of them.
	 * @return array<mixed>
	 */
	private function german_product_links( array $data ): array {
		if ( $this->is_store_product( $data ) ) {
			return $this->relink_store_product( $data );
		}
		foreach ( $data as $key => $item ) {
			if ( is_array( $item ) && $this->is_store_product( $item ) ) {
				$data[ $key ] = $this->relink_store_product( $item );
			}
		}
		return $data;
	}

	/**
	 * Whether the value is one Store API product.
	 *
	 * @param array<mixed> $data Response data.
	 */
	private function is_store_product( array $data ): bool {
		return isset( $data['id'], $data['permalink'], $data['prices'] ) && is_numeric( $data['id'] ) && is_string( $data['permalink'] );
	}

	/**
	 * The product with its German permalink, when it has a German twin.
	 *
	 * @param array<mixed> $product Product payload.
	 * @return array<mixed>
	 */
	private function relink_store_product( array $product ): array {
		$id = $product['id'] ?? null;
		if ( ! is_numeric( $id ) || ! is_string( $product['permalink'] ?? null ) ) {
			return $product;
		}
		$german = $this->german_of_id( (int) $id );
		if ( null === $german ) {
			return $product;
		}
		$link = get_permalink( $german );
		if ( is_string( $link ) && '' !== $link ) {
			$product['permalink'] = $link;
		}
		return $product;
	}
}
