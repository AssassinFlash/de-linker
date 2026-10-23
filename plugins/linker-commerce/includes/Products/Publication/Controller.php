<?php
/**
 * Current publication contracts and authenticated preparation leases.
 *
 * @package Linker\Commerce
 */
declare( strict_types = 1 );
namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;
use WP_REST_Request;
use WP_REST_Response;
use WP_Error;

/** REST authentication uses native WordPress Application Passwords/capabilities. */
final class Controller {
	public function register_routes(): void {
		foreach ( array( 'manifest' => 'GET', 'validate' => 'POST', 'identify' => 'POST', 'jobs/claim' => 'POST', 'jobs/ack' => 'POST' ) as $path => $method ) {
			register_rest_route( 'linker/v1', '/publication/' . $path, array( 'methods' => $method, 'permission_callback' => str_starts_with( $path, 'jobs/' ) ? array( $this, 'worker_permission' ) : '__return_true', 'callback' => function ( WP_REST_Request $request ) use ( $path ): WP_REST_Response|WP_Error { return $this->dispatch( $path, $request ); } ) );
		}
	}

	public function worker_permission(): bool {
		return current_user_can( 'manage_woocommerce' );
	}

	/** @return WP_REST_Response|WP_Error */
	public function dispatch( string $path, WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$body = $request->get_json_params();
		$body = is_array( $body ) ? $body : array();
		if ( 'manifest' === $path ) {
			$data = Publication::manifest();
		} elseif ( 'validate' === $path ) {
			$data = Publication::validate( $body );
		} elseif ( 'identify' === $path ) {
			$data = $this->identify( $body );
		} elseif ( 'jobs/claim' === $path ) {
			$data = ( new PreparationJobs() )->claim( (string) ( $body['consumer'] ?? '' ), (string) ( $body['worker_id'] ?? '' ), (int) ( $body['lease_seconds'] ?? 0 ) );
		} else {
			$data = ( new PreparationJobs() )->acknowledge( $body );
		}
		if ( is_wp_error( $data ) ) {
			return $data;
		}
		$response = new WP_REST_Response( $data );
		$response->header( 'Cache-Control', 'no-store, private, max-age=0' );
		$response->header( 'Pragma', 'no-cache' );
		return $response;
	}

	/** Exact caller-supplied labels only; no draft facts or complete model list. @param array<string,mixed> $body @return array<string,mixed>|WP_Error */
	private function identify( array $body ): array|WP_Error {
		$labels = $body['models'] ?? null;
		// Request-size bounds protect the public exact-match oracle, not product facts.
		if ( ! is_array( $labels ) || ! array_is_list( $labels ) || count( $labels ) > 20 ) {
			return new WP_Error( 'invalid_models', 'Supply at most 20 model labels.', array( 'status' => 400 ) );
		}
		$known = array();
		$ids = get_posts( array( 'post_type' => 'product', 'post_status' => array( 'publish', 'draft', 'pending', 'private', 'future', 'trash' ), 'fields' => 'ids', 'posts_per_page' => -1, 'suppress_filters' => true ) );
		foreach ( $ids as $id ) {
			$terms = wp_get_object_terms( (int) $id, 'pa_model', array( 'fields' => 'names' ) );
			if ( is_wp_error( $terms ) ) {
				continue;
			}
			foreach ( $terms as $model ) {
				$key = strtolower( trim( $model ) );
				if ( ! isset( $known[ $key ] ) || self::published( (int) $id ) ) {
					$known[ $key ] = (int) $id;
				}
			}
		}
		$result = array();
		foreach ( $labels as $label ) {
			if ( ! is_string( $label ) || strlen( $label ) > 200 || '' === trim( $label ) ) {
				return new WP_Error( 'invalid_models', 'Invalid model label.', array( 'status' => 400 ) );
			}
			$id = $known[ strtolower( trim( $label ) ) ] ?? 0;
			$item = array( 'model' => $label, 'status' => 0 === $id ? 'unknown' : ( self::published( $id ) ? 'published' : 'unavailable' ) );
			if ( 'published' === $item['status'] ) {
				$item['product_id'] = Publication::canonical_id( $id );
			}
			$result[] = $item;
		}
		return array( 'models' => $result );
	}

	private static function published( int $id ): bool {
		return Publication::is_published( $id );
	}
}
