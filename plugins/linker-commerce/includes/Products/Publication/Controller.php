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
		// Twenty 16,000-byte windows need at most six JSON escape bytes per byte.
		// The 2 MiB envelope also bounds unrelated fields before JSON decoding.
		if ( 'identify' === $path && strlen( $request->get_body() ) > 2 * 1024 * 1024 ) {
			return new WP_Error( 'invalid_models', 'Identification request exceeds its JSON budget.', array( 'status' => 400 ) );
		}
		$body = self::json_object( $request->get_json_params() );
		try {
			if ( 'manifest' === $path ) {
				$data = Publication::manifest();
			} elseif ( 'validate' === $path ) {
				$data = Publication::validate( $body );
			} elseif ( 'identify' === $path ) {
				$data = $this->identify( $body );
			} elseif ( 'jobs/claim' === $path ) {
				if ( isset( $body['operation'] ) && 'verify' !== $body['operation'] ) {
					return new WP_Error( 'invalid_job_request', 'Unknown preparation operation.', array( 'status' => 400 ) );
				}
				if ( 'verify' === ( $body['operation'] ?? '' ) ) {
					$data = ( new PreparationJobs() )->verify_lease( $body );
				} else {
					$recipe      = $body['recipe_revision'] ?? '';
					$loaded      = $body['loaded_receipt'] ?? null;
					$unavailable = true === ( $body['loaded_unavailable'] ?? false );
					if ( null !== $loaded && ! is_array( $loaded ) ) {
						return new WP_Error( 'invalid_job_request', 'Loaded receipt must be an object.', array( 'status' => 400 ) );
					}
					$data = ( new PreparationJobs() )->claim( (string) ( $body['consumer'] ?? '' ), (string) ( $body['worker_id'] ?? '' ), (int) ( $body['lease_seconds'] ?? 0 ), is_string( $recipe ) ? $recipe : 'invalid', $loaded, $unavailable, is_string( $body['identity_protocol'] ?? null ) ? $body['identity_protocol'] : '', is_string( $body['ack_recovery_protocol'] ?? null ) ? $body['ack_recovery_protocol'] : '' );
				}
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
		if ( array_key_exists( 'texts', $body ) ) {
			return $this->identify_batch( $body );
		}
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
		return array(
			'models'                  => $result,
			'model_identity_revision' => Publication::model_identity_revision( $known ),
		);
	}

	/**
	 * Leased build-only batching; public single-window limits remain unchanged.
	 *
	 * @param array<string,mixed> $body Exact lease and independent original windows.
	 * @return array<string,mixed>|WP_Error
	 */
	private function identify_batch( array $body ): array|WP_Error {
		if ( ! $this->worker_permission() ) {
			return new WP_Error( 'identity_authentication_required', 'Knowledge batch identification requires a native worker.', array( 'status' => is_user_logged_in() ? 403 : 401 ) );
		}
		$texts = $body['texts'];
		// Existing bounds: twenty exact inputs and 16,000 UTF-8 bytes per text.
		// This authenticated operation combines those limits, not their permissions.
		if ( ! is_array( $texts ) || ! array_is_list( $texts ) || count( $texts ) < 1 || count( $texts ) > 20 || array_key_exists( 'text', $body ) || array_key_exists( 'models', $body ) ) {
			return new WP_Error( 'invalid_models', 'Supply at most 20 independent bounded text windows.', array( 'status' => 400 ) );
		}
		$bytes = 0;
		foreach ( $texts as $text ) {
			if ( ! is_string( $text ) || '' === trim( $text ) || strlen( $text ) > 16000 || 1 !== preg_match( '//u', $text ) ) {
				return new WP_Error( 'invalid_models', 'Each text window must contain at most 16000 UTF-8 bytes.', array( 'status' => 400 ) );
			}
			$bytes += strlen( $text );
		}
		if ( $bytes > 320000 ) {
			return new WP_Error( 'invalid_models', 'The text batch exceeds its input budget.', array( 'status' => 400 ) );
		}
		$started          = microtime( true );
		$known            = Publication::model_statuses();
		$identity         = Publication::model_identity_revision( $known );
		$identity_seconds = microtime( true ) - $started;
		$verified         = ( new PreparationJobs() )->verify_identity_lease( $body, $identity );
		if ( $verified instanceof WP_Error ) {
			return $verified;
		}
		$started    = microtime( true );
		$normalized = array_map( static fn ( string $text ): ?string => preg_replace( '/\s+/u', ' ', $text ), $texts );
		$result     = array();
		foreach ( $known as $label => $permission ) {
			$pattern = '/(?<![\pL\pN])' . preg_quote( $label, '/' ) . '(?![\pL\pN])/iu';
			foreach ( $normalized as $text ) {
				if ( is_string( $text ) && 1 === preg_match( $pattern, $text ) ) {
					$item = array(
						'model'  => $label,
						'status' => $permission['status'],
					);
					if ( 'published' === $permission['status'] ) {
						$item['product_id'] = $permission['product_id'];
					}
					$result[] = $item;
					break;
				}
			}
		}
		return array(
			'models'                  => $result,
			'model_identity_revision' => $identity,
			'metrics'                 => array(
				'input_windows'    => count( $texts ),
				'input_bytes'      => $bytes,
				'identity_reads'   => 1,
				'identity_seconds' => $identity_seconds,
				'match_seconds'    => microtime( true ) - $started,
			),
		);
	}
}
