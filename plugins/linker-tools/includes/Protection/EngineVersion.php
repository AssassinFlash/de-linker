<?php
/**
 * Read the running engine snapshot before reusing an engineering result.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use WP_Error;

/** No durable cache or static deployment stamp may stand in for live readback. */
final class EngineVersion {
	/**
	 * One native REST request can reuse its own successful or failed handshake.
	 *
	 * @var \WeakMap<object,string|WP_Error>
	 */
	private \WeakMap $requests;

	/**
	 * Trusted test transport; never a browser-selected version.
	 *
	 * @param \Closure|null $read Optional server-owned version lookup.
	 */
	public function __construct( private readonly ?\Closure $read = null ) {
		$this->requests = new \WeakMap();
	}

	/**
	 * Fetch only the configured private service using its existing token.
	 *
	 * @param object|null $request Current request scope, never a persisted key.
	 * @return string|WP_Error Actual loaded source/feed/contract digest.
	 */
	public function current( ?object $request = null ): string|WP_Error {
		if ( null !== $request && isset( $this->requests[ $request ] ) ) {
			return $this->requests[ $request ];
		}
		$value  = null !== $this->read ? ( $this->read )() : $this->lookup();
		$result = is_string( $value ) && 1 === preg_match( '/\A[a-f0-9]{64}\z/', $value ) ? $value : self::failure();
		if ( null !== $request ) {
			$this->requests[ $request ] = $result;
		}
		return $result;
	}

	/** Native WordPress HTTP default timeout; no paid/model/compute call here. */
	private function lookup(): string|WP_Error {
		$base  = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' );
		$token = defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ? (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ) : '';
		if ( '' === $base || '' === $token ) {
			return self::failure();
		}
		$reply = wp_remote_get( $base . '/resource/version', array( 'headers' => array( 'X-Linker-Service-Token' => $token ) ) );
		if ( is_wp_error( $reply ) || 200 !== (int) wp_remote_retrieve_response_code( $reply ) ) {
			return self::failure();
		}
		$body = json_decode( (string) wp_remote_retrieve_body( $reply ), true );
		return is_array( $body ) && is_string( $body['version'] ?? null ) ? $body['version'] : self::failure();
	}

	/** Safe existing error surface; no private URL or data appears in the message. */
	private static function failure(): WP_Error {
		return new WP_Error( 'linker_engine_version', __( 'Your request could not be completed. Your input is still here. Please try again.', 'linker-tools' ), array( 'status' => 503 ) );
	}
}
