<?php
/**
 * The shop in German: pages, product names and the cart.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Woo;

use Linker\I18n\Languages;
use Linker\I18n\Rest\RestLang;

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
 * for the English ids (`include=`) with `lang=de`, and RestLang leaves a
 * query by id on those records, so the price copy was already German while
 * `permalink` stayed `get_permalink()` of the English product (`/product/…`).
 * {@see self::store_product_links()} replaces it with the German twin's
 * permalink: `pll_get_post` through {@see Languages::post_translation()}, then
 * `get_permalink` (`/de/produkt/…`). The card, the configurator and the hero
 * read that field and do not resolve a second URL. Any other `lang`,
 * including `all`, keeps `/product/…`.
 */
final class Storefront {

	/**
	 * `rest_request_after_callbacks` priority.
	 *
	 * Below RestLang::leave and linker-commerce StoreApiPrices, both 10.
	 * StoreApiPrices::PRIORITY is the other half: a test asserts this stays
	 * lower. The product check does not read a set `prices` value, so a
	 * later move still rewrites the link; the test is what makes the move fail.
	 */
	public const PRODUCT_LINKS_PRIORITY = 9;

	/**
	 * First path segments under `/wc/store/v1/products` that are not a product.
	 *
	 * WooCommerce 11.2.0 registers these beside Products, ProductsById and
	 * ProductsBySlug (`src/StoreApi/RoutesController.php`, namespace
	 * `wc/store`, version `v1`). The path is `get_path_regex()` of
	 * ProductAttributes, ProductAttributesById, ProductAttributeTerms,
	 * ProductBrands, ProductBrandsById, ProductCategories,
	 * ProductCategoriesById, ProductCollectionData, ProductReviews and
	 * ProductTags. Each collection is one segment; the by-id routes add
	 * another, so they miss the single-segment match. The list is these
	 * segments and nothing else — a shape test locks it to that source.
	 *
	 * @var list<string>
	 */
	public const STORE_PRODUCT_NEIGHBOURS = array(
		'attributes',
		'brands',
		'categories',
		'collection-data',
		'reviews',
		'tags',
	);

	/**
	 * The Store API product collection. One product is this plus one segment
	 * that is not a {@see self::STORE_PRODUCT_NEIGHBOURS} entry.
	 */
	private const STORE_PRODUCT_COLLECTION = '/wc/store/v1/products';

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
	 * Priority {@see self::PRODUCT_LINKS_PRIORITY}. German means the request's
	 * `lang` is `de`, not the ambient language: `lang=all` makes RestLang
	 * enter nothing, and a German page would otherwise relink English rows.
	 * See the class note for why the link is resolved here and not in the card.
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
		if ( ! $this->store_product_route( (string) $request->get_route() ) || ! $this->german_store_request( $request ) || 400 <= $response->get_status() ) {
			return $response;
		}
		$data = $response->get_data();
		if ( ! is_array( $data ) ) {
			return $response;
		}
		$linked = $this->german_product_links( $data );
		// An untouched payload is left as WooCommerce wrote it. set_data()
		// runs only when a permalink actually changed.
		if ( $linked !== $data ) {
			$response->set_data( $linked );
		}
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
	 * Whether this Store API request asked for German (`lang=de`).
	 *
	 * Ambient {@see Languages::current()} is not enough. RestLang enters no
	 * language for `lang=all`, so a German page would otherwise relink the
	 * English products in that list. A missing `lang` is not German either:
	 * the card sends `lang` explicitly.
	 *
	 * @param \WP_REST_Request $request Request.
	 *
	 * @phpstan-param \WP_REST_Request<array<string, mixed>> $request
	 */
	private function german_store_request( \WP_REST_Request $request ): bool {
		return ! is_admin() && Languages::TARGET === $request->get_param( RestLang::PARAM );
	}

	/**
	 * A Store API product route: the collection, or one product by id or slug.
	 *
	 * The excluded segments are {@see self::STORE_PRODUCT_NEIGHBOURS}. `$`
	 * anchors each of them, so `categories-extra` is still a product slug and
	 * `categories/{id}` fails the one-segment match.
	 *
	 * @param string $route REST route, or the route pattern `get_route()` returns.
	 */
	private function store_product_route( string $route ): bool {
		if ( self::STORE_PRODUCT_COLLECTION === $route ) {
			return true;
		}
		$excluded   = implode(
			'|',
			array_map(
				static fn( string $segment ): string => preg_quote( $segment, '#' ) . '$',
				self::STORE_PRODUCT_NEIGHBOURS
			)
		);
		$collection = preg_quote( self::STORE_PRODUCT_COLLECTION, '#' );
		return 1 === preg_match( '#^' . $collection . '/(?!' . $excluded . ')[^/]+$#', $route );
	}

	/**
	 * Product payloads with the German permalink of each English product.
	 *
	 * @param array<mixed> $data One product or a list of them.
	 * @return array<mixed>
	 */
	private function german_product_links( array $data ): array {
		$one = $this->relink_store_product( $data );
		if ( null !== $one ) {
			return $one;
		}
		foreach ( $data as $key => $item ) {
			if ( ! is_array( $item ) ) {
				continue;
			}
			$relinked = $this->relink_store_product( $item );
			if ( null !== $relinked ) {
				$data[ $key ] = $relinked;
			}
		}
		return $data;
	}

	/**
	 * One Store API product with its German permalink, or null when $data is
	 * not a product.
	 *
	 * A product is a numeric `id`, a string `permalink`, and a `prices` key
	 * (WooCommerce 11.2.0 ProductSchema). linker-commerce StoreApiPrices walks
	 * the same payload on this hook and may set `prices` to null; `isset()`
	 * is then false, so the key is tested with `array_key_exists`. The price
	 * rule stays in that class. This helper is the only shape check: the
	 * caller does not validate the id and permalink again.
	 *
	 * The twin lookup does not ask {@see self::german_request()}. The caller
	 * already decided the request is `lang=de`, including after RestLang has
	 * restored the ambient language.
	 *
	 * @param array<mixed> $data Response value.
	 * @return array<mixed>|null The product, relinked when it has a German twin.
	 */
	private function relink_store_product( array $data ): ?array {
		$id        = $data['id'] ?? null;
		$permalink = $data['permalink'] ?? null;
		if ( ! is_numeric( $id ) || ! is_string( $permalink ) || ! array_key_exists( 'prices', $data ) ) {
			return null;
		}
		if ( Languages::SOURCE !== $this->languages->of_post( (int) $id ) ) {
			return $data;
		}
		$german = $this->languages->post_translation( (int) $id, Languages::TARGET );
		if ( null === $german ) {
			return $data;
		}
		$link = get_permalink( $german );
		if ( is_string( $link ) && '' !== $link ) {
			$data['permalink'] = $link;
		}
		return $data;
	}
}
