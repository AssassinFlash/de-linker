<?php
/**
 * Shared verification through the real WordPress HTTP boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\Turnstile;
use WP_Error;

/**
 * Provider fixtures exercise WordPress transport without contacting Cloudflare.
 *
 * @coversNothing
 */
final class PublicVerificationTest extends IntegrationTestCase {
	// Official public always-pass dummy keys, #506 testing documentation.
	private const SITE_KEY = '1x00000000000000000000AA';
	private const SECRET   = '1x0000000000000000000000000000000AA';

	/**
	 * Local fixture configuration never reads the saved production file.
	 *
	 * @param string $mode Explicit test mode.
	 */
	private function configuration( string $mode = 'enforce' ): Configuration {
		return new Configuration( $mode, self::SITE_KEY, self::SECRET, 'example.test' );
	}

	/** Exact hostname/action/Boolean binding, stable retry UUID and no extra data. */
	public function test_valid_verification_uses_the_canonical_private_transport(): void {
		$id   = wp_generate_uuid4();
		$seen = array();
		$http = static function ( $pre, $args, $url ) use ( &$seen ) {
			$seen = array( $args, $url );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode(
					array(
						'success'  => true,
						'hostname' => 'example.test',
						'action'   => 'inquiry',
					)
				),
			);
		};
		add_filter( 'pre_http_request', $http, 10, 3 );
		try {
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic-token', 'inquiry', $id );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 'valid', $result->status );
		$this->assertSame( 'https://challenges.cloudflare.com/turnstile/v0/siteverify', $seen[1] );
		$this->assertSame(
			array(
				'secret'          => self::SECRET,
				'response'        => 'synthetic-token',
				'idempotency_key' => $id,
			),
			$seen[0]['body']
		);
		$this->assertSame( 0, $seen[0]['redirection'] );
		$this->assertSame( 3, $seen[0]['timeout'] );
		$this->assertStringNotContainsString( self::SECRET, (string) wp_json_encode( $this->configuration() ) );
		$this->assertStringNotContainsString( 'synthetic-token', (string) wp_json_encode( $result ) );
	}

	/**
	 * Invalid values and provider outages do not collapse into a positive check.
	 *
	 * @dataProvider responses
	 * @param string $body Upstream body.
	 * @param int    $code HTTP status.
	 * @param string $status Expected category.
	 * @param string $reason Safe fixed reason.
	 */
	public function test_provider_outcomes( string $body, int $code, string $status, string $reason ): void {
		$http = static fn () => array(
			'response' => array( 'code' => $code ),
			'body'     => $body,
		);
		add_filter( 'pre_http_request', $http );
		try {
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic-token', 'inquiry', wp_generate_uuid4() );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( $status, $result->status );
		$this->assertSame( $reason, $result->reason );
	}

	/**
	 * Strict response matrix from the fixed Siteverify contract.
	 *
	 * @return array<string, array{string, int, string, string}>
	 */
	public static function responses(): array {
		return array(
			'wrong hostname'       => array( '{"success":true,"hostname":"other.test","action":"inquiry"}', 200, 'invalid', 'hostname' ),
			'wrong action'         => array( '{"success":true,"hostname":"example.test","action":"registration"}', 200, 'invalid', 'action' ),
			'truthy success'       => array( '{"success":"true","hostname":"example.test","action":"inquiry"}', 200, 'unavailable', 'response' ),
			'missing success'      => array( '{}', 200, 'unavailable', 'response' ),
			'invalid JSON'         => array( '{', 200, 'unavailable', 'response' ),
			'provider busy'        => array( '{}', 503, 'unavailable', 'http' ),
			'provider redirect'    => array( '{}', 302, 'unavailable', 'http' ),
			'expired or duplicate' => array( '{"success":false,"error-codes":["timeout-or-duplicate"]}', 200, 'invalid', 'expired_or_replayed' ),
			'invalid token'        => array( '{"success":false,"error-codes":["invalid-input-response"]}', 200, 'invalid', 'rejected' ),
			'bad private key'      => array( '{"success":false,"error-codes":["invalid-input-secret"]}', 200, 'unavailable', 'provider' ),
			'provider failure'     => array( '{"success":false,"error-codes":["internal-error"]}', 200, 'unavailable', 'provider' ),
			'unknown error shape'  => array( '{"success":false,"error-codes":[{}]}', 200, 'invalid', 'rejected' ),
		);
	}

	/** Local invalid input never spends a provider request; off is explicit. */
	public function test_invalid_input_and_disabled_configuration_do_not_call_upstream(): void {
		$calls = 0;
		$http  = static function () use ( &$calls ) {
			++$calls;
			return new WP_Error( 'must_not_call' );
		};
		add_filter( 'pre_http_request', $http );
		try {
			$client = new Turnstile( $this->configuration() );
			foreach ( array( array( '', 'inquiry', wp_generate_uuid4() ), array( str_repeat( 'x', 2049 ), 'inquiry', wp_generate_uuid4() ), array( 'synthetic', 'wrong action', wp_generate_uuid4() ), array( 'synthetic', 'inquiry', 'not-a-uuid' ) ) as $values ) {
				$this->assertSame( 'invalid', $client->verify( ...$values )->status );
			}
			$off = $this->configuration( 'off' );
			$this->assertTrue( $off->health()['configured'] );
			$this->assertFalse( $off->health()['ready'] );
			$this->assertSame( 'unavailable', ( new Turnstile( $off ) )->verify( 'synthetic', 'inquiry', wp_generate_uuid4() )->status );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 0, $calls );
	}

	/** A network error's arbitrary message cannot enter a rendered diagnostic. */
	public function test_network_error_is_a_safe_unavailable_result(): void {
		$http = static fn () => new WP_Error( 'http_request_failed', 'synthetic secret text must not be copied' );
		add_filter( 'pre_http_request', $http );
		try {
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic', 'inquiry', wp_generate_uuid4() );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 'unavailable', $result->status );
		$this->assertSame( 'network', $result->reason );
		$this->assertStringNotContainsString( 'synthetic secret', (string) wp_json_encode( $result ) );
	}
}
