<?php
/**
 * The authenticated readback of the generation an engine process actually loaded.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use WP_Error;

/**
 * What the engine serves right now, never what a receipt once reported.
 *
 * An instance pulled from the site rewrites every upload address, so renewing
 * the document bindings changes every product revision: the receipts a
 * production worker left behind name a generation that no longer exists, and
 * no local process acknowledges the new one. The engine itself loaded that
 * generation (its feed came from this site), and only its own authenticated
 * readback can say so — the same trust the production worker's ACK carries.
 */
final class EngineLoadedState {
	/** Operator override for an explicitly selected engine process. */
	public const ENVIRONMENT_TOKEN = 'LINKER_ENGINE_SERVICE_TOKEN';

	/** The instance's shared service token (`linker-local serve` sets it). */
	public const CONFIG_TOKEN = 'LINKER_GENIE_SERVICE_TOKEN';

	/** The authenticated read of the loaded generation, including its products. */
	public const VERSION_PATH = '/resource/version?ready=1';

	/** Seconds to wait for the engine's own readback. */
	public const TIMEOUT_SECONDS = 15;

	/**
	 * The token the engine verifies: this invocation's override, else this instance's.
	 */
	public static function token(): string {
		$token = getenv( self::ENVIRONMENT_TOKEN );
		if ( is_string( $token ) && '' !== $token ) {
			return $token;
		}
		return defined( self::CONFIG_TOKEN ) ? (string) constant( self::CONFIG_TOKEN ) : '';
	}

	/**
	 * Read and validate the loaded generation of one engine process.
	 *
	 * @param string $engine The engine's base URL, as instance configuration.
	 * @return array{version:string,source_revision:string,compatibility_revision:string,products:list<array{product_id:int,product_revision:string}>}|WP_Error
	 */
	public static function read( string $engine ): array|WP_Error {
		$url = self::url( $engine );
		if ( $url instanceof WP_Error ) {
			return $url;
		}
		$token = self::token();
		if ( '' === $token ) {
			return new WP_Error(
				'engine_token_missing',
				sprintf( 'No engine service token: set %s or the %s constant.', self::ENVIRONMENT_TOKEN, self::CONFIG_TOKEN )
			);
		}
		$response = wp_remote_get(
			$url,
			array(
				'timeout' => self::TIMEOUT_SECONDS,
				'headers' => array(
					'accept'                 => 'application/json',
					'x-linker-service-token' => $token,
				),
			)
		);
		if ( $response instanceof WP_Error ) {
			return new WP_Error( 'engine_unreachable', sprintf( '%s did not answer: %s', $url, $response->get_error_message() ) );
		}
		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = (string) wp_remote_retrieve_body( $response );
		if ( 200 !== $status ) {
			return new WP_Error(
				'engine_rejected',
				sprintf( '%s answered HTTP %d: %s', $url, $status, self::excerpt( $body ) )
			);
		}
		return self::validated( json_decode( $body, true ) );
	}

	/**
	 * The readback route of one already-validated engine base URL.
	 *
	 * @param string $engine The engine's base URL.
	 * @return string|WP_Error
	 */
	private static function url( string $engine ): string|WP_Error {
		$engine = rtrim( trim( $engine ), '/' );
		$parts  = wp_parse_url( $engine );
		$scheme = is_array( $parts ) ? strtolower( (string) ( $parts['scheme'] ?? '' ) ) : '';
		if (
			'' === $engine
			|| ! is_array( $parts )
			|| ! in_array( $scheme, array( 'http', 'https' ), true )
			|| '' === (string) ( $parts['host'] ?? '' )
			|| isset( $parts['user'] )
			|| isset( $parts['pass'] )
			|| isset( $parts['query'] )
			|| isset( $parts['fragment'] )
			|| 1 === preg_match( '/[\s\x00-\x1f]/', $engine )
		) {
			return new WP_Error( 'invalid_engine_url', sprintf( '"%s" is not an engine base URL (http or https, no credentials, query or fragment).', $engine ) );
		}
		return $engine . self::VERSION_PATH;
	}

	/**
	 * Validate the readback; an unknown shape can never grant readiness.
	 *
	 * @param mixed $state The decoded readback.
	 * @return array{version:string,source_revision:string,compatibility_revision:string,products:list<array{product_id:int,product_revision:string}>}|WP_Error
	 */
	private static function validated( mixed $state ): array|WP_Error {
		$reject = static fn ( string $reason ): WP_Error => new WP_Error( 'invalid_engine_state', 'The engine readback is not a loaded publication generation: ' . $reason );
		if ( ! is_array( $state ) ) {
			return $reject( 'it is not a JSON object.' );
		}
		foreach ( array( 'version', 'compatibility_revision' ) as $key ) {
			if ( ! is_string( $state[ $key ] ?? null ) || '' === $state[ $key ] ) {
				return $reject( sprintf( '%s is empty.', $key ) );
			}
		}
		if ( 1 !== preg_match( '/^[a-f0-9]{64}$/D', (string) ( $state['source_revision'] ?? '' ) ) ) {
			return $reject( 'source_revision is not a revision hash.' );
		}
		$rows = $state['prepared_products'] ?? null;
		if ( ! is_array( $rows ) || ! array_is_list( $rows ) ) {
			return $reject( 'prepared_products is not a list.' );
		}
		$products = array();
		foreach ( $rows as $row ) {
			$id       = is_array( $row ) ? ( $row['product_id'] ?? null ) : null;
			$revision = is_array( $row ) ? ( $row['product_revision'] ?? null ) : null;
			if ( ! is_int( $id ) || $id < 1 || ! is_string( $revision ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $revision ) || isset( $products[ $id ] ) ) {
				return $reject( 'a prepared product is not one distinct product with a revision hash.' );
			}
			$products[ $id ] = array(
				'product_id'       => $id,
				'product_revision' => $revision,
			);
		}
		return array(
			'version'                => $state['version'],
			'source_revision'        => $state['source_revision'],
			'compatibility_revision' => $state['compatibility_revision'],
			'products'               => array_values( $products ),
		);
	}

	/**
	 * A bounded diagnostic, never an unbounded proxy response in a WP-CLI error.
	 *
	 * @param string $body The response body.
	 */
	private static function excerpt( string $body ): string {
		$body = trim( preg_replace( '/\s+/', ' ', $body ) ?? '' );
		return '' === $body ? 'no body' : ( strlen( $body ) > 300 ? substr( $body, 0, 300 ) . '…' : $body );
	}
}
