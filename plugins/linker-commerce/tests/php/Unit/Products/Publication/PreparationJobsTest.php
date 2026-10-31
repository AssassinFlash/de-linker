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
use Linker\Commerce\Products\Publication\Controller;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Product availability, successful materialization and semantic coverage differ.
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

	/** One fresh source read reconciles both consumers and leases its exact manifest. */
	public function test_claim_reconciles_both_consumers_with_one_fresh_source_read(): void {
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->once()->andReturn( true );
		WP_Mock::userFunction( 'get_posts' )->twice()->andReturn( array( 12 ) );
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->once()->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'fixture-token' );
		$result = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ) );
		$this->assertIsArray( $result );
		$this->assertIsArray( $result['job'] );
		$this->assertSame( $result['job']['source_revision'], $result['job']['manifest']['source_revision'] );
		$this->assertSame( $result['job']['source_revision'], $this->state['engineering']['source_revision'] );
		$this->assertSame( 'pending', $this->state['engineering']['status'] );
		$this->assertSame( 'preparing', $this->state['knowledge']['status'] );
		$this->assertSame( 1, $result['job']['activation_epoch'] );
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
			$this->assertTrue( PreparationJobs::readiness( 12, $request['prepared_products'][0]['product_revision'], $request['model_identity_revision'] )['knowledge'] );
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

	/** A deterministic semantic warning is settled, visible, and never grants readiness. */
	public function test_materialized_recipe_with_semantic_warning_does_not_build_again(): void {
		$request                         = $this->recipe_receipt();
		$request['prepared_products']    = array();
		$request['preparation_complete'] = false;
		$request['unprepared_documents'] = $this->diagnostic( 'no_proven_passage' );
		$result                          = ( new PreparationJobs() )->acknowledge( $request );
		$this->assertIsArray( $result );
		$this->assertTrue( $result['complete'] );
		$this->assertSame( 'ready', $this->state['knowledge']['status'] );
		$this->assertTrue( $this->state['knowledge']['materialization_complete'] );
		$this->assertFalse( $this->state['knowledge']['preparation_complete'] );
		$this->assertSame( 'index-fixture-1', $this->state['knowledge']['index_version'] );
		$this->assertSame( $request['unprepared_documents'], $this->state['knowledge']['unprepared_documents'] );
		$this->assertFalse( PreparationJobs::readiness( 12, 'missing' )['knowledge'] );
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		$this->assertSame( array( 'job' => null ), ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ) ) );
	}

	/** Parse failures retry even when a worker incorrectly claims materialization. */
	public function test_unparsed_document_keeps_recipe_retryable(): void {
		$request                         = $this->recipe_receipt();
		$request['unprepared_documents'] = $this->diagnostic( 'document_unparsed' );
		$result                          = ( new PreparationJobs() )->acknowledge( $request );
		$this->assertIsArray( $result );
		$this->assertFalse( $result['complete'] );
		$this->assertSame( 'pending', $this->state['knowledge']['status'] );
		$this->assertFalse( $this->state['knowledge']['materialization_complete'] );
	}

	/** Code-only upgrades automatically invalidate an old source/recipe lease. */
	public function test_recipe_change_reclaims_unchanged_source_and_rejects_old_receipt(): void {
		$old = $this->recipe_receipt();
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'new-token' );
		$result = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'b', 64 ) );
		$this->assertIsArray( $result );
		$this->assertIsArray( $result['job'] );
		$this->assertNotSame( $old['job_id'], $result['job']['job_id'] );
		$this->assertSame( $old['source_revision'], $result['job']['source_revision'] );
		$this->assertSame( str_repeat( 'b', 64 ), $result['job']['recipe_revision'] );
		$rejected = ( new PreparationJobs() )->acknowledge( $old );
		$this->assertInstanceOf( \WP_Error::class, $rejected );
		$this->assertSame( 'stale_job', $rejected->get_error_code() );
		$stale_worker = ( new PreparationJobs() )->claim( 'knowledge', 'old-mac', 600, str_repeat( 'a', 64 ) );
		$this->assertInstanceOf( \WP_Error::class, $stale_worker );
		$this->assertSame( str_repeat( 'b', 64 ), $this->state['knowledge']['recipe_revision'] );
	}

	/** Receipt metadata must describe the actual source, recipe and index generation. */
	public function test_recipe_loaded_identity_mismatches_are_rejected(): void {
		foreach ( array( 'recipe_revision', 'loaded_recipe_revision', 'loaded_revision', 'index_version', 'expected_serving_revision', 'serving_revision', 'activation_epoch', 'model_identity_revision', 'loaded_model_identity_revision' ) as $field ) {
			$request           = $this->recipe_receipt();
			$request[ $field ] = '';
			$result            = ( new PreparationJobs() )->acknowledge( $request );
			$this->assertInstanceOf( \WP_Error::class, $result, $field );
			$this->assertSame( 'preparing', $this->state['knowledge']['status'] );
		}
	}

	/** A legacy worker cannot silently erase the source's newer recipe requirement. */
	public function test_legacy_claim_cannot_downgrade_recipe(): void {
		$this->recipe_receipt();
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		$result = ( new PreparationJobs() )->claim( 'knowledge', 'old-mac', 600 );
		$this->assertInstanceOf( \WP_Error::class, $result );
		$this->assertSame( str_repeat( 'a', 64 ), $this->state['knowledge']['recipe_revision'] );
	}

	/** Reconciliation keeps the recipe while replacing a changed Woo source. */
	public function test_woo_source_change_keeps_recipe_and_new_job_identity(): void {
		$old = $this->recipe_receipt();
		$this->state['knowledge']['source_revision'] = 'old-woo-source';
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		( new PreparationJobs() )->reconcile();
		$this->assertSame( $old['source_revision'], $this->state['knowledge']['source_revision'] );
		$this->assertSame( str_repeat( 'a', 64 ), $this->state['knowledge']['recipe_revision'] );
		$this->assertNotSame( $old['job_id'], $this->state['knowledge']['job_id'] );
		$this->assertSame( 'pending', $this->state['knowledge']['status'] );
	}

	/** Explicit code rollback uses a current-recipe compare-and-swap, without data rollback. */
	public function test_known_recipe_rollback_preserves_woo_source_and_other_consumer(): void {
		$request                                     = $this->recipe_receipt();
		$this->state['knowledge']['loaded_products'] = array( 12 => $request['prepared_products'][0]['product_revision'] );
		$this->state['knowledge']['loaded_model_identity_revision'] = $request['model_identity_revision'];
		$this->state['knowledge']['superseded_recipes']             = array( str_repeat( 'b', 64 ) );
		$this->state['engineering']                                 = array(
			'status'          => 'ready',
			'source_revision' => 'untouched-engine',
		);
		$result = ( new PreparationJobs() )->reactivate_recipe( str_repeat( 'a', 64 ), str_repeat( 'b', 64 ) );
		$this->assertIsArray( $result );
		$this->assertTrue( $result['accepted'] );
		$this->assertSame( $request['source_revision'], $result['source_revision'] );
		$this->assertSame( str_repeat( 'b', 64 ), $result['recipe_revision'] );
		$this->assertSame( 'pending', $this->state['knowledge']['status'] );
		$this->assertSame( 0, $this->state['knowledge']['lease_expires_at'] );
		$this->assertArrayNotHasKey( 'lease_token', $this->state['knowledge'] );
		$this->assertSame( array( str_repeat( 'a', 64 ) ), $this->state['knowledge']['superseded_recipes'] );
		$this->assertTrue( PreparationJobs::readiness( 12, $request['prepared_products'][0]['product_revision'], $request['model_identity_revision'] )['knowledge'] );
		$this->assertSame(
			array(
				'status'          => 'ready',
				'source_revision' => 'untouched-engine',
			),
			$this->state['engineering']
		);
	}

	/** Unknown targets and a concurrent newer recipe cannot be overridden. */
	public function test_unknown_or_stale_recipe_rollback_is_rejected(): void {
		$this->recipe_receipt();
		$this->state['knowledge']['superseded_recipes'] = array( str_repeat( 'b', 64 ) );
		$before = $this->state;
		foreach ( array( array( 'a', 'c' ), array( 'c', 'b' ) ) as $identities ) {
			$result = ( new PreparationJobs() )->reactivate_recipe( str_repeat( $identities[0], 64 ), str_repeat( $identities[1], 64 ) );
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertSame( $before, $this->state );
		}
	}

	/** Every new lease has a higher durable activation fence, including retry and rollback. */
	public function test_activation_epoch_survives_retry_recipe_source_and_rollback(): void {
		$request                         = $this->recipe_receipt();
		$request['unprepared_documents'] = $this->diagnostic( 'document_unparsed' );
		( new PreparationJobs() )->acknowledge( $request );
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'retry-token' );
		$retry = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ) );
		$this->assertIsArray( $retry );
		$this->assertSame( 4, $retry['job']['activation_epoch'] );
		$next = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'b', 64 ) );
		$this->assertIsArray( $next );
		$this->assertSame( 5, $next['job']['activation_epoch'] );
		( new PreparationJobs() )->reactivate_recipe( str_repeat( 'b', 64 ), str_repeat( 'a', 64 ) );
		$rollback = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ) );
		$this->assertIsArray( $rollback );
		$this->assertSame( 6, $rollback['job']['activation_epoch'] );
		$this->state['knowledge']['source_revision'] = 'old-source';
		( new PreparationJobs() )->reconcile();
		$new_source = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ) );
		$this->assertIsArray( $new_source );
		$this->assertSame( 7, $new_source['job']['activation_epoch'] );
		$this->assertArrayNotHasKey( 'activation_epoch', $this->state['engineering'] );
	}

	/** Native preactivation verification is read-only and rejects stale lease context. */
	public function test_activation_lease_verification_and_old_epoch_ack_reject(): void {
		$request = $this->recipe_receipt();
		$verify  = array_merge( $request, array( 'consumer' => 'knowledge' ) );
		$before  = $this->state;
		$result  = ( new PreparationJobs() )->verify_lease( $verify );
		$this->assertIsArray( $result );
		$this->assertTrue( $result['verified'] );
		$this->assertSame( $before, $this->state );
		foreach ( array( 'source_revision', 'recipe_revision', 'lease_token', 'activation_epoch', 'model_identity_revision' ) as $field ) {
			$old           = $verify;
			$old[ $field ] = 'activation_epoch' === $field ? 2 : 'old';
			$this->assertInstanceOf( \WP_Error::class, ( new PreparationJobs() )->verify_lease( $old ) );
		}
		$request['activation_epoch'] = 2;
		$this->assertInstanceOf( \WP_Error::class, ( new PreparationJobs() )->acknowledge( $request ) );
		$this->assertSame( $before, $this->state );
	}

	/** A ready job reconciles the actual process every poll without trusting it to grant readiness. */
	public function test_ready_receipt_matches_once_and_requeues_changed_loaded_generation(): void {
		$request = $this->recipe_receipt();
		( new PreparationJobs() )->acknowledge( $request );
		$loaded = array(
			'source_revision'           => $request['source_revision'],
			'recipe_revision'           => $request['recipe_revision'],
			'expected_serving_revision' => $request['expected_serving_revision'],
			'serving_revision'          => $request['serving_revision'],
			'activation_epoch'          => $request['activation_epoch'],
			'index_version'             => $request['index_version'],
			'products'                  => $request['prepared_products'],
			'model_identity_revision'   => $request['model_identity_revision'],
		);
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'repair-token' );
		$this->assertSame( array( 'job' => null ), ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), $loaded ) );
		$before_products         = $this->state['knowledge']['loaded_products'];
		$loaded['index_version'] = 'unacknowledged-generation';
		$result                  = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), $loaded );
		$this->assertIsArray( $result );
		$this->assertSame( 4, $result['job']['activation_epoch'] );
		$this->assertSame( $before_products, $this->state['knowledge']['loaded_products'] );
		$this->assertSame( 'preparing', $this->state['knowledge']['status'] );
	}

	/** A failed process observation cannot revoke an acknowledged materialized generation. */
	public function test_unknown_loaded_observation_preserves_ready_without_new_lease(): void {
		$request                         = $this->recipe_receipt();
		$request['preparation_complete'] = false;
		$request['unprepared_documents'] = $this->diagnostic( 'no_proven_passage' );
		( new PreparationJobs() )->acknowledge( $request );
		$before = $this->state['knowledge'];
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'must-not-be-leased' );
		$result = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), null, true );
		$this->assertSame( array( 'job' => null ), $result );
		$this->assertSame( $before, $this->state['knowledge'] );
		$this->assertSame( 'ready', $this->state['knowledge']['status'] );
		$this->assertSame( 3, $this->state['knowledge']['activation_epoch'] );
	}

	/** Invalid JSON shapes are unknown observations, not proof of a changed generation. */
	public function test_malformed_loaded_observation_does_not_revoke_ready(): void {
		$request = $this->recipe_receipt();
		( new PreparationJobs() )->acknowledge( $request );
		$before = $this->state['knowledge'];
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'must-not-be-leased' );
		$this->assertSame( array( 'job' => null ), ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), array( 'index_version' => 'partial-response' ) ) );
		$this->assertSame( $before, $this->state['knowledge'] );
	}

	/** Unknown bootstrap still prepares because no native generation has been acknowledged. */
	public function test_unknown_bootstrap_still_claims_a_real_preparation(): void {
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'bootstrap-token' );
		$result = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), null, true );
		$this->assertIsArray( $result );
		$this->assertIsArray( $result['job'] );
		$this->assertSame( 1, $result['job']['activation_epoch'] );
		$this->assertSame( 'preparing', $this->state['knowledge']['status'] );
	}

	/** Restore only a native-ACKed same-input materialization, without relabeling its epoch. */
	public function test_failed_same_input_restores_trusted_receipt_without_rebuilding(): void {
		$request                         = $this->recipe_receipt();
		$request['preparation_complete'] = false;
		$request['unprepared_documents'] = $this->diagnostic( 'no_proven_passage' );
		( new PreparationJobs() )->acknowledge( $request );
		$this->state['knowledge']['status']                   = 'failed';
		$this->state['knowledge']['activation_epoch']         = 4;
		$this->state['knowledge']['materialization_complete'] = false;
		$this->state['knowledge']['unprepared_documents']     = array();
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'must-not-be-leased' );
		$result = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), $this->loaded_receipt( $request ) );
		$this->assertSame( array( 'job' => null ), $result );
		$this->assertSame( 'ready', $this->state['knowledge']['status'] );
		$this->assertTrue( $this->state['knowledge']['materialization_complete'] );
		$this->assertFalse( $this->state['knowledge']['preparation_complete'] );
		$this->assertSame( $request['unprepared_documents'], $this->state['knowledge']['unprepared_documents'] );
		$this->assertSame( 4, $this->state['knowledge']['activation_epoch'] );
		$this->assertSame( 3, $this->state['knowledge']['loaded_activation_epoch'] );
	}

	/** A fresh readback cannot cancel a current worker's native lease. */
	public function test_trusted_receipt_recovery_does_not_supersede_active_lease(): void {
		$request = $this->recipe_receipt();
		( new PreparationJobs() )->acknowledge( $request );
		$this->state['knowledge']['status']           = 'preparing';
		$this->state['knowledge']['activation_epoch'] = 4;
		$this->state['knowledge']['lease_token']      = 'another-live-worker';
		$this->state['knowledge']['lease_expires_at'] = time() + 300;
		$before                                       = $this->state['knowledge'];
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		$this->assertSame( array( 'job' => null ), ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, str_repeat( 'a', 64 ), $this->loaded_receipt( $request ) ) );
		$this->assertSame( $before, $this->state['knowledge'] );
	}

	/** Body fields cannot invent prior materialization or bypass changed inputs. */
	public function test_receipt_recovery_requires_native_snapshot_and_same_inputs(): void {
		foreach ( array( 'no_snapshot', 'recipe_changed', 'different_loaded_identity' ) as $case ) {
			$request = $this->recipe_receipt();
			( new PreparationJobs() )->acknowledge( $request );
			$this->state['knowledge']['status']           = 'failed';
			$this->state['knowledge']['activation_epoch'] = 4;
			$loaded                                       = $this->loaded_receipt( $request );
			$recipe                                       = str_repeat( 'a', 64 );
			if ( 'no_snapshot' === $case ) {
				unset( $this->state['knowledge']['loaded_materialization_complete'] );
			} elseif ( 'recipe_changed' === $case ) {
				$recipe = str_repeat( 'b', 64 );
			} else {
				$loaded['model_identity_revision'] = 'another-model-map';
			}
			WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
			WP_Mock::userFunction( 'wp_generate_password' )->andReturn( 'actual-new-lease' );
			$result = ( new PreparationJobs() )->claim( 'knowledge', 'mac', 600, $recipe, $loaded );
			$this->assertIsArray( $result );
			$this->assertIsArray( $result['job'], $case );
			$this->assertSame( 5, $result['job']['activation_epoch'], $case );
			$this->assertSame( 3, $this->state['knowledge']['loaded_activation_epoch'], $case );
			$this->assertSame( 'preparing', $this->state['knowledge']['status'], $case );
		}
	}

	/** One fresh native map serves independent windows without any PDF read. */
	public function test_authenticated_batch_reuses_one_map_without_cross_window_hits(): void {
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturn(
			array(
				(object) array(
					'object_id' => 12,
					'name'      => 'Energy Cabinet Pro',
				),
			)
		);
		$request             = $this->recipe_receipt();
		$request['consumer'] = 'knowledge';
		$request['texts']    = array_merge( array( 'Energy Cabinet', 'Pro' ), array_fill( 0, 18, 'Other source text.' ) );
		WP_Mock::userFunction( 'current_user_can' )->with( 'manage_woocommerce' )->andReturn( true );
		WP_Mock::userFunction( 'wp_upload_dir' )->andReturnUsing(
			static function (): never {
				throw new \LogicException( 'Batch identity cannot read documents.' );
			}
		);
		$refreshes = 0;
		$reads     = 0;
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			static function () use ( &$refreshes ): bool {
				++$refreshes;
				return true;
			}
		);
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			static function () use ( &$reads ): array {
				++$reads;
				return array( 12 );
			}
		);
		foreach ( array( false, true ) as $whole ) {
			if ( $whole ) {
				$request['texts'][0] = 'Use Energy Cabinet Pro here.';
			}
			$response = $this->dispatch( 'identify', $request );
			$this->assertInstanceOf( \WP_REST_Response::class, $response );
			$data = $response->get_data();
			$this->assertCount( $whole ? 1 : 0, $data['models'] );
			$this->assertSame( $request['model_identity_revision'], $data['model_identity_revision'] );
			$this->assertSame( 20, $data['metrics']['input_windows'] );
			$this->assertSame( 1, $data['metrics']['identity_reads'] );
			$this->assertSame( array_sum( array_map( 'strlen', $request['texts'] ) ), $data['metrics']['input_bytes'] );
			$this->assertSame( 1, $refreshes );
			$this->assertSame( 1, $reads );
			$refreshes = 0;
			$reads     = 0;
		}
	}

	/** Authentication, bounded independent inputs and the entire lease remain mandatory. */
	public function test_batch_rejects_invalid_auth_budget_and_lease_context(): void {
		$request             = $this->recipe_receipt();
		$request['consumer'] = 'knowledge';
		$request['texts']    = array( 'MODEL-12' );
		$allowed             = false;
		$logged_in           = false;
		// References are necessary because the same route is exercised across authentication states.
		WP_Mock::userFunction( 'current_user_can' )->andReturnUsing(
			static function () use ( &$allowed ): bool {
				return $allowed;
			}
		);
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturnUsing(
			static function () use ( &$logged_in ): bool {
				return $logged_in;
			}
		);
		foreach ( array( 401, 403 ) as $status ) {
			$error = $this->dispatch( 'identify', $request );
			$this->assertInstanceOf( \WP_Error::class, $error );
			$this->assertSame( array( 'status' => $status ), $error->get_error_data() );
			$logged_in = true;
		}
		$allowed = true;
		foreach ( array( array(), array_fill( 0, 21, 'MODEL-12' ), array( str_repeat( 'x', 16001 ) ), array( "\xff" ), array( ' ' ) ) as $texts ) {
			$invalid          = $request;
			$invalid['texts'] = $texts;
			$error            = $this->dispatch( 'identify', $invalid );
			$this->assertInstanceOf( \WP_Error::class, $error );
			$this->assertSame( 'invalid_models', $error->get_error_code() );
		}
		foreach ( array( 'text', 'models' ) as $mixed ) {
			$invalid           = $request;
			$invalid[ $mixed ] = null;
			$this->assertInstanceOf( \WP_Error::class, $this->dispatch( 'identify', $invalid ) );
		}
		foreach ( array( 'job_id', 'source_revision', 'recipe_revision', 'lease_token', 'activation_epoch', 'model_identity_revision', 'consumer' ) as $field ) {
			$invalid           = $request;
			$invalid[ $field ] = 'activation_epoch' === $field ? 2 : 'old';
			$error             = $this->dispatch( 'identify', $invalid );
			$this->assertInstanceOf( \WP_Error::class, $error, $field );
			$this->assertSame( array( 'status' => 409 ), $error->get_error_data() );
		}
		$this->state['knowledge']['lease_expires_at'] = time() - 1;
		$this->assertInstanceOf( \WP_Error::class, $this->dispatch( 'identify', $request ) );
	}

	/** An old client or unversioned loaded receipt never proves current knowledge. */
	public function test_unknown_identity_is_not_a_claim_or_loaded_permission(): void {
		$error = $this->dispatch(
			'jobs/claim',
			array(
				'consumer'      => 'knowledge',
				'worker_id'     => 'old-worker',
				'lease_seconds' => 600,
			)
		);
		$this->assertInstanceOf( \WP_Error::class, $error );
		$this->assertSame( 'identity_required', $error->get_error_code() );
		$request = $this->recipe_receipt();
		$legacy  = $request;
		unset( $legacy['model_identity_revision'] );
		$this->assertInstanceOf( \WP_Error::class, ( new PreparationJobs() )->verify_lease( $legacy + array( 'consumer' => 'knowledge' ) ) );
		$this->assertInstanceOf( \WP_Error::class, ( new PreparationJobs() )->acknowledge( $legacy ) );
		( new PreparationJobs() )->acknowledge( $request );
		unset( $this->state['knowledge']['loaded_model_identity_revision'] );
		$this->assertFalse( PreparationJobs::readiness( 12, $request['prepared_products'][0]['product_revision'], $request['model_identity_revision'] )['knowledge'] );
	}

	/** Draft labels fence knowledge while the published source and engineering projection stay stable. */
	public function test_draft_identity_change_invalidates_only_knowledge_and_scopes(): void {
		$draft_model = 'DRAFT-13';
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing( static fn ( array $args ): array => is_array( $args['post_status'] ) ? array( 12, 13 ) : ( isset( $args['date_query'] ) ? array() : array( 12 ) ) );
		WP_Mock::userFunction( 'get_post_type' )->with( 13 )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->with( 13 )->andReturn( 'draft' );
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturnUsing(
			static function () use ( &$draft_model ): array {
				return array(
					(object) array(
						'object_id' => 12,
						'name'      => 'MODEL-12',
					),
					(object) array(
						'object_id' => 13,
						'name'      => $draft_model,
					),
				);
			}
		);
		WP_Mock::userFunction( 'update_postmeta_cache' );
		WP_Mock::userFunction( 'update_object_term_cache' );
		$old = $this->recipe_receipt();
		( new PreparationJobs() )->acknowledge( $old );
		$this->state['engineering'] = array(
			'source_revision' => $old['source_revision'],
			'status'          => 'ready',
			'job_id'          => 'stable-engine',
		);
		$engine_before              = $this->state['engineering'];
		$feed_before                = \Linker\Commerce\Products\EngineeringFeed::feed( '2027-01-01' );
		$draft_model                = 'DRAFT-13-RENAMED';
		$manifest                   = Publication::manifest();
		$this->assertSame( $old['source_revision'], $manifest['source_revision'] );
		$this->assertNotSame( $old['model_identity_revision'], $manifest['model_identity_revision'] );
		$this->assertFalse( $manifest['products'][0]['ready']['knowledge'] );
		$this->assertFalse( Publication::validate( array( 'model_identity_revision' => $old['model_identity_revision'] ) )['valid'] );
		$this->assertTrue(
			Publication::validate(
				array(
					'products'  => array(),
					'documents' => array(),
				)
			)['valid']
		);
		$feed_after = \Linker\Commerce\Products\EngineeringFeed::feed( '2027-01-01' );
		unset( $feed_before['generated_at'], $feed_after['generated_at'] );
		$this->assertSame( $feed_before, $feed_after );
		$this->assertArrayNotHasKey( 'model_identity_revision', $feed_after );
		$rejected = ( new PreparationJobs() )->verify_identity_lease( $old + array( 'consumer' => 'knowledge' ), $manifest['model_identity_revision'] );
		$this->assertInstanceOf( \WP_Error::class, $rejected );
		$this->assertSame( 'stale_job', $rejected->get_error_code() );
		WP_Mock::userFunction( 'delete_option' )->with( 'linker_publication_pending' )->andReturn( true );
		( new PreparationJobs() )->reconcile();
		$this->assertSame( 'pending', $this->state['knowledge']['status'] );
		$this->assertNotSame( $old['job_id'], $this->state['knowledge']['job_id'] );
		$this->assertSame( $engine_before, $this->state['engineering'] );
		$this->assertInstanceOf( \WP_Error::class, ( new PreparationJobs() )->acknowledge( $old ) );
	}

	/**
	 * Run the real REST dispatcher without creating a WordPress instance.
	 *
	 * @param string              $path Registered action.
	 * @param array<string,mixed> $body Decoded request.
	 */
	private function dispatch( string $path, array $body ): \WP_REST_Response|\WP_Error {
		WP_Mock::userFunction( 'nocache_headers' );
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn ( mixed $value ): bool => $value instanceof \WP_Error );
		$request = Mockery::mock( \WP_REST_Request::class );
		$request->shouldReceive( 'get_body' )->andReturn( (string) json_encode( $body ) );
		$request->shouldReceive( 'get_json_params' )->andReturn( $body );
		return ( new Controller() )->dispatch( $path, $request );
	}

	/**
	 * A recipe-aware current generation receipt.
	 *
	 * @return array<string,mixed>
	 */
	private function recipe_receipt(): array {
		$request                                      = $this->receipt( 'knowledge' );
		$this->state['knowledge']['recipe_revision']  = str_repeat( 'a', 64 );
		$this->state['knowledge']['activation_epoch'] = 3;
		return array_merge(
			$request,
			array(
				'recipe_revision'           => str_repeat( 'a', 64 ),
				'loaded_recipe_revision'    => str_repeat( 'a', 64 ),
				'expected_serving_revision' => str_repeat( 'c', 64 ),
				'serving_revision'          => str_repeat( 'c', 64 ),
				'activation_epoch'          => 3,
				'loaded_revision'           => $request['source_revision'],
				'index_version'             => 'index-fixture-1',
				'materialization_complete'  => true,
				'preparation_complete'      => true,
			)
		);
	}

	/**
	 * Actual process diagnostic corresponding to one native ACK fixture.
	 *
	 * @param array<string,mixed> $request Accepted generation receipt.
	 * @return array<string,mixed>
	 */
	private function loaded_receipt( array $request ): array {
		return array(
			'source_revision'           => $request['loaded_revision'],
			'model_identity_revision'   => $request['loaded_model_identity_revision'],
			'recipe_revision'           => $request['loaded_recipe_revision'],
			'expected_serving_revision' => $request['expected_serving_revision'],
			'serving_revision'          => $request['serving_revision'],
			'index_version'             => $request['index_version'],
			'activation_epoch'          => $request['activation_epoch'],
			'products'                  => $request['prepared_products'],
			'materialization_complete'  => $request['materialization_complete'],
			'preparation_complete'      => $request['preparation_complete'],
			'unprepared_documents'      => $request['unprepared_documents'] ?? array(),
		);
	}

	/**
	 * One current source warning.
	 *
	 * @param string $reason Structured diagnostic reason.
	 * @return list<array{document_id:string,product_id:int,reason:string}>
	 */
	private function diagnostic( string $reason ): array {
		return array(
			array(
				'document_id' => Publication::manifest()['documents'][0]['document_id'],
				'product_id'  => 12,
				'reason'      => $reason,
			),
		);
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
		if ( 'knowledge' === $consumer ) {
			$this->state[ $consumer ]['model_identity_revision'] = $manifest['model_identity_revision'];
		}
		return array(
			'model_identity_revision'        => $manifest['model_identity_revision'],
			'loaded_model_identity_revision' => $manifest['model_identity_revision'],
			'job_id'                         => 'fixture-' . $consumer,
			'source_revision'                => $manifest['source_revision'],
			'lease_token'                    => 'fixture-token',
			'status'                         => 'ready',
			'loaded_revision'                => 'actual-loaded-index-fixture',
			'prepared_products'              => array(
				array(
					'product_id'       => 12,
					'product_revision' => $manifest['products'][0]['product_revision'],
				),
			),
		);
	}
}
