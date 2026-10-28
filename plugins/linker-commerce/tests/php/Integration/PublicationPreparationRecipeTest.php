<?php
/**
 * Actual native queue locks and REST dispatch preserve compiler/source identities.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\Controller;
use Linker\Commerce\Products\Publication\PreparationJobs;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Only queue options are isolated; original products, uploads and permissions stay.
 *
 * @coversNothing
 */
final class PublicationPreparationRecipeTest extends IntegrationTestCase {

	/** Restore the exact pre-test queue, after any task-owned product is removed. */
	protected function setUp(): void {
		parent::setUp();
		$this->assertSame( 'local', wp_get_environment_type(), 'Never run preparation fixtures outside a local instance.' );
		$jobs    = get_option( PreparationJobs::OPTION );
		$pending = get_option( 'linker_publication_pending' );
		$this->later(
			static function () use ( $jobs, $pending ): void {
				if ( false === $jobs ) {
					delete_option( PreparationJobs::OPTION );
				} else {
					update_option( PreparationJobs::OPTION, $jobs, false );
				}
				if ( false === $pending ) {
					delete_option( 'linker_publication_pending' );
				} else {
					update_option( 'linker_publication_pending', $pending, false );
				}
			}
		);
		$actions = array();
		$record  = static function ( int $id ) use ( &$actions ): void {
			$action = \ActionScheduler::store()->fetch_action( $id );
			if ( 'linker_publication_reconcile' === $action->get_hook() && 'linker-publication' === $action->get_group() ) {
				$actions[] = $id;
			}
		};
		add_action( 'action_scheduler_stored_action', $record );
		$this->later(
			static function () use ( &$actions, $record ): void {
				remove_action( 'action_scheduler_stored_action', $record );
				foreach ( $actions as $id ) {
					\ActionScheduler::store()->delete_action( $id );
				}
			}
		);
		update_option( PreparationJobs::OPTION, array(), false );
	}

	/** Successful processing settles once while missing semantic coverage remains visible. */
	public function test_native_materialized_semantic_warning_settles_without_product_readiness(): void {
		$job     = $this->claim( str_repeat( 'a', 64 ) );
		$request = $this->receipt( $job, 'no_proven_passage' );
		$result  = ( new PreparationJobs() )->acknowledge( $request );
		$this->assertSame(
			array(
				'accepted' => true,
				'complete' => true,
			),
			$result
		);
		$state = get_option( PreparationJobs::OPTION );
		$this->assertSame( 'ready', $state['knowledge']['status'] );
		$this->assertTrue( $state['knowledge']['materialization_complete'] );
		$this->assertFalse( $state['knowledge']['preparation_complete'] );
		$this->assertSame( 'native-generation-1', $state['knowledge']['index_version'] );
		$this->assertSame( $job['recipe_revision'], $state['knowledge']['loaded_recipe_revision'] );
		$this->assertSame( $request['unprepared_documents'], $state['knowledge']['unprepared_documents'] );
		$this->assertSame( array( 'job' => null ), ( new PreparationJobs() )->claim( 'knowledge', 'native-fixture', 600, $job['recipe_revision'] ) );
		$this->assertSame( array(), $state['knowledge']['loaded_products'] );
	}

	/** Native failed parsing retries the same recipe with a new lease. */
	public function test_native_parse_failure_remains_retryable(): void {
		$job     = $this->claim( str_repeat( 'a', 64 ) );
		$request = $this->receipt( $job, 'document_unparsed' );
		$this->assertSame(
			array(
				'accepted' => true,
				'complete' => false,
			),
			( new PreparationJobs() )->acknowledge( $request )
		);
		$again = $this->claim( $job['recipe_revision'] );
		$this->assertSame( $job['job_id'], $again['job_id'] );
		$this->assertNotSame( $job['lease_token'], $again['lease_token'] );
		$state = get_option( PreparationJobs::OPTION );
		$this->assertFalse( $state['knowledge']['materialization_complete'] );
	}

