<?php
/**
 * `publication ack-knowledge`: Genie's own open index, never a receipt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\PublicationCommand;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\GenieLoadedState;
use Linker\Commerce\Products\Publication\PreparationJobs;
use Mockery;
use WP_CLI\ExitException;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Knowledge readiness is recipe-aware; only the serving process's own readback
 * names the compiler, the index generation and the serving rules it runs, so
 * these cases drive the command over that readback.
 *
 * @covers \Linker\Commerce\Cli\PublicationCommand
 * @covers \Linker\Commerce\Products\Publication\GenieLoadedState
 */
final class PublicationCommandKnowledgeAckTest extends TestCase {
	use \Linker\Commerce\Tests\Support\CurrentFaqProduct;

	/**
	 * The in-memory queue option.
	 *
	 * @var array<string,mixed>
	 */
	private array $state = array();

	/**
	 * Genie's answer to the next readback request.
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
	 * One published product, a queue option store and a stubbed Genie.
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
			'wp_remote_post',
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
		putenv( GenieLoadedState::ENVIRONMENT_TOKEN . '=fixture-service-token' ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- The unit test supplies a process environment the CLI reads.
	}

	/** Keep queue and upload fixture effects local to this case. */
	public function tearDown(): void {
		putenv( GenieLoadedState::ENVIRONMENT_TOKEN ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Undo the test's own environment override.
		$GLOBALS['wpdb'] = $this->previous_database;
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** Genie's complete readback acknowledges the recipe-aware generation. */
	public function test_complete_readback_acknowledges_the_recipe_aware_generation(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded(
			$manifest,
			array(
				'preparation_complete' => true,
				'unprepared_documents' => array(),
			)
		);
		$this->state  = array(
			'knowledge' => array(
				'job_id'                  => 'stale-job',
				'source_revision'         => $manifest['source_revision'],
				'status'                  => 'pending',
				'loaded_products'         => array( 12 => str_repeat( 'e', 64 ) ),
				'lease_expires_at'        => 0,
				'model_identity_revision' => $manifest['model_identity_revision'],
			),
		);

		ob_start();
		( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891/' ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'wp-cli success:', $output );
		$this->assertSame( 'ready', $this->state['knowledge']['status'] );
		$this->assertSame( 'fixture-index-1', $this->state['knowledge']['index_version'] );
		$this->assertSame( str_repeat( 'a', 64 ), $this->state['knowledge']['recipe_revision'] );
		$this->assertSame( 1, $this->knowledge_ready( $manifest ) );
		$this->assertSame(
			array(
				array(
					'url'   => 'http://127.0.0.1:8891/knowledge/loaded',
					'token' => 'fixture-service-token',
				),
			),
			$this->requests
		);
	}

	/** An index built from another source is refused before any claim. */
	public function test_source_mismatch_is_refused_without_acknowledging(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, array( 'source_revision' => str_repeat( '9', 64 ) ) );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'genie_source_mismatch', $failure->getMessage() );
		$this->assertSame( 0, $this->knowledge_ready( $manifest ) );
		$this->assertSame( array(), $this->state );
	}

	/** An index of another model identity is refused before any claim. */
	public function test_identity_mismatch_is_refused_without_acknowledging(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, array( 'model_identity_revision' => str_repeat( '8', 64 ) ) );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'genie_identity_mismatch', $failure->getMessage() );
		$this->assertSame( array(), $this->state );
	}

	/** An index carrying other product revisions cannot grant readiness. */
	public function test_stale_product_revisions_are_refused(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, array( 'product_revision' => str_repeat( '7', 64 ) ) );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'genie_products_stale', $failure->getMessage() );
		$this->assertSame( array(), $this->state );
	}

	/** An index built for other serving rules is refused with its own reason. */
	public function test_serving_revision_mismatch_is_refused(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded( $manifest, array( 'serving_revision' => str_repeat( '6', 64 ) ) );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'invalid_genie_state', $failure->getMessage() );
		$this->assertStringContainsString( 'serving rules', $failure->getMessage() );
		$this->assertSame( array(), $this->state );
	}

	/** Genie that does not answer is a failure, never an assumed success. */
	public function test_unreachable_genie_fails_without_writing_the_queue(): void {
		$this->answer = new WP_Error( 'http_request_failed', 'cURL error 7: Connection refused' );

		$failure = null;
		try {
			( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		} catch ( ExitException $error ) {
			$failure = $error;
		}

		$this->assertInstanceOf( ExitException::class, $failure );
		$this->assertStringContainsString( 'genie_unreachable', $failure->getMessage() );
		$this->assertSame( array(), $this->state );
	}

	/** Table-level diagnostics settle the generation without blocking readiness. */
	public function test_table_diagnostics_settle_readiness_with_honest_preparation(): void {
		$manifest     = Publication::manifest();
		$document     = $manifest['documents'][0];
		$this->answer = $this->loaded(
			$manifest,
			array(
				'preparation_complete' => false,
				'unprepared_documents' => array(
					array(
						'document_id' => (string) $document['document_id'],
						'product_id'  => (int) $document['product_ids'][0],
						'reason'      => 'table_without_scope',
					),
				),
			)
		);

		ob_start();
		( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'wp-cli success:', $output );
		$this->assertSame( 'ready', $this->state['knowledge']['status'] );
		$this->assertFalse( $this->state['knowledge']['preparation_complete'] );
		$this->assertSame( 'table_without_scope', $this->state['knowledge']['unprepared_documents'][0]['reason'] );
		$this->assertSame( 'Some current document associations still lack proven passages.', $this->state['knowledge']['error'] );
	}

	/** An already acknowledged generation reports instead of claiming again. */
	public function test_a_ready_receipt_for_the_same_generation_is_idempotent(): void {
		$manifest     = Publication::manifest();
		$this->answer = $this->loaded(
			$manifest,
			array(
				'preparation_complete' => true,
				'unprepared_documents' => array(),
			)
		);
		$this->state  = array(
			'knowledge' => array(
				'job_id'                         => 'ready-job',
				'source_revision'                => $manifest['source_revision'],
				'status'                         => 'ready',
				'loaded_products'                => array( 12 => $manifest['products'][0]['product_revision'] ),
				'lease_expires_at'               => 0,
				'model_identity_revision'        => $manifest['model_identity_revision'],
				'loaded_model_identity_revision' => $manifest['model_identity_revision'],
				'loaded_revision'                => $manifest['source_revision'],
				'loaded_recipe_revision'         => str_repeat( 'a', 64 ),
				'index_version'                  => 'fixture-index-1',
				'serving_revision'               => str_repeat( 'b', 64 ),
			),
		);

		ob_start();
		( new PublicationCommand() )->ack_knowledge( array(), array( 'genie' => 'http://127.0.0.1:8891' ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'wp-cli success:', $output );
		$this->assertStringContainsString( 'already acknowledged', $output );
		$this->assertSame( 'ready-job', $this->state['knowledge']['job_id'] );
	}

	/**
	 * Genie's readback for one source: exactly the manifest's knowledge products.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 * @param array<string,mixed> $overrides Fields this case changes.
	 * @return array<string,mixed>
	 */
	private function loaded( array $manifest, array $overrides ): array {
		$identity = str_repeat( 'b', 64 );
		$products = array();
		foreach ( $manifest['products'] as $product ) {
			if ( in_array( $product['engineering_role'] ?? '', \Linker\Commerce\Products\EngineeringReference::ROLES, true ) ) {
				continue;
			}
			$products[] = array(
				'product_id'       => (int) $product['product_id'],
				'product_revision' => (string) $product['product_revision'],
			);
		}
		if ( isset( $overrides['product_revision'] ) ) {
			$products = array_map(
				static fn ( array $product ): array => array(
					'product_id'       => $product['product_id'],
					'product_revision' => (string) $overrides['product_revision'],
				),
				$products
			);
			unset( $overrides['product_revision'] );
		}
		return array_merge(
			array(
				'index_version'             => 'fixture-index-1',
				'source_revision'           => $manifest['source_revision'],
				'model_identity_revision'   => $manifest['model_identity_revision'],
				'recipe_revision'           => str_repeat( 'a', 64 ),
				'expected_serving_revision' => $identity,
				'serving_revision'          => $identity,
				'activation_epoch'          => 99,
				'products'                  => $products,
				'materialization_complete'  => true,
				'preparation_complete'      => true,
				'unprepared_documents'      => array(),
			),
			$overrides
		);
	}

	/**
	 * Products whose knowledge receipt matches the current source and identity.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 */
	private function knowledge_ready( array $manifest ): int {
		$ready = 0;
		foreach ( $manifest['products'] as $product ) {
			if ( PreparationJobs::readiness( (int) $product['product_id'], (string) $product['product_revision'], (string) $manifest['model_identity_revision'] )['knowledge'] ) {
				++$ready;
			}
		}
		return $ready;
	}
}
