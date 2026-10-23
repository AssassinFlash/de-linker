<?php
/**
 * Native Store API and existing draft sessions follow canonical publication.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;
use WP_Error;
use WP_REST_Request;
use WP_Query;
use WC_Cart;

/** Scope native reads without changing privileged product administration. */
final class Visibility {
	/**
	 * Whether the currently running REST callback is a public product read.
	 *
	 * @var bool
	 */
	private bool $store_products = false;

	/** Register the narrow native extension points. */
	public function register(): void {
		add_filter( 'rest_request_before_callbacks', array( $this, 'enter' ), 1, 3 );
		add_filter( 'rest_request_after_callbacks', array( $this, 'leave' ), 1, 3 );
		add_action( 'pre_get_posts', array( $this, 'query' ), 100 );
		add_action( 'template_redirect', array( $this, 'single_product' ), 0 );
		add_action( 'woocommerce_cart_loaded_from_session', array( $this, 'prune' ), 1 );
		add_action( 'woocommerce_before_calculate_totals', array( $this, 'prune' ), 1 );
		add_filter( 'woocommerce_product_is_visible', array( $this, 'visible' ), 10, 2 );
	}

	/**
	 * Enter public Store API product reads, including a stale direct ID.
	 *
	 * @param mixed               $response Earlier callback response.
	 * @param array<string,mixed> $handler Handler.
	 * @param WP_REST_Request     $request Request.
	 * @phpstan-param WP_REST_Request<array<string,mixed>> $request
	 * @return mixed
	 */
	public function enter( mixed $response, array $handler, WP_REST_Request $request ): mixed {
		$this->store_products = 'GET' === $request->get_method() && 1 === preg_match( '#^/wc/store/v[0-9]+/products(?:/[^/]+)?$#D', $request->get_route() );
		if ( $this->store_products && preg_match( '#/products/([0-9]+)$#D', $request->get_route(), $matches ) && ! Publication::is_published( (int) $matches[1] ) ) {
			return new WP_Error( 'woocommerce_rest_product_invalid_id', 'Invalid product ID.', array( 'status' => 404 ) );
		}
		return $response;
	}

	/**
	 * Check direct slug results too, then leave the native callback scope.
	 *
	 * @param mixed               $response Native response.
	 * @param array<string,mixed> $handler Handler.
	 * @param WP_REST_Request     $request Request.
	 * @phpstan-param WP_REST_Request<array<string,mixed>> $request
	 * @return mixed
	 */
	public function leave( mixed $response, array $handler, WP_REST_Request $request ): mixed {
		unset( $handler, $request );
		if ( $this->store_products && $response instanceof \WP_REST_Response ) {
			$data = $response->get_data();
			if ( is_array( $data ) && isset( $data['id'] ) && ! Publication::is_published( (int) $data['id'] ) ) {
				$response = new WP_Error( 'woocommerce_rest_product_invalid_id', 'Invalid product ID.', array( 'status' => 404 ) );
			}
		}
		$this->store_products = false;
		return $response;
	}

	/**
	 * Constrain collection pagination/counts before the native query runs.
	 *
	 * @param WP_Query $query Native query.
	 */
	public function query( WP_Query $query ): void {
		$front = ! is_admin() && ( ! defined( 'REST_REQUEST' ) || ! REST_REQUEST ) && ( ! defined( 'WP_CLI' ) || ! WP_CLI );
		if ( ( ! $this->store_products && ! $front ) || $query->get( 'linker_publication_internal' ) || ! in_array( 'product', (array) $query->get( 'post_type' ), true ) || ( $query->is_preview() && current_user_can( 'manage_woocommerce' ) ) ) {
			return;
		}
		$ids     = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => 'publish',
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
			)
		);
		$allowed = array_values( array_filter( array_map( 'intval', $ids ), array( Publication::class, 'is_published' ) ) );
		$include = $query->get( 'post__in' );
		if ( is_array( $include ) && array() !== $include ) {
			$allowed = array_values( array_intersect( $include, $allowed ) );
		}
		$query->set( 'post__in', array() === $allowed ? array( 0 ) : $allowed );
	}

	/** A locale mirror cannot expose a withdrawn canonical product page. */
	public function single_product(): void {
		if ( ! is_singular( 'product' ) || ( is_preview() && current_user_can( 'edit_post', get_queried_object_id() ) ) || Publication::is_published( get_queried_object_id() ) ) {
			return;
		}
		global $wp_query;
		$wp_query->set_404();
		status_header( 404 );
		nocache_headers();
	}

	/**
	 * Existing Woo sessions cannot disclose a withdrawn product's current data.
	 *
	 * @param WC_Cart $cart Native cart.
	 */
	public function prune( WC_Cart $cart ): void {
		foreach ( $cart->get_cart_contents() as $key => $line ) {
			if ( ! Publication::is_published( (int) ( $line['product_id'] ?? 0 ) ) ) {
				$cart->remove_cart_item( $key );
			}
		}
	}

	/**
	 * Preserve Woo's own visibility and additionally require current source.
	 *
	 * @param bool $visible Woo visibility.
	 * @param int  $id Product ID.
	 */
	public function visible( bool $visible, int $id ): bool {
		return $visible && Publication::is_published( $id );
	}
}
