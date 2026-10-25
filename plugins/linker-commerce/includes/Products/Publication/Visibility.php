<?php
/**
 * Native Store API and existing draft sessions follow canonical publication.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\EngineeringReference;
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
		// Run after PriceDisplay's native unpriced-inquiry permission at priority 10.
		add_filter( 'woocommerce_is_purchasable', array( $this, 'purchasable' ), 20, 2 );
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
		$this->store_products = in_array( $request->get_method(), array( 'GET', 'HEAD' ), true ) && 1 === preg_match( '#^/wc/store/v[0-9]+/products(?:/[^/]+)?$#D', $request->get_route() );
		if ( $this->store_products && preg_match( '#/products/([0-9]+)$#D', $request->get_route(), $matches ) && ! self::sales_product( (int) $matches[1] ) ) {
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
			if ( is_array( $data ) && isset( $data['id'] ) && ! self::sales_product( (int) $data['id'] ) ) {
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
		$mixed   = array() !== array_diff( (array) $query->get( 'post_type' ), array( 'product' ) );
		$ids     = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => $mixed ? array_values( get_post_stati() ) : 'publish',
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'cache_results'               => false,
			)
		);
		$allowed = array_values( array_filter( Publication::published_ids( array_map( 'intval', $ids ) ), static fn ( int $id ): bool => ! EngineeringReference::is_reference( $id ) ) );
		$include = $query->get( 'post__in' );
		if ( $mixed ) {
			// A product-only allow-list would erase matching pages and posts.
			// Read every native product status so drafts and private records also
			// remain excluded when a caller supplies its own include/status list.
			$denied = array_values( array_diff( array_map( 'intval', $ids ), $allowed ) );
			if ( is_array( $include ) && array() !== $include ) {
				// Native WP_Query gives post__in precedence over post__not_in.
				$include = array_values( array_diff( array_map( 'absint', $include ), $denied ) );
				$query->set( 'post__in', array() === $include ? array( 0 ) : $include );
			} else {
				$exclude = $query->get( 'post__not_in' );
				$exclude = is_array( $exclude ) ? array_map( 'absint', $exclude ) : array();
				$query->set( 'post__not_in', array_values( array_unique( array_merge( $exclude, $denied ) ) ) );
			}
			return;
		}
		if ( is_array( $include ) && array() !== $include ) {
			$allowed = array_values( array_intersect( $include, $allowed ) );
		}
		$query->set( 'post__in', array() === $allowed ? array( 0 ) : $allowed );
	}

	/** A locale mirror cannot expose a withdrawn canonical product page. */
	public function single_product(): void {
		if ( ! is_singular( 'product' ) || ( is_preview() && current_user_can( 'edit_post', get_queried_object_id() ) ) || self::sales_product( get_queried_object_id() ) ) {
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
			if ( ! self::sales_product( (int) ( $line['product_id'] ?? 0 ) ) ) {
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
		return $visible && self::sales_product( $id );
	}

	/**
	 * Keep reference records out of native cart additions even if priced later.
	 *
	 * @param bool        $purchasable Native permission.
	 * @param \WC_Product $product Product or variation.
	 */
	public function purchasable( bool $purchasable, \WC_Product $product ): bool {
		$id = $product->get_parent_id() > 0 ? $product->get_parent_id() : $product->get_id();
		return $purchasable && self::sales_product( $id );
	}

	/**
	 * Public commerce scope, narrower than engineering publication.
	 *
	 * @param int $id Locale or source product.
	 */
	private static function sales_product( int $id ): bool {
		return Publication::is_published( $id ) && ! EngineeringReference::is_reference( $id );
	}
}
