<?php
/**
 * The authenticated readback of the knowledge generation Genie actually loaded.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use WP_Error;

/**
 * What the serving process has open right now, never what a receipt once reported.
 *
 * Knowledge readiness is recipe-aware: the acknowledgement names the compiler
 * (`recipe_revision`), the index generation (`index_version`), the rules the
 * process runs (`serving_revision`) and the native model identity. An engine's
 * `/resource/version` carries none of these; Genie's own `/knowledge/loaded`
 * reports exactly its open index and is therefore the only local evidence that
 * can acknowledge a knowledge generation — the same readback the production
 * worker acknowledges from.
 */
final class GenieLoadedState {
	/** Operator override of the instance's service token. */
	public const ENVIRONMENT_TOKEN = 'LINKER_GENIE_SERVICE_TOKEN';

	/** The instance's shared service token (wp-config constant, set by `serve`). */
	public const CONFIG_TOKEN = 'LINKER_GENIE_SERVICE_TOKEN';

	/** The readback of the open index, including its prepared products. */
	public const LOADED_PATH = '/knowledge/loaded';

	/** Seconds to wait for Genie's own readback. */
	public const TIMEOUT_SECONDS = 30;

	/** Reasons Woo accepts for an unprepared document association. */
	public const REASONS = array( 'no_proven_passage', 'document_unparsed', 'table_without_scope' );

	/**
	 * The token Genie verifies: this invocation's override, else this instance's.
	 */
	public static function token(): string {
		$token = getenv( self::ENVIRONMENT_TOKEN );
		if ( is_string( $token ) && '' !== $token ) {
			return $token;
		}
		return defined( self::CONFIG_TOKEN ) ? (string) constant( self::CONFIG_TOKEN ) : '';
	}

	/**
	 * Read and validate the knowledge generation one Genie process has loaded.
	 *
	 * @param string $genie The Genie base URL, as instance configuration.
	 * @return array<string,mixed>|WP_Error
	 */
	public static function read( string $genie ): array|WP_Error {
		$url = self::url( $genie );
		if ( $url instanceof WP_Error ) {
			return $url;
		}
		$token = self::token();
		if ( '' === $token ) {
			return new WP_Error(
				'genie_token_missing',
				sprintf( 'No Genie service token: set %s or the %s constant.', self::ENVIRONMENT_TOKEN, self::CONFIG_TOKEN )
			);
		}
		$response = wp_remote_post(
			$url,
			array(
				'timeout' => self::TIMEOUT_SECONDS,
				'headers' => array(
					'accept'                 => 'application/json',
					'content-type'           => 'application/json',
					'x-linker-service-token' => $token,
				),
				'body'    => '{}',
			)
		);
		if ( $response instanceof WP_Error ) {
			return new WP_Error( 'genie_unreachable', sprintf( '%s did not answer: %s', $url, $response->get_error_message() ) );
		}
		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = (string) wp_remote_retrieve_body( $response );
		if ( 200 !== $status ) {
			return new WP_Error(
				'genie_rejected',
				sprintf( '%s answered HTTP %d: %s', $url, $status, self::excerpt( $body ) )
			);
		}
		return self::validated( json_decode( $body, true ) );
	}

	/**
	 * The readback route of one already-validated Genie base URL.
	 *
	 * @param string $genie The Genie base URL.
	 * @return string|WP_Error
	 */
	private static function url( string $genie ): string|WP_Error {
		$genie  = rtrim( trim( $genie ), '/' );
		$parts  = wp_parse_url( $genie );
		$scheme = is_array( $parts ) ? strtolower( (string) ( $parts['scheme'] ?? '' ) ) : '';
		if (
			'' === $genie
			|| ! is_array( $parts )
			|| ! in_array( $scheme, array( 'http', 'https' ), true )
			|| '' === (string) ( $parts['host'] ?? '' )
			|| isset( $parts['user'] )
			|| isset( $parts['pass'] )
			|| isset( $parts['query'] )
			|| isset( $parts['fragment'] )
			|| 1 === preg_match( '/[\s\x00-\x1f]/', $genie )
		) {
			return new WP_Error( 'invalid_genie_url', sprintf( '"%s" is not a Genie base URL (http or https, no credentials, query or fragment).', $genie ) );
		}
		return $genie . self::LOADED_PATH;
	}

