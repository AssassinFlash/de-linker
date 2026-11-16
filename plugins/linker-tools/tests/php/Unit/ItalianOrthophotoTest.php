<?php
/**
 * Unit tests for the Italian national 50 cm orthophoto HTTPS tile relay.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Imagery\ItalianOrthophoto;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Verifies EPSG:3857 bounding-box validation and binary JPEG verification.
 *
 * @covers \Linker\Tools\Imagery\ItalianOrthophoto
 */
final class ItalianOrthophotoTest extends TestCase {

	/**
	 * A JPEG that declares a full 256x256 frame and carries a photographic
	 * payload, so it stands for the bytes the upstream service really sends.
	 *
	 * @param int $width  Declared frame width.
	 * @param int $height Declared frame height.
	 * @param int $bytes  Total length, which must exceed the blank-tile floor.
	 * @return string JPEG bytes.
	 */
	private static function jpeg( int $width = 256, int $height = 256, int $bytes = 24000 ): string {
		$app0   = "\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00";
		$sof0   = "\xff\xc0\x00\x11\x08"
			. chr( ( $height >> 8 ) & 0xFF ) . chr( $height & 0xFF )
			. chr( ( $width >> 8 ) & 0xFF ) . chr( $width & 0xFF )
			. "\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01";
		$head   = "\xff\xd8" . $app0 . $sof0;
		$tail   = "\xff\xd9";
		$filler = str_repeat( "\x5a", max( 0, $bytes - strlen( $head ) - strlen( $tail ) ) );
		return $head . $filler . $tail;
	}

	/**
	 * Valid Milan EPSG:3857 bounding boxes normalise cleanly; foreign or inverted boxes are refused.
	 */
	public function test_normalise_bbox_accepts_italy_and_refuses_invalid_envelopes(): void {
		$this->assertSame(
			'1022900.000,5694800.000,1023200.000,5695100.000',
			ItalianOrthophoto::normalise_bbox( '1022900,5694800,1023200,5695100' )
		);
		$this->assertNull( ItalianOrthophoto::normalise_bbox( '1023200,5694800,1022900,5695100' ) );
		$this->assertNull( ItalianOrthophoto::normalise_bbox( '-14900,6710400,-14600,6710700' ) );
		$this->assertNull( ItalianOrthophoto::normalise_bbox( '1000000,5000000,1500000,5500000' ) );
		$this->assertNull( ItalianOrthophoto::normalise_bbox( 'http://attacker.invalid' ) );
	}

	/**
	 * A verified upstream JPEG returns 200 with immutable public caching and nosniff.
	 */
	public function test_tile_relays_verified_jpeg_and_refuses_non_jpeg_payloads(): void {
		$jpeg = self::jpeg();
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing(
			static fn( mixed $value ): bool => $value instanceof WP_Error
		);
		WP_Mock::userFunction(
			'wp_remote_retrieve_response_code',
			array(
				'return' => static fn( array $reply ): int => (int) $reply['code'],
			)
		);
		WP_Mock::userFunction(
			'wp_remote_retrieve_header',
			array(
				'return' => static fn( array $reply ): string => (string) $reply['type'],
			)
		);
		WP_Mock::userFunction(
			'wp_remote_retrieve_body',
			array(
				'return' => static fn( array $reply ): string => (string) $reply['body'],
			)
		);

		$captured_url = '';
		$relay        = new ItalianOrthophoto(
			static function ( string $url ) use ( $jpeg, &$captured_url ): array {
				$captured_url = $url;
				return array(
					'code' => 200,
					'type' => 'image/jpeg',
					'body' => $jpeg,
				);
			}
		);

		/**
		 * Mocked REST request carrying Milan's bounding box.
		 *
		 * @var WP_REST_Request&\Mockery\MockInterface $request
		 */
		$request = \Mockery::mock( WP_REST_Request::class );
		$request->shouldReceive( 'get_param' )->with( 'bbox' )->andReturn( '1022900,5694800,1023200,5695100' );
		$request->shouldReceive( 'get_route' )->andReturn( '/linker/v1/imagery/it' );

		$response = $relay->tile( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( 'image/jpeg', $response->get_headers()['Content-Type'] );
		$this->assertSame( 'nosniff', $response->get_headers()['X-Content-Type-Options'] );
		$this->assertStringStartsWith( ItalianOrthophoto::UPSTREAM . '?bbox=1022900.000%2C5694800.000%2C1023200.000%2C5695100.000', $captured_url );

		ob_start();
		$served  = $relay->serve( false, $response, $request, null );
		$emitted = (string) ob_get_clean();
		$this->assertTrue( $served );
		$this->assertSame( $jpeg, $emitted );

		$broken  = new ItalianOrthophoto(
			static fn(): array => array(
				'code' => 200,
				'type' => 'text/html',
				'body' => '<html>error</html>',
			)
		);
		$refusal = $broken->tile( $request );
		$this->assertInstanceOf( WP_Error::class, $refusal );
		$this->assertSame( 'linker_imagery_invalid_reply', $refusal->get_error_code() );
	}

	/**
	 * A blank tile is refused rather than cached for a week.
	 *
	 * Measured 2026-11-16: the Italian service answers Rome at one zoom level
	 * with a valid but empty 256x256 JPEG of 1,651 bytes. Relaying it would put
	 * a white square on the map and, with `immutable` caching, keep it there.
	 */
	public function test_a_blank_upstream_tile_is_refused_instead_of_cached(): void {
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing(
			static fn( mixed $value ): bool => $value instanceof WP_Error
		);
		WP_Mock::userFunction(
			'wp_remote_retrieve_response_code',
			array( 'return' => static fn( array $reply ): int => 200 ) // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.Found -- the mock stands in for the WordPress reader.
		);
		WP_Mock::userFunction(
			'wp_remote_retrieve_header',
			array( 'return' => static fn( array $reply ): string => 'image/jpeg' ) // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.Found -- the mock stands in for the WordPress reader.
		);
		WP_Mock::userFunction(
			'wp_remote_retrieve_body',
			array( 'return' => static fn( array $reply ): string => (string) $reply['body'] )
		);

		$blank = self::jpeg( 256, 256, 1651 );
		$relay = new ItalianOrthophoto( static fn(): array => array( 'body' => $blank ) );

		/**
		 * The same request the screen sends for Rome.
		 *
		 * @var WP_REST_Request&\Mockery\MockInterface $rome
		 */
		$rome = \Mockery::mock( WP_REST_Request::class );
		$rome->shouldReceive( 'get_param' )->with( 'bbox' )->andReturn( '1390548.85,5144469.65,1390701.75,5144622.55' );
		$rome->shouldReceive( 'get_route' )->andReturn( '/linker/v1/imagery/it' );

		$answer = $relay->tile( $rome );
		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( 'linker_imagery_invalid_reply', $answer->get_error_code() );

		// A frame that is not the size the map asked for is refused too.
		$wrong = new ItalianOrthophoto(
			static fn(): array => array( 'body' => self::jpeg( 64, 64, 24000 ) )
		);
		$cut   = $wrong->tile( $rome );
		$this->assertInstanceOf( WP_Error::class, $cut );
		$this->assertSame( 'linker_imagery_invalid_reply', $cut->get_error_code() );
	}
}
