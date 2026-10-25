<?php
/** Audited one-time disposition of the incident's exact historical native inquiries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Inquiry\Assessment\CurrentSource;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Mail\Capacity;
use WC_Order;
use WP_Error;

/** No automatic spam verdict: an authenticated employee must execute the manifest. */
final class BusinessDisposition {
	public const META   = '_linker_business_disposition';
	public const REASON = 'confirmed-transfer-fredmer-20261022';
	// The independently verified historical set has exactly 87 entries; #568 evidence.
	public const MAXIMUM          = 87;
	public const EXCLUDED_CONTROL = 8037;

	/**
	 * Exact immutable original message, not an email/domain heuristic.
	 *
	 * @param WC_Order $order Native record.
	 */
	public static function body( WC_Order $order ): string {
		$data    = Queue::data( $order );
		$message = $data['snapshot']['submission']['message'] ?? null;
		return is_string( $message ) && $message === $order->get_customer_note() ? $message : '';
	}

	/**
	 * Reader verifies employee provenance, native private audit, HMAC and full original body.
	 *
	 * @param WC_Order $order Native record, freshly loaded under the capacity mutex.
	 */
	public static function processed( WC_Order $order ): bool {
		$order = CurrentSource::order( $order->get_id() );
		if ( ! $order instanceof WC_Order ) {
			return false; }
		$order->read_meta_data( true );
		$record = $order->get_meta( self::META );
		if ( is_array( $record ) && is_int( $record['by'] ?? null ) ) {
			clean_user_cache( $record['by'] );
			wp_cache_delete( $record['by'], 'user_meta' );
		}
		if ( ! is_array( $record ) || 1 !== ( $record['v'] ?? null ) || self::REASON !== ( $record['reason'] ?? null ) || ! is_int( $record['by'] ?? null ) || ! user_can( $record['by'], 'manage_woocommerce' ) || ! is_int( $record['at'] ?? null ) || $record['at'] < 1 || ! is_string( $record['operation'] ?? null ) || ! wp_is_uuid( $record['operation'], 4 ) || ! is_int( $record['note'] ?? null ) || ! is_string( $record['body'] ?? null ) || ! is_string( $record['mac'] ?? null ) ) {
			return false;
		}
		$unsigned = $record;
		unset( $unsigned['mac'] );
		if ( ! hash_equals( $record['mac'], self::signature( $order->get_id(), $unsigned ) ) || ! hash_equals( $record['body'], hash( 'sha256', self::body( $order ) ) ) ) {
			return false;
		}
		clean_comment_cache( $record['note'] );
		wp_cache_delete( $record['note'], 'comment_meta' );
		$note    = get_comment( $record['note'] );
		$content = $unsigned;
		unset( $content['note'] );
		return $note instanceof \WP_Comment && (int) $note->comment_post_ID === $order->get_id() && 'order_note' === $note->comment_type && (int) $note->user_id === $record['by'] && (string) wp_json_encode( $content ) === $note->comment_content && in_array( get_comment_meta( $record['note'], 'is_customer_note', true ), array( '', '0' ), true ) && get_comment_meta( $record['note'], self::META, true ) === $unsigned;
	}

