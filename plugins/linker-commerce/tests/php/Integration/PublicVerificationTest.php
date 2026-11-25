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
	 */
	private function configuration(): Configuration {
		return new Configuration( 'enforce', self::SITE_KEY, self::SECRET, 'example.test' );
	}

	/** Exact hostname/action/Boolean binding, one provider request and no extra data. */
	public function test_valid_verification_uses_the_canonical_private_transport(): void {
		$calls = 0;
		$seen  = array();
		$http  = static function ( $pre, $args, $url ) use ( &$seen, &$calls ) {
			++$calls;
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
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic-token', 'inquiry' );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 'valid', $result->status );
		$this->assertSame( 1, $calls );
		$this->assertSame( 'https://challenges.cloudflare.com/turnstile/v0/siteverify', $seen[1] );
		$this->assertSame(
			array(
				'secret'   => self::SECRET,
				'response' => 'synthetic-token',
			),
			$seen[0]['body']
		);
		$this->assertSame( 0, $seen[0]['redirection'] );
		// The provider timeout exceeds the measured 2.45–3.47 second round trip.
		$this->assertSame( 12, $seen[0]['timeout'] );
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
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic-token', 'inquiry' );
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

	/** Missing credentials and invalid native actions never call the provider. */
	public function test_invalid_input_and_missing_configuration_do_not_call_upstream(): void {
		$calls = 0;
		$http  = static function () use ( &$calls ) {
			++$calls;
			return new WP_Error( 'must_not_call' );
		};
		add_filter( 'pre_http_request', $http );
		try {
			$client = new Turnstile( $this->configuration() );
			foreach ( array( array( '', 'inquiry' ), array( str_repeat( 'x', 2049 ), 'inquiry' ), array( 'synthetic', 'draft_write' ) ) as $values ) {
				$this->assertSame( 'invalid', $client->verify( ...$values )->status );
			}
			$missing = new Configuration( 'enforce', self::SITE_KEY, '', 'example.test' );
			$this->assertFalse( $missing->configured() );
			$this->assertSame( 'unavailable', ( new Turnstile( $missing ) )->verify( 'synthetic', 'inquiry' )->status );
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
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic', 'inquiry' );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 'unavailable', $result->status );
		$this->assertSame( 'network', $result->reason );
		$this->assertStringNotContainsString( 'synthetic secret', (string) wp_json_encode( $result ) );
	}

	/**
	 * Cloudflare's official testing keys report no action field; the exact
	 * local browser chain (widget → native form → Siteverify) depends on that shape.
	 */
	public function test_testing_keys_accept_the_official_testing_response_without_action(): void {
		$http = static fn () => array(
			'response' => array( 'code' => 200 ),
			'body'     => '{"success":true,"hostname":"example.test"}',
		);
		add_filter( 'pre_http_request', $http );
		try {
			$result = ( new Turnstile( $this->configuration() ) )->verify( 'synthetic-token', 'registration' );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 'valid', $result->status );
	}

	/** Real production keys still require the action to be reported and equal. */
	public function test_real_keys_reject_a_missing_action(): void {
		$real = new Configuration( 'enforce', '0x4AAAAAAAfakesitekey000000', '0x4AAAAAAAfakesecret0000000000000', 'example.test' );
		$http = static fn () => array(
			'response' => array( 'code' => 200 ),
			'body'     => '{"success":true,"hostname":"example.test"}',
		);
		add_filter( 'pre_http_request', $http );
		try {
			$result = ( new Turnstile( $real ) )->verify( 'synthetic-token', 'registration' );
		} finally {
			remove_filter( 'pre_http_request', $http );
		}
		$this->assertSame( 'invalid', $result->status );
		$this->assertSame( 'action', $result->reason );
	}
}
