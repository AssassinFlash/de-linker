<?php
/**
 * `publication ack-engineering`: the engine readback, never a receipt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\PublicationCommand;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\EngineLoadedState;
use Linker\Commerce\Products\Publication\PreparationJobs;
use Mockery;
use WP_CLI\ExitException;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * A pulled instance's receipts name a generation that no longer exists; the
 * engine's own authenticated readback is the only evidence of the one it
 * loaded, so these cases drive the command over that readback.
 *
 * @covers \Linker\Commerce\Cli\PublicationCommand
 * @covers \Linker\Commerce\Products\Publication\EngineLoadedState
 */
final class PublicationCommandAckTest extends TestCase {
	use \Linker\Commerce\Tests\Support\CurrentFaqProduct;

	/**
	 * The in-memory queue option.
	 *
	 * @var array<string,mixed>
	 */
	private array $state = array();

	/**
	 * The engine's answer to the next readback request.
	 *
	 * @var array<string,mixed>|WP_Error|null
	 */
	private array|WP_Error|null $answer = null;

	/**
	 * The readback requests, as [url, token].
	 *
	 * @var list<array{url:string,token:string}>
	 */
	private array $requests = array();

	/**
	 * Previous global database object, restored after each case.
	 *
	 * @var mixed
	 */
	private mixed $previous_database;

