<?php
/**
 * Persistent global review capacity, independent of normal verified admission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Lock;
use WC_Order;
use WP_Error;

/** Native options store only bounded HMAC references; Woo owns all content. */
final class IntakeStore {
	public const OPTION = 'linker_public_review_capacity';
	// Initial operating allocation and separate lanes: docs/specs/542-safe-intake.md.
	public const CAPACITY = array(
		'verification' => 128,
		'campaign'     => 3,
		'individual'   => 16,
	);

	/**
	 * Serialize capacity decisions and first native save across DB connections.
	 *
	 * @param callable(array<string,mixed>&):(WC_Order|WP_Error|array<string,mixed>) $work Native work.
	 * @return WC_Order|WP_Error|array<string,mixed>
	 */
	public static function edit( callable $work ): WC_Order|WP_Error|array {
		$result = new WP_Error( 'linker_intake_busy', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
		Lock::run(
			'intake-capacity',
			static function () use ( $work, &$result ): void {
				wp_cache_delete( self::OPTION, 'options' );
				$state = get_option(
					self::OPTION,
					array(
						'entries'        => array(),
						'campaign_count' => 0,
					)
				);
				if ( ! is_array( $state ) || ! is_array( $state['entries'] ?? null ) || count( $state['entries'] ) > array_sum( self::CAPACITY ) ) {
					return;
				}
				try {
					$result = $work( $state );
				} catch ( \Throwable $error ) {
					// Native checkout may have started an unfinished transaction.
					wc_transaction_query( 'rollback' );
					$result = new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
				}
			}
		);
		return $result;
	}

	/**
	 * Verify the durable native option before allowing side effects.
	 *
	 * @param array<string,mixed> $state Bounded private registry.
	 * @throws \RuntimeException Storage/readback failure.
	 */
	public static function save( array $state ): void {
		update_option( self::OPTION, $state, false );
		wp_cache_delete( self::OPTION, 'options' );
		if ( get_option( self::OPTION ) !== $state ) {
			throw new \RuntimeException( 'intake_capacity_readback_failed' );
		}
	}

	/**
	 * Native erasure also removes retry associations in the review registry.
	 *
	 * @throws \RuntimeException Busy storage makes erasure retryable.
	 *
	 * @param WC_Order $order Anonymized native order.
	 */
	public static function forget( WC_Order $order ): void {
		$order->delete_meta_data( Intake::META );
		$order->delete_meta_data( Intake::LANE_META );
		$order->save_meta_data();
		$result = self::edit(
			static function ( array &$state ) use ( $order ): array {
				foreach ( $state['entries'] as $id => $entry ) {
					if ( $order->get_id() === (int) ( $entry['order'] ?? 0 ) || $id === $order->get_meta( BusinessRecord::REQUEST ) ) {
						unset( $state['entries'][ $id ] );
					}
				}
				self::save( $state );
				return array();
			}
		);
		if ( is_wp_error( $result ) ) {
			throw new \RuntimeException( 'intake_erasure_busy' );
		}
	}
	/**
	 * Verified-email privacy includes interrupted reservations with no native ID.
	 * Erasure strips links without refunding unresolved capacity.
	 *
	 * @param string[] $owners Trusted requester HMAC associations.
	 * @param bool     $erase Whether to strip requester associations.
	 * @return array<string,mixed>|WP_Error
	 */
	public static function privacy( array $owners, bool $erase ): array|WP_Error {
		$result = self::edit(
			static function ( array &$state ) use ( $owners, $erase ): array {
				$data = array();
				foreach ( $state['entries'] as $id => $entry ) {
					if ( array() === array_intersect( $owners, $entry['owners'] ?? array() ) ) {
						continue;
					}
					$data[] = array(
						'id'    => $id,
						'lane'  => $entry['lane'],
						'order' => $entry['order'],
						'at'    => $entry['at'],
					);
					if ( $erase ) {
						$state['entries'][ $id ]['owners']      = array();
						$state['entries'][ $id ]['fingerprint'] = '';
						$state['entries'][ $id ]['binding']     = '';
						$state['entries'][ $id ]['erased']      = true;
					}
				}
				if ( $erase && array() !== $data ) {
					self::save( $state );
				}
				return array(
					'data'    => $data,
					'removed' => $erase ? count( $data ) : 0,
				);
			}
		);
		return $result instanceof WP_Error || is_array( $result ) ? $result : new WP_Error( 'intake_privacy_unavailable' );
	}
}