	/** Code corrections reprocess the same Woo source and reject stale workers/receipts. */
	public function test_native_recipe_upgrade_and_deliberate_rollback(): void {
		$old = $this->claim( str_repeat( 'a', 64 ) );
		$new = $this->claim( str_repeat( 'b', 64 ) );
		$this->assertSame( $old['source_revision'], $new['source_revision'] );
		$this->assertNotSame( $old['job_id'], $new['job_id'] );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->acknowledge( $this->receipt( $old, 'no_proven_passage' ) ) );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->claim( 'knowledge', 'old-native-fixture', 600, $old['recipe_revision'] ) );
		$before = get_option( PreparationJobs::OPTION );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->reactivate_recipe( str_repeat( 'c', 64 ), $old['recipe_revision'] ) );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->reactivate_recipe( $new['recipe_revision'], str_repeat( 'c', 64 ) ) );
		$this->assertSame( $before, get_option( PreparationJobs::OPTION ) );
		$rollback = ( new PreparationJobs() )->reactivate_recipe( $new['recipe_revision'], $old['recipe_revision'] );
		$this->assertIsArray( $rollback );
		$this->assertTrue( $rollback['accepted'] );
		$this->assertSame( $new['source_revision'], $rollback['source_revision'] );
		$this->assertSame( $old['recipe_revision'], $rollback['recipe_revision'] );
		$after = get_option( PreparationJobs::OPTION );
		$this->assertSame( $before['engineering'], $after['engineering'] );
		$this->assertSame( $before['knowledge']['loaded_products'], $after['knowledge']['loaded_products'] );
		$this->assertSame( 0, $after['knowledge']['lease_expires_at'] );
	}

	/** Normal native Woo saves replace source identity and reject the older receipt. */
	public function test_native_woo_save_requeues_without_losing_recipe(): void {
		$old     = $this->claim( str_repeat( 'a', 64 ) );
		$product = $this->product( '100' );
		$product->set_name( 'Preparation source fixture ' . self::tag() );
		$product->save();
		$new = $this->claim( $old['recipe_revision'] );
		$this->assertNotSame( $old['source_revision'], $new['source_revision'] );
		$this->assertSame( $old['recipe_revision'], $new['recipe_revision'] );
		$this->assertNotSame( $old['job_id'], $new['job_id'] );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->acknowledge( $this->receipt( $old, 'no_proven_passage' ) ) );
	}

	/**
	 * Existing dispatch and CLI recovery preserve the exact activation fence.
	 *
	 * Isolate the native WP-CLI constant from other WordPress fixtures.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_native_activation_verification_and_monotonic_retry_fence(): void {
		if ( ! defined( 'WP_CLI' ) ) {
			define( 'WP_CLI', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Native CLI context is isolated in this fixture process.
		}
		$seed = $this->claim( str_repeat( 'e', 64 ) );
		$this->assertIsArray( ( new PreparationJobs() )->acknowledge( $this->receipt( $seed, 'no_proven_passage' ) ) );
		$first = $this->claim( str_repeat( 'a', 64 ) );
		$this->assertGreaterThan( 0, $first['activation_epoch'] );
		$body = array_merge(
			$first,
			array(
				'operation' => 'verify',
				'consumer'  => 'knowledge',
			)
		);
		unset( $body['manifest'] );
		$request = new WP_REST_Request( 'POST' );
		$request->set_header( 'content-type', 'application/json' );
		$request->set_body( (string) wp_json_encode( $body ) );
		$before   = get_option( PreparationJobs::OPTION );
		$verified = ( new Controller() )->dispatch( 'jobs/claim', $request );
		$this->assertInstanceOf( WP_REST_Response::class, $verified );
		$this->assertTrue( $verified->get_data()['verified'] );
		$this->assertSame( $before, get_option( PreparationJobs::OPTION ) );
		$identity = array(
			'job_id'           => $first['job_id'],
			'source_revision'  => $first['source_revision'],
			'recipe_revision'  => $first['recipe_revision'],
			'activation_epoch' => $first['activation_epoch'],
			'worker_id'        => 'native-fixture',
		);
		$recover  = static fn ( array $expected, bool $stopped, bool $apply ): array|WP_Error => ( new PreparationJobs() )->abandon_interrupted_knowledge( $expected['job_id'], $expected['source_revision'], $expected['recipe_revision'], $expected['activation_epoch'], $expected['worker_id'], $stopped, $apply );
		wp_set_current_user( 0 );
		$this->assertInstanceOf( WP_Error::class, $recover( $identity, true, true ) );
		wp_set_current_user( 1 );
		$this->assertTrue( current_user_can( 'manage_woocommerce' ) );
		$preview = $recover( $identity, false, false );
		$this->assertIsArray( $preview );
		$this->assertFalse( $preview['applied'] );
		$this->assertStringNotContainsString( $first['lease_token'], (string) wp_json_encode( $preview ) );
		$this->assertSame( $before, get_option( PreparationJobs::OPTION ) );
		$this->assertInstanceOf( WP_Error::class, $recover( $identity, false, true ) );
		foreach ( array_keys( $identity ) as $field ) {
			$wrong           = $identity;
			$wrong[ $field ] = 'activation_epoch' === $field ? $first['activation_epoch'] + 1 : ( 'worker_id' === $field ? 'another-worker' : str_repeat( 'f', 64 ) );
			$this->assertInstanceOf( WP_Error::class, $recover( $wrong, true, true ) );
			$this->assertSame( $before, get_option( PreparationJobs::OPTION ) );
		}
		$this->assertIsArray( $recover( $identity, true, true ) );
		$expected_state                                  = $before;
		$expected_state['knowledge']['status']           = 'failed';
		$expected_state['knowledge']['lease_expires_at'] = 0;
		unset( $expected_state['knowledge']['lease_token'] );
		$this->assertSame( $expected_state, get_option( PreparationJobs::OPTION ) );
		$this->assertInstanceOf( WP_Error::class, $recover( $identity, true, true ) );
		$this->assertInstanceOf( WP_Error::class, ( new Controller() )->dispatch( 'jobs/claim', $request ) );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->acknowledge( $this->receipt( $first, 'no_proven_passage' ) ) );
		$second = $this->claim( $first['recipe_revision'] );
		$this->assertSame( $first['activation_epoch'] + 1, $second['activation_epoch'] );
		$this->assertInstanceOf( WP_Error::class, ( new Controller() )->dispatch( 'jobs/claim', $request ) );
		$third = $this->claim( str_repeat( 'b', 64 ) );
		$this->assertSame( $second['activation_epoch'] + 1, $third['activation_epoch'] );
		( new PreparationJobs() )->reactivate_recipe( $third['recipe_revision'], $first['recipe_revision'] );
		$rollback = $this->claim( $first['recipe_revision'] );
		$this->assertSame( $third['activation_epoch'] + 1, $rollback['activation_epoch'] );
	}

	/** A successful queue receipt cannot hide a later switched or unavailable process. */
	public function test_native_ready_receipt_reconciles_actual_process_and_runtime(): void {
		$job                          = $this->claim( str_repeat( 'a', 64 ) );
		$receipt                      = $this->receipt( $job, 'no_proven_passage' );
		$mismatch                     = $receipt;
		$mismatch['serving_revision'] = str_repeat( 'd', 64 );
		$this->assertInstanceOf( WP_Error::class, ( new PreparationJobs() )->acknowledge( $mismatch ) );
		$this->assertSame(
			array(
				'accepted' => true,
				'complete' => true,
			),
			( new PreparationJobs() )->acknowledge( $receipt )
		);
		$loaded = array(
			'source_revision'           => $job['source_revision'],
			'recipe_revision'           => $job['recipe_revision'],
			'expected_serving_revision' => $receipt['expected_serving_revision'],
			'serving_revision'          => $receipt['serving_revision'],
			'index_version'             => $receipt['index_version'],
			'activation_epoch'          => $job['activation_epoch'],
			'products'                  => array(),
		);
		$this->assertSame( array( 'job' => null ), ( new PreparationJobs() )->claim( 'knowledge', 'native-fixture', 600, $job['recipe_revision'], $loaded ) );
		$before                  = get_option( PreparationJobs::OPTION );
		$loaded['index_version'] = 'unexpected-generation';
		$result                  = ( new PreparationJobs() )->claim( 'knowledge', 'native-fixture', 600, $job['recipe_revision'], $loaded );
		$this->assertIsArray( $result );
		$this->assertSame( $job['activation_epoch'] + 1, $result['job']['activation_epoch'] );
		$after = get_option( PreparationJobs::OPTION );
		$this->assertSame( $before['knowledge']['loaded_products'], $after['knowledge']['loaded_products'] );
		$this->assertSame( $before['engineering'], $after['engineering'] );
	}

	/**
	 * Exercise actual JSON dispatch including the optional recipe field.
	 *
	 * @param string $recipe Actual fixture compiler hash.
	 * @return array<string,mixed>
	 */
	private function claim( string $recipe ): array {
		$request = new WP_REST_Request( 'POST' );
		$request->set_header( 'content-type', 'application/json' );
		$request->set_body(
			(string) wp_json_encode(
				array(
					'consumer'        => 'knowledge',
					'worker_id'       => 'native-fixture',
					'lease_seconds'   => 600,
					'recipe_revision' => $recipe,
				)
			)
		);
		$result = ( new Controller() )->dispatch( 'jobs/claim', $request );
		$this->assertInstanceOf( WP_REST_Response::class, $result );
		$job = $result->get_data()['job'];
		$this->assertIsArray( $job );
		$this->assertSame( $recipe, $job['recipe_revision'] );
		return $job;
	}

	/**
	 * A source-bound serving receipt; no product is made usable without proven text.
	 *
	 * @param array<string,mixed> $job Actual native job.
	 * @param string              $reason Deliberate coverage/processing diagnostic.
	 * @return array<string,mixed>
	 */
	private function receipt( array $job, string $reason ): array {
		$this->assertNotEmpty( $job['manifest']['documents'], 'Run against the required real snapshot with authorized documents.' );
		$document = $job['manifest']['documents'][0];
		return array(
			'job_id'                    => $job['job_id'],
			'lease_token'               => $job['lease_token'],
			'source_revision'           => $job['source_revision'],
			'loaded_revision'           => $job['source_revision'],
			'recipe_revision'           => $job['recipe_revision'],
			'loaded_recipe_revision'    => $job['recipe_revision'],
			'expected_serving_revision' => str_repeat( 'c', 64 ),
			'serving_revision'          => str_repeat( 'c', 64 ),
			'activation_epoch'          => $job['activation_epoch'],
			'index_version'             => 'native-generation-1',
			'status'                    => 'ready',
			'prepared_products'         => array(),
			'materialization_complete'  => true,
			'preparation_complete'      => false,
			'unprepared_documents'      => array(
				array(
					'document_id' => $document['document_id'],
					'product_id'  => $document['product_ids'][0],
					'reason'      => $reason,
				),
			),
		);
	}
}
