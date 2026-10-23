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
						$loaded             = $state[ $consumer ]['loaded_products'] ?? array();
						$state[ $consumer ] = array(
							'job_id'           => hash( 'sha256', $consumer . '/' . $manifest['source_revision'] ),
							'consumer'         => $consumer,
							'source_revision'  => $manifest['source_revision'],
							'status'           => 'pending',
							'loaded_products'  => $loaded,
							'lease_expires_at' => 0,
							'error'            => '',
						);
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
	 * @param string $consumer Consumer identity.
	 * @param string $worker_id Worker identity.
	 * @param int    $lease_seconds Requested lease, bounded to WordPress one day.
	 * @return array<string,mixed>|WP_Error
	 */
	public function claim( string $consumer, string $worker_id, int $lease_seconds ): array|WP_Error {
		if ( ! in_array( $consumer, self::CONSUMERS, true ) || '' === $worker_id || $lease_seconds < 1 || $lease_seconds > DAY_IN_SECONDS ) {
			return new WP_Error( 'invalid_job_request', 'Invalid consumer, worker or lease.', array( 'status' => 400 ) );
		}
		$this->reconcile();
		$result = array( 'job' => null );
		$taken  = Lock::run(
			'publication-jobs',
			static function () use ( $consumer, $worker_id, $lease_seconds, &$result ): void {
				$manifest = Publication::manifest();
				$state    = get_option( self::OPTION, array() );
				$job      = $state[ $consumer ] ?? array();
				if ( 'ready' === ( $job['status'] ?? '' ) || (int) ( $job['lease_expires_at'] ?? 0 ) > time() || ( $job['source_revision'] ?? '' ) !== $manifest['source_revision'] ) {
					return;
				}
				$job['lease_token']      = wp_generate_password( 64, false );
				$job['lease_expires_at'] = time() + $lease_seconds;
				$job['worker_id']        = $worker_id;
				$job['status']           = 'preparing';
				$state[ $consumer ]      = $job;
				update_option( self::OPTION, $state, false );
				unset( $job['loaded_products'], $job['error'], $job['worker_id'], $job['status'] );
				$job['manifest'] = $manifest;
				$result['job']   = $job;
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
					$job = $state[ $consumer ] ?? array();
					if ( ( $job['job_id'] ?? '' ) !== ( $request['job_id'] ?? null ) || ! is_string( $request['lease_token'] ?? null ) || ! hash_equals( $job['lease_token'] ?? '', $request['lease_token'] ) || (int) ( $job['lease_expires_at'] ?? 0 ) <= time() || ( $request['source_revision'] ?? '' ) !== $manifest['source_revision'] || ( $job['source_revision'] ?? '' ) !== $manifest['source_revision'] ) {
						continue;
					}
					if ( ! in_array( $request['status'] ?? '', array( 'ready', 'failed' ), true ) || ( 'ready' === $request['status'] && ( ! is_string( $request['loaded_revision'] ?? null ) || '' === $request['loaded_revision'] ) ) ) {
						$result = new WP_Error( 'invalid_job_ack', 'A ready job requires the actual loaded revision.', array( 'status' => 400 ) );
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
							if ( ! is_array( $product ) || ! is_int( $product['product_id'] ?? null ) || ! isset( $expected[ $product['product_id'] ] ) || ( $product['product_revision'] ?? '' ) !== $expected[ $product['product_id'] ] ) {
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
							if ( ! $job['preparation_complete'] ) {
								$job['status'] = 'pending';
								$job['error']  = 'Some current document associations still lack proven passages.';
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