	/**
	 * A restored old registry must rediscover native audited sources, never forget debt.
	 * Only this incident's at-most-87 associations are added, with no content duplication.
	 *
	 * @param array<string,mixed> $state Locked authoritative capacity state.
	 * @throws \RuntimeException Invalid or unreadable authoritative historical association.
	 */
	public static function reconcile( array &$state ): void {
		if ( ! isset( $state['business_dispositions'] ) ) {
			global $wpdb;
			$wpdb->flush();
			// phpcs:disable WordPress.DB.SlowDBQuery -- Fixed at-most-88 native audit discovery, not public body search.
			if ( \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ) {
				$ids = wc_get_orders(
					array(
						'limit'      => self::MAXIMUM + 1,
						'return'     => 'ids',
						'meta_query' => array(
							array(
								'key'     => self::META,
								'compare' => 'EXISTS',
							),
						),
					)
				); // phpcs:ignore WordPress.DB.SlowDBQuery -- Fixed incident audit discovery, only after absent/old registry restore.
			} else {
				$ids = get_posts(
					array(
						'post_type'      => 'shop_order',
						'post_status'    => 'any',
						'posts_per_page' => self::MAXIMUM + 1,
						'fields'         => 'ids',
						'meta_key'       => self::META,
					)
				); // phpcs:ignore WordPress.DB.SlowDBQuery -- Same native CPT association discovery.
			}
			// phpcs:enable
			$handle = $wpdb->__get( 'dbh' );
			// A swallowed native query error never proves an empty historical audit.
			if ( ! is_array( $ids ) || '' !== $wpdb->last_error || ( $handle instanceof \mysqli && 0 !== $handle->errno ) ) {
				throw new \RuntimeException( 'historical_disposition_history_unreadable' );
			}
			$state['business_dispositions'] = array();
			foreach ( $ids as $id ) {
				if ( ! is_int( $id ) || $id < 1 ) {
					throw new \RuntimeException( 'historical_disposition_history_invalid' );
				}
				$state['business_dispositions'][ $id ] = true;
			}
		}
		if ( ! is_array( $state['business_dispositions'] ) || count( $state['business_dispositions'] ) > self::MAXIMUM ) {
			throw new \RuntimeException( 'historical_disposition_index_invalid' );
		}
		foreach ( $state['business_dispositions'] as $id => $present ) {
			if ( ! is_int( $id ) || true !== $present ) {
				throw new \RuntimeException( 'historical_disposition_index_invalid' );
			}
			$order = CurrentSource::order( $id );
			if ( ! $order instanceof WC_Order ) {
				if ( BusinessCapacity::source_missing( $id ) ) {
					continue; }
				throw new \RuntimeException( 'historical_disposition_source_unreadable' );
			}
			$order->read_meta_data( true );
			$processed = self::processed( $order );
			foreach ( $state['business'] as $key => $entry ) {
				if ( $entry['order'] === $id && $processed ) {
					unset( $state['business'][ $key ] );
				}
			}
			if ( ! $processed && in_array( $order->get_status(), array( 'pending', 'on-hold', Statuses::RECEIVED ), true ) ) {
				$state['business'][ 'legacy-' . $id ] = array(
					'pool'  => 'ordinary',
					'order' => $id,
					'bytes' => BusinessCapacity::bytes( $order ),
				);
			}
		}
	}