	/**
	 * One published product, a queue option store and a stubbed engine.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->current_faq_product( 12, array() );
		$this->previous_database = $GLOBALS['wpdb'] ?? null;
		$database                = Mockery::mock( \wpdb::class );
		$database->prefix        = 'wp_';
		$database->shouldReceive( 'prepare' )->andReturn( 'fixture lock' );
		$database->shouldReceive( 'get_var' )->andReturn( '1' );
		$GLOBALS['wpdb'] = $database;
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnUsing( static fn ( string $value ): string => $value )->byDefault();
		// WordPress's own wrapper; the unit tests run without WordPress.
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( static fn ( string $url, int $component = -1 ): mixed => parse_url( $url, $component ) )->byDefault();
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'fixture-lease' )->byDefault();
		WP_Mock::userFunction( 'delete_option' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'get_option' )->andReturnUsing( fn ( string $key ): mixed => PreparationJobs::OPTION === $key ? $this->state : false )->byDefault();
		WP_Mock::userFunction( 'update_option' )->andReturnUsing(
			function ( string $key, mixed $value ): bool {
				if ( PreparationJobs::OPTION === $key ) {
					$this->state = is_array( $value ) ? $value : array();
				}
				return true;
			}
		)->byDefault();
		WP_Mock::userFunction(
			'wp_remote_get',
			array(
				'return' => function ( string $url, array $args = array() ): array|WP_Error {
					$this->requests[] = array(
						'url'   => $url,
						'token' => (string) ( $args['headers']['x-linker-service-token'] ?? '' ),
					);
					if ( $this->answer instanceof WP_Error ) {
						return $this->answer;
					}
					return array(
						'response' => array( 'code' => 200 ),
						'body'     => (string) wp_json_encode( $this->answer ),
					);
				},
			)
		)->byDefault();
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => static fn ( array $response ): int => (int) ( $response['response']['code'] ?? 0 ) ) )->byDefault();
		WP_Mock::userFunction( 'wp_remote_retrieve_body', array( 'return' => static fn ( array $response ): string => (string) ( $response['body'] ?? '' ) ) )->byDefault();
		// The operator override of the instance's own service token; WP_Mock
		// refuses to stand in for an internal PHP function.
		putenv( EngineLoadedState::ENVIRONMENT_TOKEN . '=fixture-service-token' ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- The unit test supplies a process environment the CLI reads.
	}

	/** Keep queue and upload fixture effects local to this case. */
	public function tearDown(): void {
		putenv( EngineLoadedState::ENVIRONMENT_TOKEN ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Undo the test's own environment override.
		$GLOBALS['wpdb'] = $this->previous_database;
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** A complete engine readback acknowledges every current product revision. */
	public function test_complete_readback_acknowledges_every_current_product(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, $manifest['source_revision'] );
		$this->state  = array(
			'engineering' => array(
				'job_id'           => 'stale-job',
				'source_revision'  => $manifest['source_revision'],
				'status'           => 'pending',
				'loaded_products'  => array( 12 => str_repeat( 'e', 64 ) ),
				'lease_expires_at' => 0,
			),
		);
		$this->assertSame( 0, $this->ready( $manifest ) );

		ob_start();
		( new PublicationCommand() )->ack_engineering( array(), array( 'engine' => 'http://127.0.0.1:8890/' ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'wp-cli success:', $output );
		$this->assertSame( 1, $this->ready( $manifest ) );
		$this->assertSame( 'ready', $this->state['engineering']['status'] );
		$this->assertSame(
			array(
				array(
					'url'   => 'http://127.0.0.1:8890/resource/version?ready=1',
					'token' => 'fixture-service-token',
				),
			),
			$this->requests
		);
	}

	/** An engine that loaded another source is refused before any claim. */
	public function test_engine_source_mismatch_is_refused_without_acknowledging(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, str_repeat( '9', 64 ) );

		ob_start();
		$failure = null;
		try {
			( new PublicationCommand() )->ack_engineering( array(), array( 'engine' => 'http://127.0.0.1:8890' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}
		$output = (string) ob_get_clean();

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'engine_source_mismatch', $failure->getMessage() );
		$this->assertStringContainsString( '"stale"', $output );
		$this->assertSame( 0, $this->ready( $manifest ) );
		$this->assertSame( array(), $this->state );
	}

	/** An engine that does not answer is a failure, never an assumed success. */
	public function test_unreachable_engine_fails_without_writing_the_queue(): void {
		$this->answer = new WP_Error( 'http_request_failed', 'cURL error 7: Connection refused' );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_engineering( array(), array( 'engine' => 'http://127.0.0.1:8890' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'engine_unreachable', $failure->getMessage() );
		$this->assertStringContainsString( 'Connection refused', $failure->getMessage() );
		$this->assertSame( array(), $this->state );
	}

	/** A readback that is not a loaded generation cannot grant readiness. */
	public function test_a_body_that_is_not_a_loaded_generation_is_refused(): void {
		$manifest = Publication::manifest();
		$current  = array(
			'product_id'       => 12,
			'product_revision' => $manifest['products'][0]['product_revision'],
		);
		foreach ( array(
			array(
				'version'         => 'v1',
				'source_revision' => $manifest['source_revision'],
			),
			array(
				'version'                => 'v1',
				'source_revision'        => 'not-a-hash',
				'compatibility_revision' => $manifest['compatibility_revision'],
				'prepared_products'      => array( $current ),
			),
			array(
				'version'                => 'v1',
				'source_revision'        => $manifest['source_revision'],
				'compatibility_revision' => $manifest['compatibility_revision'],
				'prepared_products'      => array( $current, $current ),
			),
		) as $answer ) {
			$this->answer = $answer;
			$failure      = null;
			try {
				( new PublicationCommand() )->ack_engineering( array(), array( 'engine' => 'http://127.0.0.1:8890' ) );
			} catch ( ExitException $error ) {
				$failure = $error;
			}
			$this->assertInstanceOf( ExitException::class, $failure );
			$this->assertStringContainsString( 'invalid_engine_state', $failure->getMessage() );
			$this->assertSame( 0, $this->ready( $manifest ) );
		}
	}

	/** Knowledge readiness needs a recipe-aware generation; the command says so. */
	public function test_knowledge_consumer_is_explicitly_unsupported(): void {
		$this->answer = new WP_Error( 'must_not_be_read', 'unreachable' );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_engineering(
				array(),
				array(
					'engine'   => 'http://127.0.0.1:8890',
					'consumer' => 'knowledge',
				)
			);
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'unsupported_consumer', $failure->getMessage() );
		$this->assertStringContainsString( 'recipe-aware', $failure->getMessage() );
		$this->assertSame( array(), $this->requests );
		$this->assertSame( array(), $this->state );
	}

	/** A source already acknowledged reports readiness instead of failing. */
	public function test_already_ready_source_reports_readiness(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, $manifest['source_revision'] );
		$this->state  = array(
			'engineering' => array(
				'job_id'           => 'ready-job',
				'source_revision'  => $manifest['source_revision'],
				'status'           => 'ready',
				'loaded_products'  => array( 12 => $manifest['products'][0]['product_revision'] ),
				'lease_expires_at' => 0,
			),
		);

		ob_start();
		( new PublicationCommand() )->ack_engineering( array(), array( 'engine' => 'http://127.0.0.1:8890' ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'wp-cli success:', $output );
		$this->assertStringContainsString( '1 of 1 products ready', $output );
		$this->assertSame( 'ready-job', $this->state['engineering']['job_id'] );
	}

	/**
	 * The engine readback for one source: exactly the manifest's products.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 * @param string              $source   The loaded source revision.
	 * @return array<string,mixed>
	 */
	private function loaded( array $manifest, string $source ): array {
		return array(
			'version'                => 'fixture-engine-1',
			'source_revision'        => $source,
			'compatibility_revision' => $manifest['compatibility_revision'],
			'prepared_products'      => array_values(
				array_map(
					static fn ( array $product ): array => array(
						'product_id'       => (int) $product['product_id'],
						'product_revision' => (string) $product['product_revision'],
					),
					$manifest['products']
				)
			),
		);
	}

	/**
	 * Products whose engineering receipt matches the current source.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 */
	private function ready( array $manifest ): int {
		$ready = 0;
		foreach ( $manifest['products'] as $product ) {
			if ( PreparationJobs::readiness( (int) $product['product_id'], (string) $product['product_revision'] )['engineering'] ) {
				++$ready;
			}
		}
		return $ready;
	}
}
