<?php
/**
 * Persistent preparation leases; acknowledgement never changes public permission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Inquiry\Assessment\Lock;
use WP_Error;

/** A bounded current job and last loaded receipt per consumer. */
final class PreparationJobs {
	public const OPTION    = 'linker_publication_jobs';
	public const CONSUMERS = array( 'knowledge', 'engineering' );

	/**
	 * Report only matching loaded product versions.
	 *
	 * @param int    $id Canonical product ID.
	 * @param string $revision Current product revision.
	 * @return array{knowledge:bool,engineering:bool}
	 */
	public static function readiness( int $id, string $revision ): array {
		$state  = get_option( self::OPTION, array() );
		$result = array();
		foreach ( self::CONSUMERS as $consumer ) {
			$result[ $consumer ] = is_array( $state ) && ( $state[ $consumer ]['loaded_products'][ $id ] ?? '' ) === $revision;
		}
		return $result;
	}

	/** Hooks register a durable reconciliation, never heavy parsing during save. */
	public function changed(): void {
		update_option( 'linker_publication_pending', true, false );
		if ( function_exists( 'as_enqueue_async_action' ) && ! as_has_scheduled_action( 'linker_publication_reconcile', array(), 'linker-publication' ) ) {
			as_enqueue_async_action( 'linker_publication_reconcile', array(), 'linker-publication', true );
		}
	}

