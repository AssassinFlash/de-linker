<?php
/**
 * New staff evidence in WooCommerce's native privacy lifecycle.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;

/** Scope: frozen customer evidence and staff review, not historical mail copies. */
final class EvidencePrivacy {

	/** Register on Woo's own order export and approved erasure path. */
	public function register(): void {
		add_filter( 'woocommerce_privacy_export_order_personal_data', array( $this, 'export' ), 10, 2 );
		add_action( 'woocommerce_privacy_before_remove_order_personal_data', array( $this, 'erase' ) );
	}

	/**
	 * Export new evidence and correction history for this order.
	 *
	 * @param list<array{name: string, value: mixed}> $data Native export rows.
	 * @param WC_Order                                $order Order selected by Woo's requester.
	 * @return list<array{name: string, value: mixed}>
	 */
	public function export( array $data, WC_Order $order ): array {
		$evidence = $order->get_meta( CustomerEvidence::META );
		$history  = Reviews::history( $order );
		$override = $order->get_meta( Admin::OVERRIDE );
		if ( is_array( $evidence ) || array() !== $history || is_array( $override ) ) {
			$data[] = array(
				'name'  => __( 'Customer evidence and staff review', 'linker-commerce' ),
				'value' => (string) wp_json_encode(
					array(
						'evidence'   => $evidence,
						'correction' => $override,
						'history'    => $history,
					),
					JSON_UNESCAPED_UNICODE
				),
			);
		}
		return $data;
	}

	/**
	 * Serialize erasure with staff writes; never report a busy removal as complete.
	 * The existing assessment/provider snapshot and Outbox have separate ownership.
	 *
	 * @param WC_Order $order Native erasure target.
	 * @throws \RuntimeException Busy/write failure makes erasure visibly retryable.
	 */
	public function erase( WC_Order $order ): void {
		$done = Lock::run(
			'review-' . $order->get_id(),
			static function () use ( $order ): void {
				$order->read_meta_data( true );
				$notes = Reviews::history( $order );
				wc_transaction_query( 'start' );
				try {
					foreach ( $notes as $note ) {
						delete_comment_meta( (int) $note['id'], Reviews::EVENT );
						if ( metadata_exists( 'comment', (int) $note['id'], Reviews::EVENT ) ) {
							throw new \RuntimeException( 'review_erasure_failed' );
						}
					}
					foreach ( array( CustomerEvidence::META, Reviews::META, Admin::OVERRIDE ) as $key ) {
						$order->delete_meta_data( $key );
					}
					$order->update_meta_data( Reviews::ERASED, 'yes' );
					$order->save_meta_data();
					$order->read_meta_data( true );
					if ( $order->get_meta( CustomerEvidence::META ) || $order->get_meta( Reviews::META ) || $order->get_meta( Admin::OVERRIDE ) || 'yes' !== $order->get_meta( Reviews::ERASED ) ) {
						throw new \RuntimeException( 'review_erasure_failed' );
					}
					wc_transaction_query( 'commit' );
				} catch ( \Throwable $error ) {
					wc_transaction_query( 'rollback' );
					foreach ( $notes as $note ) {
						wp_cache_delete( (int) $note['id'], 'comment_meta' );
					}
					$order->read_meta_data( true );
					throw new \RuntimeException( 'customer_evidence_erasure_failed' );
				}
			}
		);
		if ( ! $done ) {
			throw new \RuntimeException( 'customer_evidence_review_busy' );
		}
	}
}