	/**
	 * One short native transaction per entry, not a falsely atomic whole batch.
	 *
	 * @param int    $id Manifest native inquiry.
	 * @param string $body_hash Verified exact body SHA256.
	 * @param string $operation Server/operator-owned batch UUID.
	 * @param bool   $rollback Remove only this batch's own exact disposition.
	 * @return array<string,mixed>|WP_Error Native confirmed result; failures are explicit.
	 */
	public static function run( int $id, string $body_hash, string $operation, bool $rollback = false ): array|WP_Error {
		if ( ! current_user_can( 'manage_woocommerce' ) || self::EXCLUDED_CONTROL === $id || ! wp_is_uuid( $operation, 4 ) || 1 !== preg_match( '/^[a-f0-9]{64}$/', $body_hash ) ) {
			return new WP_Error( 'disposition_forbidden' );
		}
		$result = new WP_Error( 'disposition_busy' );
		try {
			Lock::run(
				'historical-disposition-' . $id,
				static function () use ( $id, $body_hash, $operation, $rollback, &$result ): void {
					$result = IntakeStore::edit(
						static function ( array &$state ) use ( $id, $body_hash, $operation, $rollback ): array|WP_Error {
							if ( Capacity::transaction_active() ) {
								return new WP_Error( 'disposition_outer_transaction' );
							}
							$transaction = new NativeTransaction();
							try {
								$actor = get_current_user_id();
								clean_user_cache( $actor );
								wp_cache_delete( $actor, 'user_meta' );
								if ( ! user_can( $actor, 'manage_woocommerce' ) ) {
									throw new \RuntimeException( 'disposition_actor_changed' ); }
								$order = CurrentSource::order( $id );
								if ( ! $order instanceof WC_Order ) {
									throw new \RuntimeException( 'disposition_missing_source' );
								}
								$order->read_meta_data( true );
								$body = self::body( $order );
								if ( ! hash_equals( $body_hash, hash( 'sha256', $body ) ) || ! Campaign::matches( $body ) || $order->get_meta( Intake::META ) || $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) || ! $order->has_status( Statuses::RECEIVED ) || ! in_array( $order->get_meta( '_linker_inquiry_source' ), array( 'contact', 'proforma' ), true ) ) {
									throw new \RuntimeException( 'disposition_source_changed' );
								}
								BusinessCapacity::synchronize( $state );
								$old = $order->get_meta( self::META );
								if ( ! $rollback && is_array( $old ) && ( $old['operation'] ?? '' ) === $operation && self::processed( $order ) ) {
									$transaction->rollback();
									return array(
										'order'     => $id,
										'status'    => 'already_applied',
										'operation' => $operation,
										'note'      => $old['note'],
									);
								}
								if ( $rollback ) {
									if ( ! is_array( $old ) || ( $old['operation'] ?? '' ) !== $operation || ! self::processed( $order ) ) {
										throw new \RuntimeException( 'disposition_rollback_changed' );
									}
									$order->delete_meta_data( self::META );
									$order->save_meta_data();
									if ( ! wp_delete_comment( $old['note'], true ) ) {
										throw new \RuntimeException( 'disposition_rollback_note_failed' );
									}
									unset( $state['business_dispositions'][ $id ] );
									$state['business'][ 'legacy-' . $id ] = array(
										'pool'  => 'ordinary',
										'order' => $id,
										'bytes' => BusinessCapacity::bytes( $order ),
									);
								} else {
									if ( $old || ( ! isset( $state['business_dispositions'][ $id ] ) && count( $state['business_dispositions'] ) >= self::MAXIMUM ) ) {
										throw new \RuntimeException( 'disposition_existing_or_full' );
									}
									$record = array(
										'v'         => 1,
										'reason'    => self::REASON,
										'by'        => get_current_user_id(),
										'at'        => time(),
										'operation' => $operation,
										'body'      => $body_hash,
									);
									$note   = $order->add_order_note( (string) wp_json_encode( $record ), 0, true );
									if ( $note < 1 || ! wp_update_comment(
										array(
											'comment_ID' => $note,
											'user_id'    => get_current_user_id(),
										)
									) ) {
										throw new \RuntimeException( 'disposition_note_failed' );
									}
									$record['note'] = $note;
									if ( ! add_comment_meta( $note, self::META, $record, true ) ) {
										throw new \RuntimeException( 'disposition_audit_failed' );
									}
									$record['mac'] = self::signature( $id, $record );
									StructuredMeta::update( $order, self::META, $record );
									$order->save_meta_data();
									if ( ! self::processed( $order ) ) {
										throw new \RuntimeException( 'disposition_readback_failed' );
									}
									$state['business_dispositions'][ $id ] = true;
									self::reconcile( $state );
								}
								IntakeStore::save( $state );
								$order->read_meta_data( true );
								if ( $rollback && ( $order->get_meta( self::META ) || get_comment( $old['note'] ) ) ) {
									throw new \RuntimeException( 'disposition_rollback_readback_failed' );
								}
								$transaction->commit();
								return array(
									'order'     => $id,
									'status'    => $rollback ? 'rolled_back' : 'applied',
									'operation' => $operation,
									'note'      => $rollback ? $old['note'] : $note,
								);
							} catch ( \Throwable $error ) {
								try {
									$transaction->rollback();
								} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- Unknown original commit is not compensated on a new connection.
								}
								return new WP_Error( 'disposition_unconfirmed' );
							}
						},
						1
					);
				},
				1,
				true
			);
		} catch ( \Throwable $error ) {
			return new WP_Error( 'disposition_unconfirmed' );
		}
		return is_array( $result ) || $result instanceof WP_Error ? $result : new WP_Error( 'disposition_unconfirmed' );
	}

	/**
	 * Sign only the fixed private native audit.
	 *
	 * @param int                 $id Native source.
	 * @param array<string,mixed> $record Fixed audit fields.
	 */
	private static function signature( int $id, array $record ): string {
		return hash_hmac( 'sha256', $id . '|' . maybe_serialize( $record ), wp_salt( 'nonce' ) );
	}
}
