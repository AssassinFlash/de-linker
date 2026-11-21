<?php
/**
 * The engine's own refusal names travel through the gateway unchanged.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Admission;
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

	/** Delete coordination evidence belongs to the native gateway alone. */
	public function test_browser_cannot_supply_delete_authorization(): void {
		$transport = new Transport( static fn (): never => self::fail( 'Browser-supplied evidence reached private RPC.' ) );
		foreach ( array(
			'inquiry_generation'   => 0,
			'prepared_handoff_ids' => array(),
		) as $field => $value ) {
			$command = array(
				'schema_version' => 1,
				$field           => $value,
			);
			$result  = ( new Admission() )->send( new Principal( 'user', 'wp:1:user:17' ), 'projects/delete', $command, (string) wp_json_encode( $command ), $transport );
			self::assertInstanceOf( \WP_Error::class, $result );
			self::assertSame( 422, $result->get_error_data()['status'] );
		}
	}

	/** A signed-in project edit uses the engine's owned, idempotent revision command. */
	public function test_account_edit_preserves_native_project_revision_command(): void {
		$principal = new Principal( 'user', 'wp:1:user:17' );
		$command   = array(
			'key'               => 'ae4899d0-07b7-4f82-abc1-0b532f04be92',
			'project_id'        => str_repeat( 'a', 32 ),
			'expected_revision' => 3,
		);
		$body      = (string) wp_json_encode( $command );
		$transport = new Transport(
			function ( string $url, array $args ) use ( $principal, $body ): array {
				$this->assertSame( 'https://engine.test/projects/revise', $url );
				$this->assertSame( $principal->subject, $args['headers']['X-Linker-Planner-Principal-Subject'] );
				$this->assertSame( $body, $args['body'] );
				return array(
					'status' => 200,
					'type'   => 'application/json',
					'body'   => '{"revision":4}',
				);
			}
		);
		$result    = ( new Admission() )->send( $principal, 'projects/revise', $command, $body, $transport );
		$this->assertIsArray( $result );
		$this->assertSame( '{"revision":4}', $result['body'] );
	}

	/** The verified project owner sends each command to its private handler with its original key. */
	public function test_guest_workspace_commands_use_the_owned_engine_request(): void {
		$owner   = new Principal( 'guest', 'synthetic-guest' );
		$command = array( 'key' => 'be0e47ad-800d-49bd-bc38-a0efce1eff92' );
		$body    = (string) wp_json_encode( $command );
		foreach ( array( 'projects/create', 'projects/revise', 'profiles/csv', 'profiles/standard', 'geometry/import', 'runs/calculate', 'runs/report' ) as $path ) {
			$transport = new Transport(
				function ( string $url, array $args ) use ( $owner, $body, $path ): array {
					$this->assertSame( 'https://engine.test/' . $path, $url );
					$this->assertSame( $owner->subject, $args['headers']['X-Linker-Planner-Principal-Subject'] );
					$this->assertSame( $body, $args['body'] );
					return array(
						'status' => 200,
						'body'   => '{"schema_version":1}',
					);
				}
			);
			$result    = ( new Admission() )->send( $owner, $path, $command, $body, $transport );
			$this->assertIsArray( $result );
			$this->assertSame( 200, $result['status'] );
		}
	}

	/** The private profile handler's rejection reaches the customer unchanged. */
	public function test_standard_profile_preserves_private_validation_errors(): void {
		$body  = '{"error":{"code":"invalid_input"}}';
		$reply = ( new Admission() )->send( new Principal( 'user', 'wp:1:user:1' ), 'profiles/standard', array(), '{}', $this->replying( 422, $body ) );
		$this->assertIsArray( $reply );
		$this->assertSame( 422, $reply['status'] );
		$this->assertSame( $body, $reply['body'] );
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

	/** Loading a saved project and its history uses the workspace read budget. */
	public function test_workspace_reads_use_the_extended_request_budget(): void {
		$owner     = new Principal( 'guest', 'test-guest' );
		$budgets   = array();
		$transport = new Transport(
			static function ( string $url, array $args ) use ( &$budgets ): array {
				$budgets[] = $args['timeout'];
				return array(
					'status' => 200,
					'body'   => '{}',
				);
			}
		);
		foreach ( array( 'projects/list', 'projects/read', 'projects/runs' ) as $route ) {
			$transport->call( $owner, $route, '{}' );
		}
		self::assertSame( array( 30.0, 30.0, 30.0 ), $budgets );
	}

	/** Omitted optional pagination and revision fields are filled before engine dispatch. */
	public function test_omitted_optional_command_fields_receive_gateway_defaults(): void {
		$sent      = array();
		$transport = new Transport(
			static function ( string $url, array $args ) use ( &$sent ): array {
				$sent[ $url ] = json_decode( $args['body'], true );
				return array(
					'status' => 200,
					'type'   => 'application/json',
					'body'   => '{"ok":true}',
				);
			}
		);
		$owner     = new Principal( 'user', 'wp:1:user:1' );
		self::assertSame(
			array( 'ok' => true ),
			$transport->object( $owner, 'projects/list', array( 'schema_version' => 1 ) )
		);
		self::assertSame(
			array( 'ok' => true ),
			$transport->object(
				$owner,
				'projects/read',
				array(
					'schema_version' => 1,
					'project_id'     => 'proj_1',
				)
			)
		);
		self::assertSame(
			array( 'ok' => true ),
			$transport->object(
				$owner,
				'projects/runs',
				array(
					'schema_version' => 1,
					'project_id'     => 'proj_1',
				)
			)
		);
		self::assertSame(
			array(
				'schema_version' => 1,
				'page_size'      => 10,
				'after'          => null,
			),
			$sent['https://engine.test/projects/list']
		);
		self::assertSame(
			array(
				'schema_version' => 1,
				'project_id'     => 'proj_1',
				'revision'       => null,
			),
			$sent['https://engine.test/projects/read']
		);
		self::assertSame(
			array(
				'schema_version'    => 1,
				'project_id'        => 'proj_1',
				'page_size'         => 20,
				'before_created_at' => null,
				'before_id'         => null,
			),
			$sent['https://engine.test/projects/runs']
		);
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
				self::assertSame( 0600, fileperms( $path ) & 0777 );
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