	/**
	 * Validate the readback; an unknown shape can never grant readiness.
	 *
	 * @param mixed $state The decoded readback.
	 * @return array<string,mixed>|WP_Error
	 */
	private static function validated( mixed $state ): array|WP_Error {
		$reject = static fn ( string $reason ): WP_Error => new WP_Error( 'invalid_genie_state', 'The Genie readback is not a loaded knowledge generation: ' . $reason );
		if ( ! is_array( $state ) ) {
			return $reject( 'it is not a JSON object.' );
		}
		foreach ( array( 'source_revision', 'model_identity_revision', 'recipe_revision', 'expected_serving_revision', 'serving_revision' ) as $key ) {
			if ( 1 !== preg_match( '/^[a-f0-9]{64}$/D', (string) ( $state[ $key ] ?? '' ) ) ) {
				return $reject( sprintf( '%s is not a revision hash.', $key ) );
			}
		}
		if ( 1 !== preg_match( '/^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/D', (string) ( $state['index_version'] ?? '' ) ) ) {
			return $reject( 'index_version is empty or not a generation name.' );
		}
		if ( ( $state['serving_revision'] ?? '' ) !== ( $state['expected_serving_revision'] ?? null ) ) {
			return $reject( 'the open index was built for different serving rules, so this process cannot serve it.' );
		}
		if ( ! is_int( $state['activation_epoch'] ?? null ) || $state['activation_epoch'] < 0 ) {
			return $reject( 'activation_epoch is not a non-negative integer.' );
		}
		foreach ( array( 'materialization_complete', 'preparation_complete' ) as $key ) {
			if ( ! is_bool( $state[ $key ] ?? null ) ) {
				return $reject( sprintf( '%s is not a boolean.', $key ) );
			}
		}
		$rows = $state['products'] ?? null;
		if ( ! is_array( $rows ) || ! array_is_list( $rows ) ) {
			return $reject( 'products is not a list.' );
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
		$diagnostics = self::diagnostics( $state['unprepared_documents'] ?? null );
		if ( $diagnostics instanceof WP_Error ) {
			return $diagnostics;
		}
		return array(
			'index_version'             => $state['index_version'],
			'source_revision'           => $state['source_revision'],
			'model_identity_revision'   => $state['model_identity_revision'],
			'recipe_revision'           => $state['recipe_revision'],
			'expected_serving_revision' => $state['expected_serving_revision'],
			'serving_revision'          => $state['serving_revision'],
			'activation_epoch'          => $state['activation_epoch'],
			'products'                  => array_values( $products ),
			'materialization_complete'  => $state['materialization_complete'],
			'preparation_complete'      => $state['preparation_complete'],
			'unprepared_documents'      => $diagnostics,
		);
	}

	/**
	 * The bounded per-association diagnostics, never document text.
	 *
	 * Woo re-validates every row against the current manifest; this only keeps an
	 * unknown reason from travelling to that check as an opaque 400.
	 *
	 * @param mixed $rows The decoded rows.
	 * @return list<array{document_id:string,product_id:int,reason:string}>|WP_Error
	 */
	private static function diagnostics( mixed $rows ): array|WP_Error {
		if ( ! is_array( $rows ) || ! array_is_list( $rows ) ) {
			return new WP_Error( 'invalid_genie_state', 'The Genie readback is not a loaded knowledge generation: unprepared_documents is not a list.' );
		}
		$result = array();
		foreach ( $rows as $row ) {
			$id = is_array( $row ) && is_string( $row['document_id'] ?? null ) ? $row['document_id'] : '';
			if ( '' === $id || ! is_int( $row['product_id'] ?? null ) || ! in_array( $row['reason'] ?? null, self::REASONS, true ) ) {
				return new WP_Error( 'invalid_genie_state', 'The Genie readback is not a loaded knowledge generation: an unprepared document row is malformed.' );
			}
			$result[] = array(
				'document_id' => $id,
				'product_id'  => $row['product_id'],
				'reason'      => $row['reason'],
			);
		}
		return $result;
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
