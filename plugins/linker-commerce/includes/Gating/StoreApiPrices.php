<?php
/**
 * Prices in the Store API for visitors who may not see them.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Gating;

use WP_REST_Request;
use WP_REST_Response;

/**
 * In wc/store/v1 product responses, a product whose price the visitor may not
 * see has "prices": null (docs/specs/11-commerce.md, Gating). Without this the
 * Store API would format the empty price as "0", which reads as a price of zero.
 */
final class StoreApiPrices {

	/**
	 * `rest_request_after_callbacks` priority.
	 *
	 * The linker-i18n Storefront rewrites product permalinks on the same hook at
	 * Storefront::PRODUCT_LINKS_PRIORITY and stays ahead of this. This filter
	 * sets `prices` to null; Storefront still recognises that product
	 * (`array_key_exists( 'prices' )`, not `isset`). The two plugins walk one
	 * Store API product shape — numeric `id`, string `permalink`, `prices`
	 * present — and do not share a helper: each plugin loads without the other.
	 */
	public const PRIORITY = 10;

	/**
	 * Sets up the filter.
	 *
	 * @param CommerceState $state The price rule.
	 */
	public function __construct( private readonly CommerceState $state ) {}

	/**
	 * Nulls hidden prices in product responses; runs on
	 * rest_request_after_callbacks, which WordPress applies to every REST
	 * request, also to those made inside a page (rest_do_request(), the
	 * preloading of blocks), unlike rest_post_dispatch.
	 *
	 * @param mixed           $response Response of the endpoint.
	 * @param mixed           $handler  Route handler.
	 * @param WP_REST_Request $request  Request.
	 * @return mixed
	 */
	public function filter( $response, $handler, WP_REST_Request $request ) {
		if ( ! $response instanceof WP_REST_Response || ! str_starts_with( $request->get_route(), '/wc/store/v1/products' ) ) {
			return $response;
		}
		$data = $response->get_data();
		if ( ! is_array( $data ) ) {
			return $response;
		}
		if ( isset( $data['id'] ) ) {
			$data = $this->null_prices( $data );
		} else {
			$data = array_map( fn ( $item ) => is_array( $item ) ? $this->null_prices( $item ) : $item, $data );
		}
		$response->set_data( $data );
		return $response;
	}

	/**
	 * One product of a response, with "prices" null when the visitor may not see them.
	 *
	 * The same response is a product to linker-i18n Storefront when it has a
	 * numeric `id`, a string `permalink` and a `prices` key. Nulling the key's
	 * value here must leave the key in place: Storefront's check is
	 * `array_key_exists`, because `isset` would drop the German permalink
	 * whenever this filter runs first.
	 *
	 * @param array<string, mixed> $item Product response.
	 * @return array<string, mixed>
	 */
	private function null_prices( array $item ): array {
		$product = isset( $item['id'] ) ? wc_get_product( (int) $item['id'] ) : null;
		if ( $product instanceof \WC_Product && null !== $this->state->reason( $product, CommerceState::CARD ) ) {
			$item['prices'] = null;
		}
		return $item;
	}
}
