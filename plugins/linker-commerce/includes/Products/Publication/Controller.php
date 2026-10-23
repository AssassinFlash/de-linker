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
	/** Register public permission reads and authenticated preparation writes. */
	public function register_routes(): void {
		foreach ( array(
			'manifest'   => 'GET',
			'validate'   => 'POST',
			'identify'   => 'POST',
			'jobs/claim' => 'POST',
			'jobs/ack'   => 'POST',
		) as $path => $method ) {
			register_rest_route(
				'linker/v1',
				'/publication/' . $path,
				array(
					'methods'             => $method,
					'permission_callback' => str_starts_with( $path, 'jobs/' ) ? array( $this, 'worker_permission' ) : '__return_true',
					'callback'            => function ( WP_REST_Request $request ) use ( $path ): WP_REST_Response|WP_Error {
						return $this->dispatch( $path, $request );
					},
				)
			);
		}
	}

	/**
	 * Reject scalar JSON as an empty request object without trusting stub narrowing.
	 *
	 * @param mixed $value Decoded JSON.
	 * @return array<string,mixed>
	 */
	private static function json_object( mixed $value ): array {
		return is_array( $value ) ? $value : array();
	}

	/** Use native WordPress capability authentication for build workers. */
	public function worker_permission(): bool {
		return current_user_can( 'manage_woocommerce' );
	}

	/**
	 * Dispatch the minimal shared contract.
	 *
	 * @param string          $path Registered action.
	 * @param WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string,mixed>> $request
	 * @return WP_REST_Response|WP_Error
	 */
	public function dispatch( string $path, WP_REST_Request $request ): WP_REST_Response|WP_Error {
		nocache_headers();
		$body = self::json_object( $request->get_json_params() );
		try {
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
		} catch ( \RuntimeException $error ) {
			return new WP_Error( 'publication_unavailable', 'Current product permission could not be checked.', array( 'status' => 503 ) );
		}
		if ( is_wp_error( $data ) ) {
			return $data;
		}
		$response = new WP_REST_Response( $data );
		$response->header( 'Cache-Control', 'no-store, private, max-age=0' );
		$response->header( 'Pragma', 'no-cache' );
		return $response;
	}

	/**
	 * Exact caller-supplied labels only; no draft facts or complete model list.
	 *
	 * @param array<string,mixed> $body Caller supplied labels.
	 * @return array<string,mixed>|WP_Error
	 */
	private function identify( array $body ): array|WP_Error {
		$labels = $body['models'] ?? array();
		$text   = $body['text'] ?? null;
		if ( null !== $text && ( ! is_string( $text ) || strlen( $text ) > 16000 || isset( $body['models'] ) ) ) {
			return new WP_Error( 'invalid_models', 'Supply either model labels or bounded input text.', array( 'status' => 400 ) );
		}
		// Request-size bounds protect the public exact-match oracle, not product facts.
		if ( ! is_array( $labels ) || ! array_is_list( $labels ) || count( $labels ) > 20 ) {
			return new WP_Error( 'invalid_models', 'Supply at most 20 model labels.', array( 'status' => 400 ) );
		}
		$known = Publication::model_statuses();
		if ( is_string( $text ) ) {
			$normalized = preg_replace( '/\s+/u', ' ', $text );
			foreach ( array_keys( $known ) as $label ) {
				$pattern = '/(?<![\pL\pN])' . preg_quote( $label, '/' ) . '(?![\pL\pN])/iu';
				if ( is_string( $normalized ) && 1 === preg_match( $pattern, $normalized ) ) {
					$labels[] = $label;
				}
			}
		}
		$result = array();
		foreach ( $labels as $label ) {
			if ( ! is_string( $label ) || strlen( $label ) > 200 || '' === trim( $label ) ) {
				return new WP_Error( 'invalid_models', 'Invalid model label.', array( 'status' => 400 ) );
			}
			$permission = $known[ strtolower( trim( $label ) ) ] ?? array();
			$item       = array(
				'model'  => $label,
				'status' => $permission['status'] ?? 'unknown',
			);
			if ( 'published' === ( $permission['status'] ?? '' ) ) {
				$item['product_id'] = $permission['product_id'];
			}
			$result[] = $item;
		}
		return array( 'models' => $result );
	}
}
