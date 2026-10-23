<?php
/** Current Woo permission for native engine results and private receipts.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Protection;

use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Products\Publication;
use WP_Error;
use WP_REST_Response;

/** Publication correctness never follows the anti-abuse switch. */
final class EnginePublication {
	/**
	 * Request-local proof, never a client-selected authority.
	 *
	 * @var \WeakMap<WP_REST_Response,array<string,mixed>>|null
	 */
	private static ?\WeakMap $proofs = null;

	/**
	 * Server-selected consumer of this proof.
	 *
	 * @var \WeakMap<WP_REST_Response,string>|null
	 */
	private static ?\WeakMap $kinds = null;

	/**
	 * Validate trusted service dependencies against the owning Woo module.
	 *
	 * @param array<string,mixed> $dependencies Trusted service dependencies.
	 * @param string              $kind Server-selected proof consumer.
	 */
	public static function validate( array $dependencies, string $kind = 'engineering' ): true|WP_Error {
		if ( ! isset( $dependencies['products'], $dependencies['documents'] ) ) {
			return self::failure();
		}
		if ( ! class_exists( Publication::class ) || ! class_exists( DesignProof::class ) ) {
			return self::failure( 503 );
		}
		if ( 'genie' !== $kind && ! DesignProof::has_engineering_proof( $dependencies ) ) {
			return self::failure();
		}
		try {
			$result = Publication::validate( $dependencies );
		} catch ( \RuntimeException $exception ) {
			return self::failure( 503 );
		}
		return ! empty( $result['valid'] ) ? true : self::failure();
	}

	/**
	 * Store proof without adding HTTP headers.
	 *
	 * @param WP_REST_Response    $reply Native service response.
	 * @param array<string,mixed> $dependencies Trusted service dependencies.
	 * @param string              $kind Server-selected proof consumer.
	 */
	public static function remember( WP_REST_Response $reply, array $dependencies, string $kind = 'engineering' ): void {
		self::$proofs         ??= new \WeakMap();
		self::$proofs[ $reply ] = $dependencies;
		self::$kinds          ??= new \WeakMap();
		self::$kinds[ $reply ] = 'genie' === $kind ? 'genie' : 'engineering';
	}

	/**
	 * Browser JSON cannot select another consumer's proof contract.
	 *
	 * @param WP_REST_Response $reply Trusted native reply.
	 */
	public static function kind( WP_REST_Response $reply ): string {
		return null !== self::$kinds && isset( self::$kinds[ $reply ] ) ? self::$kinds[ $reply ] : 'engineering';
	}

	/**
	 * Read trusted proof from a live or restored response.
	 *
	 * @param WP_REST_Response $reply Native service response.
	 * @return array<string,mixed>
	 */
	public static function dependencies( WP_REST_Response $reply ): array {
		if ( null !== self::$proofs && isset( self::$proofs[ $reply ] ) ) {
			return self::$proofs[ $reply ];
		}
		$data = $reply->get_data();
		$data = is_string( $data ) ? json_decode( $data, true ) : $data;
		return is_array( $data ) && is_array( $data['publication'] ?? null ) ? $data['publication'] : array();
	}

	/**
	 * An old receipt without proof cannot authorize a current action.
	 *
	 * @param WP_REST_Response|WP_Error $reply Native receipt.
	 */
	public static function reply( WP_REST_Response|WP_Error $reply ): WP_REST_Response|WP_Error {
		if ( is_wp_error( $reply ) || $reply->get_status() >= 400 ) {
			return $reply;
		}
		$valid = self::validate( self::dependencies( $reply ), self::kind( $reply ) );
		return is_wp_error( $valid ) ? $valid : $reply;
	}

	/**
	 * Reuse the established translated refusal surface.
	 *
	 * @param int $status A stale selection or unavailable authority.
	 */
	private static function failure( int $status = 409 ): WP_Error {
		return new WP_Error( 503 === $status ? 'linker_publication_unavailable' : 'linker_publication_changed', __( 'Your request could not be completed. Your input is still here. Please try again.', 'linker-tools' ), array( 'status' => $status ) );
	}
}
