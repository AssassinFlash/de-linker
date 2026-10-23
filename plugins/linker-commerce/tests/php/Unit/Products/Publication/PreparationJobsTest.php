<?php
/**
 * A usable partial knowledge index is distinct from completed preparation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\PreparationJobs;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Safe product availability survives a partial build; the queue keeps retrying.
 *
 * @covers \Linker\Commerce\Products\Publication\PreparationJobs
 */
final class PreparationJobsTest extends TestCase {
	use \Linker\Commerce\Tests\Support\CurrentFaqProduct;

	/**
	 * Current native queue fixture.
	 *
	 * @var array<string,mixed>
	 */
	private array $state = array();

	/**
	 * Previous global database object, restored after each case.
	 *
	 * @var mixed
	 */
	private mixed $previous_database;

	/** A current published product and a connection-owned queue lock. */
	public function setUp(): void {
		parent::setUp();
		$this->current_faq_product( 12, array() );
		$this->previous_database = $GLOBALS['wpdb'] ?? null;
		$database                = Mockery::mock( \wpdb::class );
		$database->prefix        = 'wp_';
		$database->shouldReceive( 'prepare' )->andReturn( 'fixture lock' );
		$database->shouldReceive( 'get_var' )->andReturn( '1' );
		$GLOBALS['wpdb'] = $database;
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnUsing( static fn ( string $value ): string => $value );
		WP_Mock::userFunction( 'get_option' )->andReturnUsing( fn ( string $key ): array => PreparationJobs::OPTION === $key ? $this->state : array() );
		WP_Mock::userFunction( 'update_option' )->andReturnUsing(
			function ( string $key, mixed $value ): bool {
				if ( PreparationJobs::OPTION === $key ) {
					$this->state = $value;
				}
				return true;
			}
		);
	}

	/** Keep queue and upload fixture effects local to this case. */
	public function tearDown(): void {
		$GLOBALS['wpdb'] = $this->previous_database;
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** Missing/false/non-boolean coverage cannot acknowledge a complete index. */
	public function test_incomplete_coverage_remains_retryable_with_safe_products_available(): void {
		foreach ( array( null, false, 'true' ) as $complete ) {
			$request = $this->receipt( 'knowledge' );
			if ( null !== $complete ) {
				$request['preparation_complete'] = $complete;
			}
			$result = ( new PreparationJobs() )->acknowledge( $request );
			$this->assertSame(
				array(
					'accepted' => true,
					'complete' => false,
				),
				$result
			);
			$this->assertSame( 'pending', $this->state['knowledge']['status'] );
			$this->assertFalse( $this->state['knowledge']['preparation_complete'] );
			$this->assertSame( 'Some current document associations still lack proven passages.', $this->state['knowledge']['error'] );
			$this->assertTrue( PreparationJobs::readiness( 12, $request['prepared_products'][0]['product_revision'] )['knowledge'] );
			$this->assertSame( 0, $this->state['knowledge']['lease_expires_at'] );
			$this->assertArrayNotHasKey( 'lease_token', $this->state['knowledge'] );
		}
	}

	/** A source-bound complete receipt can finish; engine keeps its old contract. */
	public function test_complete_knowledge_and_existing_engine_receipts_finish(): void {
		foreach ( array( 'knowledge', 'engineering' ) as $consumer ) {
			$request = $this->receipt( $consumer );
			if ( 'knowledge' === $consumer ) {
				$request['preparation_complete'] = true;
			}
			$this->assertSame(
				array(
					'accepted' => true,
					'complete' => true,
				),
				( new PreparationJobs() )->acknowledge( $request )
			);
			$this->assertSame( 'ready', $this->state[ $consumer ]['status'] );
		}
	}

	/** Structured missing associations are current identities and contain no text. */
	public function test_missing_document_diagnostics_override_a_false_complete_claim(): void {
		$request                         = $this->receipt( 'knowledge' );
		$request['preparation_complete'] = true;
		$document                        = Publication::manifest()['documents'][0];
		$request['unprepared_documents'] = array(
			array(
				'document_id' => $document['document_id'],
				'product_id'  => 12,
				'reason'      => 'no_proven_passage',
				'text'        => 'must not persist',
			),
		);
		$this->assertSame(
			array(
				'accepted' => true,
				'complete' => false,
			),
			( new PreparationJobs() )->acknowledge( $request )
		);
		$this->assertSame(
			array(
				array(
					'document_id' => $document['document_id'],
					'product_id'  => 12,
					'reason'      => 'no_proven_passage',
				),
			),
			$this->state['knowledge']['unprepared_documents']
		);
	}

	/** A worker cannot use diagnostics to name an unrelated private document. */
	public function test_unknown_document_association_diagnostic_is_rejected(): void {
		$request                         = $this->receipt( 'knowledge' );
		$request['unprepared_documents'] = array(
			array(
				'document_id' => 'doc-private',
				'product_id'  => 12,
				'reason'      => 'document_unparsed',
			),
		);
		$result                          = ( new PreparationJobs() )->acknowledge( $request );
		$this->assertInstanceOf( \WP_Error::class, $result );
		$this->assertSame( 'invalid_job_ack', $result->get_error_code() );
		$this->assertSame( 'preparing', $this->state['knowledge']['status'] );
	}

	/** Reference records do not require supplier-answer knowledge preparation. */
	public function test_knowledge_expected_scope_excludes_engineering_reference_records(): void {
		$this->current_faq_meta[ EngineeringReference::ROLE_META_KEY ] = EngineeringReference::PV_MODULE;
		$request                         = $this->receipt( 'knowledge' );
		$request['prepared_products']    = array();
		$request['preparation_complete'] = true;
		$this->assertSame(
			array(
				'accepted' => true,
				'complete' => true,
			),
			( new PreparationJobs() )->acknowledge( $request )
		);
		$this->assertFalse( PreparationJobs::readiness( 12, Publication::manifest()['products'][0]['product_revision'] )['knowledge'] );
	}

	/**
	 * One currently leased native job, with the actual source product revision.
	 *
	 * @param string $consumer Current queue consumer.
	 * @return array<string,mixed>
	 */
	private function receipt( string $consumer ): array {
		$manifest    = Publication::manifest();
		$this->state = array(
			$consumer => array(
				'job_id'           => 'fixture-' . $consumer,
				'source_revision'  => $manifest['source_revision'],
				'lease_token'      => 'fixture-token',
				'lease_expires_at' => time() + 300,
				'status'           => 'preparing',
			),
		);
		return array(
			'job_id'            => 'fixture-' . $consumer,
			'source_revision'   => $manifest['source_revision'],
			'lease_token'       => 'fixture-token',
			'status'            => 'ready',
			'loaded_revision'   => 'actual-loaded-index-fixture',
			'prepared_products' => array(
				array(
					'product_id'       => 12,
					'product_revision' => $manifest['products'][0]['product_revision'],
				),
			),
		);
	}
}