	/** Current reads remain authoritative if an event or process was lost. */
	public function reconcile(): void {
		Lock::run(
			'publication-jobs',
			static function (): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				$state    = is_array( $state ) ? $state : array();
				foreach ( self::CONSUMERS as $consumer ) {
					if ( ( $state[ $consumer ]['source_revision'] ?? '' ) !== $manifest['source_revision'] ) {
						$state[ $consumer ] = self::pending( $consumer, $manifest['source_revision'], $state[ $consumer ] ?? array(), (string) ( $state[ $consumer ]['recipe_revision'] ?? '' ) );
					}
				}
				update_option( self::OPTION, $state, false );
				delete_option( 'linker_publication_pending' );
			}
		);
	}

	/**
	 * Claim the current source under a bounded worker lease.
	 *
	 * @param string                   $consumer Consumer identity.
	 * @param string                   $worker_id Worker identity.
	 * @param int                      $lease_seconds Requested lease, bounded to WordPress one day.
	 * @param string                   $recipe_revision Actual knowledge compiler identity; empty is the legacy protocol.
	 * @param array<string,mixed>|null $loaded_receipt Actual process readback; never grants product readiness.
	 * @param bool                     $loaded_unavailable Actual process readback failed and requires repair when ready.
	 * @return array<string,mixed>|WP_Error
	 */
	public function claim( string $consumer, string $worker_id, int $lease_seconds, string $recipe_revision = '', ?array $loaded_receipt = null, bool $loaded_unavailable = false ): array|WP_Error {
		if ( ! in_array( $consumer, self::CONSUMERS, true ) || '' === $worker_id || $lease_seconds < 1 || $lease_seconds > DAY_IN_SECONDS || ( '' !== $recipe_revision && ( 'knowledge' !== $consumer || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $recipe_revision ) ) ) ) {
			return new WP_Error( 'invalid_job_request', 'Invalid consumer, worker or lease.', array( 'status' => 400 ) );
		}
		$this->reconcile();
		$result = array( 'job' => null );
		$taken  = Lock::run(
			'publication-jobs',
			static function () use ( $consumer, $worker_id, $lease_seconds, $recipe_revision, $loaded_receipt, $loaded_unavailable, &$result ): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				$job      = $state[ $consumer ] ?? array();
				if ( 'knowledge' === $consumer && ( $job['recipe_revision'] ?? '' ) !== $recipe_revision ) {
					if ( '' === $recipe_revision || in_array( $recipe_revision, $job['superseded_recipes'] ?? array(), true ) ) {
						$result = new WP_Error( 'recipe_required', 'This knowledge job requires a recipe-aware worker.', array( 'status' => 409 ) );
						return;
					}
					// Compiler corrections reprocess an unchanged Woo source and invalidate
					// older leases. Loaded products remain a versioned serving receipt.
					$job = self::pending( $consumer, $manifest['source_revision'], $job, $recipe_revision );
				}
				if ( 'knowledge' === $consumer && '' !== $recipe_revision && 'ready' === ( $job['status'] ?? '' ) && ( $loaded_unavailable || ( null !== $loaded_receipt && ! self::matches_loaded( $job, $loaded_receipt ) ) ) ) {
					$job          = self::pending( $consumer, $manifest['source_revision'], $job, $recipe_revision );
					$job['error'] = 'The serving process differs from the acknowledged knowledge generation.';
				}
				if ( 'ready' === ( $job['status'] ?? '' ) || (int) ( $job['lease_expires_at'] ?? 0 ) > time() || ( $job['source_revision'] ?? '' ) !== $manifest['source_revision'] ) {
					return;
				}
				$job['lease_token']      = wp_generate_password( 64, false );
				$job['lease_expires_at'] = time() + $lease_seconds;
				$job['worker_id']        = $worker_id;
				$job['status']           = 'preparing';
				if ( 'knowledge' === $consumer ) {
					// Every lease, including retries, has a durable higher activation
					// fence. Source/recipe changes and rollback never reset this counter.
					$job['activation_epoch'] = (int) ( $job['activation_epoch'] ?? 0 ) + 1;
				}
				$state[ $consumer ] = $job;
				update_option( self::OPTION, $state, false );
				unset( $job['loaded_products'], $job['error'], $job['worker_id'], $job['status'] );
				$job['manifest'] = $manifest;
				$result          = array( 'job' => $job );
			}
		);
		return $taken ? $result : new WP_Error( 'publication_busy', 'Preparation queue is busy.', array( 'status' => 503 ) );
	}

	/**
	 * Verify a leased activation immediately before the private VPS atomic switch.
	 *
	 * Reuses the authenticated claim route; no new permission or publication grant.
	 *
	 * @param array<string,mixed> $request Exact lease context, including activation epoch.
	 * @return array<string,mixed>|WP_Error
	 */
	public function verify_lease( array $request ): array|WP_Error {
		$result = new WP_Error( 'stale_job', 'The activation lease or current source has changed.', array( 'status' => 409 ) );
		$taken  = Lock::run(
			'publication-jobs',
			static function () use ( $request, &$result ): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				$job      = $state['knowledge'] ?? array();
				if ( 'knowledge' !== ( $request['consumer'] ?? '' ) || 'preparing' !== ( $job['status'] ?? '' ) || ( $job['job_id'] ?? '' ) !== ( $request['job_id'] ?? null ) || ! is_string( $request['lease_token'] ?? null ) || ! hash_equals( $job['lease_token'] ?? '', $request['lease_token'] ) || (int) ( $job['lease_expires_at'] ?? 0 ) <= time() || ( $request['source_revision'] ?? '' ) !== $manifest['source_revision'] || ( $job['source_revision'] ?? '' ) !== $manifest['source_revision'] || '' === ( $job['recipe_revision'] ?? '' ) || ( $request['recipe_revision'] ?? '' ) !== ( $job['recipe_revision'] ?? '' ) || ! self::same_epoch( $job, $request ) ) {
					return;
				}
				$result = array(
					'verified'         => true,
					'activation_epoch' => $job['activation_epoch'],
					'job_id'           => $job['job_id'],
					'source_revision'  => $job['source_revision'],
					'recipe_revision'  => $job['recipe_revision'],
				);
			}
		);
		return $taken ? $result : new WP_Error( 'publication_busy', 'Preparation queue is busy.', array( 'status' => 503 ) );
	}

	/**
	 * Abandon one operator-confirmed interrupted lease through native WP-CLI only.
	 *
	 * This is not a receipt: current Woo facts, the activation epoch and every
	 * previously loaded field remain unchanged. A later claim gets a new fence.
	 *
	 * @param string $job_id         Exact observed knowledge job.
	 * @param string $source         Exact observed and current Woo source.
	 * @param string $recipe         Exact observed compiler identity.
	 * @param int    $epoch          Exact observed activation epoch.
	 * @param string $worker_id      Exact observed interrupted worker.
	 * @param bool   $worker_stopped Operator has independently confirmed it stopped.
	 * @param bool   $apply          Preview by default; explicit application only.
	 * @return array<string,mixed>|WP_Error
	 */
	public function abandon_interrupted_knowledge( string $job_id, string $source, string $recipe, int $epoch, string $worker_id, bool $worker_stopped, bool $apply = false ): array|WP_Error {
		if ( ! defined( 'WP_CLI' ) || ! WP_CLI || ! current_user_can( 'manage_woocommerce' ) ) {
			return new WP_Error( 'interrupted_lease_cli_required', 'This recovery requires a privileged native WP-CLI operator.', array( 'status' => 403 ) );
		}
		if ( 1 !== preg_match( '/^[a-f0-9]{64}$/D', $job_id ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $source ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $recipe ) || $epoch < 1 || '' === $worker_id ) {
			return new WP_Error( 'invalid_interrupted_lease', 'Recovery requires exact job, source, recipe, epoch and worker identities.', array( 'status' => 400 ) );
		}
		if ( $apply && ! $worker_stopped ) {
			return new WP_Error( 'interrupted_worker_confirmation_required', 'Confirm that the exact worker has stopped before abandoning its lease.', array( 'status' => 400 ) );
		}
		$result = new WP_Error( 'interrupted_lease_changed', 'The knowledge job, current source or interrupted worker has changed.', array( 'status' => 409 ) );
		$taken  = Lock::run(
			'publication-jobs',
			static function () use ( $job_id, $source, $recipe, $epoch, $worker_id, $apply, &$result ): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				$job      = $state['knowledge'] ?? array();
				if ( 'preparing' !== ( $job['status'] ?? '' ) || ( $job['job_id'] ?? null ) !== $job_id || ( $job['source_revision'] ?? null ) !== $source || $manifest['source_revision'] !== $source || ( $job['recipe_revision'] ?? null ) !== $recipe || ( $job['worker_id'] ?? null ) !== $worker_id || ! self::same_epoch( $job, array( 'activation_epoch' => $epoch ) ) ) {
					return;
				}
				// Explicit whitelist: the lease token is never selected for output or
				// used as worker credentials.
				$result = array(
					'applied'                   => $apply,
					'consumer'                  => 'knowledge',
					'job_id'                    => $job_id,
					'source_revision'           => $source,
					'recipe_revision'           => $recipe,
					'activation_epoch'          => $epoch,
					'worker_id'                 => $worker_id,
					'previous_status'           => 'preparing',
					'previous_lease_expires_at' => $job['lease_expires_at'] ?? 0,
					'target_status'             => 'failed',
					'target_lease_expires_at'   => 0,
					'removes_lease_token'       => true,
				);
				if ( $apply ) {
					$job['status']           = 'failed';
					$job['lease_expires_at'] = 0;
					unset( $job['lease_token'] );
					$state['knowledge'] = $job;
					update_option( self::OPTION, $state, false );
				}
			}
		);
		return $taken ? $result : new WP_Error( 'publication_busy', 'Preparation queue is busy.', array( 'status' => 503 ) );
	}

	/**
	 * Reactivate an installed older compiler during an explicitly verified rollback.
	 *
	 * Internal only: no REST route. The operator verifies the installed worker code
	 * before this compare-and-swap; unknown hashes cannot become rollback targets.
	 * This changes one preparation job, never Woo permission or serving facts.
	 *
	 * @param string $expected_current_recipe Compiler identity observed before rollback.
	 * @param string $target_recipe Previously used compiler verified on the build host.
	 * @return array<string,mixed>|WP_Error
	 */
	public function reactivate_recipe( string $expected_current_recipe, string $target_recipe ): array|WP_Error {
		if ( 1 !== preg_match( '/^[a-f0-9]{64}$/D', $expected_current_recipe ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $target_recipe ) ) {
			return new WP_Error( 'invalid_recipe_rollback', 'A rollback requires known compiler identities.', array( 'status' => 400 ) );
		}
		$result = new WP_Error( 'stale_recipe', 'The current compiler changed or the rollback target is unknown.', array( 'status' => 409 ) );
		$taken  = Lock::run(
			'publication-jobs',
			static function () use ( $expected_current_recipe, $target_recipe, &$result ): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				$job      = $state['knowledge'] ?? array();
				if ( ( $job['recipe_revision'] ?? '' ) !== $expected_current_recipe || ! in_array( $target_recipe, $job['superseded_recipes'] ?? array(), true ) ) {
					return;
				}
				$job                       = self::pending( 'knowledge', $manifest['source_revision'], $job, $target_recipe );
				$job['superseded_recipes'] = array_values( array_diff( $job['superseded_recipes'], array( $target_recipe ) ) );
				$state['knowledge']        = $job;
				update_option( self::OPTION, $state, false );
				$result = array(
					'accepted'        => true,
					'job_id'          => $job['job_id'],
					'source_revision' => $job['source_revision'],
					'recipe_revision' => $job['recipe_revision'],
				);
			}
		);
		return $taken ? $result : new WP_Error( 'publication_busy', 'Preparation queue is busy.', array( 'status' => 503 ) );
	}

	/**
	 * Confirm actual loaded state only while source and lease still match.
	 *
	 * @param array<string,mixed> $request Preparation receipt.
	 * @return array<string,mixed>|WP_Error
	 */
	public function acknowledge( array $request ): array|WP_Error {
		$result = new WP_Error( 'stale_job', 'The preparation lease or source has changed.', array( 'status' => 409 ) );
		Lock::run(
			'publication-jobs',
			static function () use ( $request, &$result ): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				foreach ( self::CONSUMERS as $consumer ) {
					$job    = $state[ $consumer ] ?? array();
					$recipe = (string) ( $job['recipe_revision'] ?? '' );
					if ( ( $job['job_id'] ?? '' ) !== ( $request['job_id'] ?? null ) || ! is_string( $request['lease_token'] ?? null ) || ! hash_equals( $job['lease_token'] ?? '', $request['lease_token'] ) || (int) ( $job['lease_expires_at'] ?? 0 ) <= time() || ( $request['source_revision'] ?? '' ) !== $manifest['source_revision'] || ( $job['source_revision'] ?? '' ) !== $manifest['source_revision'] || ( 'knowledge' === $consumer && ( $request['recipe_revision'] ?? '' ) !== $recipe ) || ( '' !== $recipe && ( ! self::same_epoch( $job, $request ) ) ) ) {
						continue;
					}
					if ( ! in_array( $request['status'] ?? '', array( 'ready', 'failed' ), true ) || ( 'ready' === $request['status'] && ( ! is_string( $request['loaded_revision'] ?? null ) || '' === $request['loaded_revision'] ) ) ) {
						$result = new WP_Error( 'invalid_job_ack', 'A ready job requires the actual loaded revision.', array( 'status' => 400 ) );
						return;
					}
					if ( 'ready' === $request['status'] && '' !== $recipe && ( ( $request['loaded_revision'] ?? '' ) !== $manifest['source_revision'] || ( $request['loaded_recipe_revision'] ?? '' ) !== $recipe || ! is_string( $request['index_version'] ?? null ) || 1 !== preg_match( '/^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/D', $request['index_version'] ) || ! is_string( $request['expected_serving_revision'] ?? null ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $request['expected_serving_revision'] ) || ( $request['serving_revision'] ?? '' ) !== $request['expected_serving_revision'] ) ) {
						$result = new WP_Error( 'invalid_job_ack', 'A recipe-aware receipt requires the actual loaded source, recipe and index generation.', array( 'status' => 400 ) );
						return;
					}
					$job['status']           = $request['status'];
					$job['error']            = sanitize_text_field( (string) ( $request['error'] ?? '' ) );
					$job['lease_expires_at'] = 0;
					unset( $job['lease_token'] );
					if ( 'ready' === $job['status'] ) {
						$job['loaded_revision'] = $request['loaded_revision'];
						$expected_products      = 'knowledge' === $consumer ? array_filter( $manifest['products'], static fn ( array $product ): bool => \Linker\Commerce\Products\EngineeringReference::PV_MODULE !== ( $product['engineering_role'] ?? '' ) ) : $manifest['products'];
						$expected               = array_column( $expected_products, 'product_revision', 'product_id' );
						$prepared               = $request['prepared_products'] ?? ( 'engineering' === $consumer ? $manifest['products'] : null );
						if ( ! is_array( $prepared ) || ! array_is_list( $prepared ) ) {
							$result = new WP_Error( 'invalid_job_ack', 'Knowledge acknowledgement requires actual prepared product revisions.', array( 'status' => 400 ) );
							return;
						}
						$loaded = array();
						foreach ( $prepared as $product ) {
							if ( ! is_array( $product ) || ! is_int( $product['product_id'] ?? null ) || ! isset( $expected[ $product['product_id'] ] ) || isset( $loaded[ $product['product_id'] ] ) || ( $product['product_revision'] ?? '' ) !== $expected[ $product['product_id'] ] ) {
								$result = new WP_Error( 'invalid_job_ack', 'Prepared products must match current source revisions.', array( 'status' => 400 ) );
								return;
							}
							$loaded[ $product['product_id'] ] = $product['product_revision'];
						}
						$job['loaded_products'] = $loaded;
						if ( count( $loaded ) !== count( $expected ) ) {
							$job['status'] = 'pending';
						}
						if ( 'knowledge' === $consumer ) {
							$diagnostics = self::unprepared_documents( $request['unprepared_documents'] ?? array(), $manifest );
							if ( $diagnostics instanceof WP_Error ) {
								$result = $diagnostics;
								return;
							}
							$job['unprepared_documents'] = $diagnostics;
							$job['preparation_complete'] = true === ( $request['preparation_complete'] ?? false ) && array() === $diagnostics && count( $loaded ) === count( $expected );
							if ( '' !== $recipe ) {
								$job['materialization_complete']  = true === ( $request['materialization_complete'] ?? false ) && ! in_array( 'document_unparsed', array_column( $diagnostics, 'reason' ), true );
								$job['index_version']             = $request['index_version'];
								$job['loaded_recipe_revision']    = $request['loaded_recipe_revision'];
								$job['expected_serving_revision'] = $request['expected_serving_revision'];
								$job['serving_revision']          = $request['serving_revision'];
								$job['loaded_activation_epoch']   = $request['activation_epoch'];
								$job['status']                    = $job['materialization_complete'] ? 'ready' : 'pending';
							}
							if ( ! $job['preparation_complete'] ) {
								if ( '' === $recipe ) {
									$job['status'] = 'pending';
								}
								$job['error'] = 'Some current document associations still lack proven passages.';
							}
						}
					}
					$state[ $consumer ] = $job;
					update_option( self::OPTION, $state, false );
					$result = array(
						'accepted' => true,
						'complete' => 'ready' === $job['status'],
					);
					return;
				}
			}
		);
		return $result;
	}

	/**
	 * A new job invalidates earlier leases but retains the actual serving receipt.
	 *
	 * @param string              $consumer Queue consumer.
	 * @param string              $source Current Woo source.
	 * @param array<string,mixed> $previous Previous serving receipt.
	 * @param string              $recipe Knowledge compiler identity, empty for legacy/engineering.
	 * @return array<string,mixed>
	 */
	private static function pending( string $consumer, string $source, array $previous, string $recipe ): array {
		$superseded = $previous['superseded_recipes'] ?? array();
		if ( '' !== ( $previous['recipe_revision'] ?? '' ) && ( $previous['recipe_revision'] ?? '' ) !== $recipe ) {
			$superseded[] = $previous['recipe_revision'];
		}
		$job = array(
			'job_id'           => hash( 'sha256', $consumer . '/' . $source . ( '' === $recipe ? '' : '/' . $recipe ) ),
			'consumer'         => $consumer,
			'source_revision'  => $source,
			'recipe_revision'  => $recipe,
			'status'           => 'pending',
			'loaded_products'  => $previous['loaded_products'] ?? array(),
			'lease_expires_at' => 0,
			'error'            => '',
		);
		if ( 'knowledge' === $consumer ) {
			// Only compiler hashes are retained: forgetting one could let an old
			// still-running worker silently replace the newer compiler requirement.
			$job['superseded_recipes']       = array_values( array_unique( $superseded ) );
			$job['preparation_complete']     = false;
			$job['materialization_complete'] = false;
			$job['activation_epoch']         = (int) ( $previous['activation_epoch'] ?? 0 );
			foreach ( array( 'loaded_revision', 'index_version', 'loaded_recipe_revision', 'expected_serving_revision', 'serving_revision', 'loaded_activation_epoch' ) as $key ) {
				if ( isset( $previous[ $key ] ) ) {
					$job[ $key ] = $previous[ $key ];
				}
			}
		}
		return $job;
	}

	/**
	 * Reconcile the actual process with the receipt, without granting any readiness.
	 *
	 * @param array<string,mixed> $job Last acknowledged generation.
	 * @param array<string,mixed> $loaded Actual serving process response.
	 */
	private static function matches_loaded( array $job, array $loaded ): bool {
		foreach ( array(
			'source_revision'           => 'loaded_revision',
			'recipe_revision'           => 'loaded_recipe_revision',
			'expected_serving_revision' => 'expected_serving_revision',
			'serving_revision'          => 'serving_revision',
			'index_version'             => 'index_version',
			'activation_epoch'          => 'loaded_activation_epoch',
		) as $actual => $stored ) {
			if ( ! array_key_exists( $stored, $job ) || ( $loaded[ $actual ] ?? null ) !== $job[ $stored ] ) {
				return false;
			}
		}
		$products = $loaded['products'] ?? null;
		if ( ! is_array( $products ) || ! array_is_list( $products ) ) {
			return false;
		}
		$actual = array();
		foreach ( $products as $product ) {
			if ( ! is_array( $product ) || ! is_int( $product['product_id'] ?? null ) || ! is_string( $product['product_revision'] ?? null ) || isset( $actual[ $product['product_id'] ] ) ) {
				return false;
			}
			$actual[ $product['product_id'] ] = $product['product_revision'];
		}
		$expected = $job['loaded_products'] ?? array();
		ksort( $actual );
		ksort( $expected );
		return $actual === $expected;
	}

	/**
	 * Only the exact positive native lease epoch can activate or acknowledge.
	 *
	 * @param array<string,mixed> $job Current queue state.
	 * @param array<string,mixed> $request Leased operation.
	 */
	private static function same_epoch( array $job, array $request ): bool {
		return isset( $request['activation_epoch'], $job['activation_epoch'] ) && is_int( $request['activation_epoch'] ) && 0 < $request['activation_epoch'] && $request['activation_epoch'] === $job['activation_epoch'];
	}

	/**
	 * Retain bounded source identities for missing passages, without source text.
	 *
	 * @param mixed               $rows Worker diagnostics.
	 * @param array<string,mixed> $manifest Current source read.
	 * @return list<array{document_id:string,product_id:int,reason:string}>|WP_Error
	 */
	private static function unprepared_documents( mixed $rows, array $manifest ): array|WP_Error {
		if ( ! is_array( $rows ) || ! array_is_list( $rows ) ) {
			return new WP_Error( 'invalid_job_ack', 'Unprepared documents must be a list of current source associations.', array( 'status' => 400 ) );
		}
		$documents = array_column( $manifest['documents'], null, 'document_id' );
		$result    = array();
		foreach ( $rows as $row ) {
			$id = is_array( $row ) && is_string( $row['document_id'] ?? null ) ? $row['document_id'] : '';
			if ( ! is_array( $row ) || ! is_int( $row['product_id'] ?? null ) || ! isset( $documents[ $id ] ) || ! in_array( $row['product_id'], $documents[ $id ]['product_ids'], true ) || ! in_array( $row['reason'] ?? null, array( 'no_proven_passage', 'document_unparsed' ), true ) ) {
				return new WP_Error( 'invalid_job_ack', 'Unprepared documents must name current document/product associations.', array( 'status' => 400 ) );
			}
			$result[ $id . '/' . $row['product_id'] ] = array(
				'document_id' => $id,
				'product_id'  => $row['product_id'],
				'reason'      => $row['reason'],
			);
		}
		return array_values( $result );
	}
}
