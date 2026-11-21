<?php
/**
 * Cloudflare's test response at the HTTP boundary of the native Genie handoff.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

/** Isolates the provider while the real Woo and Genie handlers process a submission. */
final class GenieVerificationFixture {
	/**
	 * Configure the official public test keys and answer only their matching token.
	 *
	 * @param callable(callable():void):void $later Register test cleanup.
	 */
	public static function install( callable $later ): void {
		$secret = '1x0000000000000000000000000000000AA';
		foreach ( array(
			'LINKER_TURNSTILE_SITE_KEY'   => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY' => $secret,
			'LINKER_TURNSTILE_HOSTNAME'   => 'example.com',
		) as $key => $value ) {
			$previous = getenv( $key );
			putenv( $key . '=' . $value ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Test process only.
			$later(
				static function () use ( $previous, $key ): void {
					putenv( false === $previous ? $key : $key . '=' . $previous ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Restore test environment.
				}
			);
		}
		$siteverify = static function ( $previous, array $args, string $url ) use ( $secret ) {
			if ( 'https://challenges.cloudflare.com/turnstile/v0/siteverify' !== $url ) {
				return $previous;
			}
			$accepted = ( $args['body']['secret'] ?? null ) === $secret && 'XXXX.DUMMY.TOKEN.XXXX' === ( $args['body']['response'] ?? null );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode(
					array(
						'success'  => $accepted,
						'hostname' => 'example.com',
					)
				),
			);
		};
		add_filter( 'pre_http_request', $siteverify, 10, 3 );
		$later(
			static function () use ( $siteverify ): void {
				remove_filter( 'pre_http_request', $siteverify, 10 );
			}
		);
	}
}
