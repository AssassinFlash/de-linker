<?php
/**
 * The engine's own refusal names travel through the gateway unchanged.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Principal;
use Linker\Tools\Planner\SeriesDownload;
use Linker\Tools\Planner\Transport;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Several 409s reach this seam; only one of them is a claim conflict.
 *
 * @covers \Linker\Tools\Planner\Transport
 */
final class TransportTest extends TestCase {

	/** A configured endpoint and service token, without a live host. */
	public function setUp(): void {
		parent::setUp();
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'unit-test-only' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Existing native service constant; a synthetic unit-test value only.
		}
		WP_Mock::userFunction( '__' )->andReturnUsing( static fn ( string $text ): string => $text );
		WP_Mock::userFunction( 'get_option' )->with( 'linker_planner_url', '' )->andReturn( 'https://engine.test' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( $value ): string => (string) json_encode( $value ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- The mock stands in for the WordPress function itself.
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn ( $value ): bool => $value instanceof \WP_Error );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturnUsing( static fn ( array $reply ): int => $reply['status'] );
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturnUsing( static fn ( array $reply ): string => $reply['body'] );
		WP_Mock::userFunction( 'wp_remote_retrieve_header' )->andReturnUsing( static fn ( array $reply ): string => $reply['type'] ?? 'application/json' );
		WP_Mock::userFunction( 'wp_tempnam' )->andReturnUsing( static fn (): string => (string) tempnam( sys_get_temp_dir(), 'lps' ) );
	}

	/**
	 * Build a transport whose single reply is the given status and body.
	 *
	 * @param int    $status HTTP status the engine returns.
	 * @param string $body   Raw engine reply body.
	 */
	private function replying( int $status, string $body ): Transport {
		return new Transport(
			static fn (): array => array(
				'status' => $status,
				'body'   => $body,
				'type'   => 'application/json',
			)
		);
	}

	/**
	 * Send one command through the transport.
	 *
	 * @param Transport $transport Transport under test.
	 * @return \WP_Error|array<string,mixed>
	 */
	private function send( Transport $transport ): \WP_Error|array {
		return $transport->object(
			new Principal( 'user', 'wp:1:user:1' ),
			'projects/read',
			array(
				'schema_version' => 1,
				'project_id'     => 'abc',
				'revision'       => null,
			)
		);
	}

	/**
	 * Four engine 409s must stay distinguishable; only the lease is a claim
	 * conflict, because retrying the other three cannot succeed.
	 */
	public function test_engine_conflict_codes_survive_the_gateway(): void {
		$cases = array(
			'conflict'                    => 'linker_planner_conflict',
			'evaluation_revision_changed' => 'linker_planner_evaluation_revision_changed',
			'product_evidence_changed'    => 'linker_planner_product_evidence_changed',
			'lease_lost'                  => 'linker_planner_lease_lost',
		);
		foreach ( $cases as $engine_code => $expected ) {
			$refusal = $this->send( $this->replying( 409, (string) wp_json_encode( array( 'error' => array( 'code' => $engine_code ) ) ) ) );
			self::assertInstanceOf( \WP_Error::class, $refusal, $engine_code );
			self::assertSame( $expected, $refusal->get_error_code(), $engine_code );
			self::assertSame( 409, $refusal->get_error_data()['status'], $engine_code );
		}
	}

	/** An unreadable or unexpected body still yields the generic status code. */
	public function test_unrecognised_bodies_fall_back_per_status(): void {
		foreach ( array(
			409 => 'claim_conflict',
			404 => 'not_found',
			422 => 'input',
			503 => 'unavailable',
			500 => 'upstream',
		) as $status => $expected ) {
			$refusal = $this->send( $this->replying( $status, 'not json at all' ) );
			self::assertInstanceOf( \WP_Error::class, $refusal, (string) $status );
			self::assertSame( 'linker_planner_' . $expected, $refusal->get_error_code(), (string) $status );
		}
	}

	/** A code that is not a stable machine name is not passed through. */
	public function test_unsafe_codes_are_not_forwarded(): void {
		$refusal = $this->send( $this->replying( 409, (string) wp_json_encode( array( 'error' => array( 'code' => 'Product Evidence Changed!' ) ) ) ) );
		self::assertInstanceOf( \WP_Error::class, $refusal );
		self::assertSame( 'linker_planner_claim_conflict', $refusal->get_error_code() );
	}
	/** A series stream must be owned, purpose-bound and match the frozen hash. */
	public function test_owned_series_is_streamed_and_removed_on_refusal(): void {
		$bytes     = "interval,value\n0,1\n";
		$path      = '';
		$purpose   = 'planning_pv_series_csv_v1';
		$actual    = $bytes;
		$transport = new Transport(
			static function ( string $url, array $args ) use ( &$path, &$purpose, &$actual, $bytes ): array {
				if ( str_ends_with( $url, '/assets/read' ) ) {
					return array(
						'status' => 200,
						'type'   => 'application/json',
						'body'   => (string) wp_json_encode(
							array(
								'id'             => 'asset',
								'project_id'     => 'project',
								'purpose'        => $purpose,
								'media_type'     => 'text/csv',
								'content_sha256' => hash( 'sha256', $bytes ),
							)
						),
					);
				}
				self::assertTrue( $args['stream'] );
				self::assertSame( SeriesDownload::MAX_BYTES + 1, $args['limit_response_size'] );
				$path = $args['filename'];
				file_put_contents( $path, $actual ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- Synthetic request-owned test file.
				return array(
					'status' => 200,
					'type'   => 'application/octet-stream',
					'body'   => '',
				);
			}
		);
		$command   = array(
			'schema_version' => 1,
			'project_id'     => 'project',
			'asset_id'       => 'asset',
			'series_csv'     => true,
		);
		$owner     = new Principal( 'user', 'wp:1:user:1' );
		$result    = SeriesDownload::fetch( $owner, $command, $transport );
		self::assertInstanceOf( SeriesDownload::class, $result );
		self::assertSame( strlen( $bytes ), $result->size );
		ob_start();
		$result->output();
		self::assertSame( $bytes, ob_get_clean() );
		self::assertFileDoesNotExist( $path );
		$actual = 'changed';
		self::assertInstanceOf( \WP_Error::class, SeriesDownload::fetch( $owner, $command, $transport ) );
		self::assertFileDoesNotExist( $path );
		$purpose = 'planning_report_pdf_v1';
		self::assertInstanceOf( \WP_Error::class, SeriesDownload::fetch( $owner, $command, $transport ) );
	}
}
