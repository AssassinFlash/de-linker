<?php
/**
 * Tests for the VIES check, with answers recorded from VIES.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\VatNumber;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Tests for ViesClient. The fixtures in tests/php/Fixtures/vies are answers of the
 * VIES REST API (POST check-vat-number), recorded via Apify on 2026-10-09.
 *
 * @covers \Linker\Commerce\Registration\ViesClient
 */
final class ViesClientTest extends TestCase {

	/**
	 * Body and status handling as WordPress's HTTP API does it.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_body', array( 'return' => static fn ( array $response ): string => $response['body'] ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => static fn ( array $response ): int => $response['response']['code'] ) );
	}

	/**
	 * VIES answers with a recorded fixture for the request it receives.
	 *
	 * @param string $fixture Fixture file name.
	 * @param string $country Country code expected in the request.
	 * @param string $number  Number expected in the request.
	 */
	private function vies_answers( string $fixture, string $country, string $number ): void {
		$recorded = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/Fixtures/vies/' . $fixture ), true );
		WP_Mock::userFunction(
			'wp_remote_post',
			array(
				'times'  => 1,
				'args'   => array(
					ViesClient::ENDPOINT,
					\Mockery::on(
						static fn ( array $args ): bool => json_decode( $args['body'], true ) === array(
							'countryCode' => $country,
							'vatNumber'   => $number,
						)
					),
				),
				'return' => array(
					'body'     => json_encode( $recorded['body'] ),
					'response' => array( 'code' => $recorded['status'] ),
				),
			)
		);
	}

	/**
	 * A number VIES confirms is valid.
	 */
	public function test_valid(): void {
		$this->vies_answers( 'valid-DE143454214.json', 'DE', '143454214' );

		$this->assertSame(
			array(
				'status' => VatProfile::VALID,
				'detail' => '',
			),
			( new ViesClient() )->check( new VatNumber( 'DE', '143454214' ) )
		);
	}

	/**
	 * A number VIES does not know is invalid.
	 */
	public function test_invalid(): void {
		$this->vies_answers( 'invalid-DE000000000.json', 'DE', '000000000' );

		$this->assertSame(
			array(
				'status' => VatProfile::INVALID,
				'detail' => '',
			),
			( new ViesClient() )->check( new VatNumber( 'DE', '000000000' ) )
		);
	}

	/**
	 * INVALID_INPUT ("the provided CountryCode is invalid or the VAT number is empty") is invalid.
	 */
	public function test_invalid_input(): void {
		$this->vies_answers( 'invalid-input-XX123.json', 'XX', '123' );

		$this->assertSame(
			array(
				'status' => VatProfile::INVALID,
				'detail' => 'INVALID_INPUT',
			),
			( new ViesClient() )->check( new VatNumber( 'XX', '123' ) )
		);
	}

	/**
	 * When VIES or the member state cannot answer, the number is not checked, never invalid.
	 */
	public function test_unavailable(): void {
		WP_Mock::userFunction(
			'wp_remote_post',
			array(
				'return_in_order' => array(
					array(
						'body'     => '{"actionSucceed":false,"errorWrappers":[{"error":"MS_UNAVAILABLE"}]}',
						'response' => array( 'code' => 200 ),
					),
					new WP_Error( 'http_request_failed', 'cURL error 28: Operation timed out' ),
					array(
						'body'     => '<html>Bad gateway</html>',
						'response' => array( 'code' => 502 ),
					),
				),
			)
		);
		$client = new ViesClient();
		$vat    = new VatNumber( 'DE', '143454214' );

		$this->assertSame(
			array(
				'status' => VatProfile::UNVERIFIED,
				'detail' => 'MS_UNAVAILABLE',
			),
			$client->check( $vat )
		);
		$this->assertSame(
			array(
				'status' => VatProfile::UNVERIFIED,
				'detail' => 'cURL error 28: Operation timed out',
			),
			$client->check( $vat )
		);
		$this->assertSame(
			array(
				'status' => VatProfile::UNVERIFIED,
				'detail' => 'HTTP 502',
			),
			$client->check( $vat )
		);
	}
}
