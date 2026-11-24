<?php
/**
 * Persistent normal inquiry occupancy, before Woo's first save (#568).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Settings\Options;
use Linker\Commerce\Inquiry\Statuses;
use WC_Order;
use WP_Error;

/** The review registry's native lock/CAS also serializes independent normal pools. */
final class BusinessCapacity {
	public const KEY = '_linker_business_capacity_key';

	/** Native completion/deletion, rather than elapsed time or SMTP, releases space. */
	public function register(): void {
		add_action( 'woocommerce_order_status_changed', array( $this, 'status' ), 30, 4 );
		add_action( 'woocommerce_delete_order', array( $this, 'deleted' ) );
	}

	/**
	 * Verify actual native status after persistence. Mail delivery never calls this.
	 *
	 * @param int      $id Native inquiry.
	 * @param string   $from Previous status.
	 * @param string   $to New status.
	 * @param WC_Order $order Native updated object.
	 */
	public function status( int $id, string $from, string $to, WC_Order $order ): void {
		unset( $from, $order );
		if ( in_array( $to, array( Statuses::QUOTATION, 'completed', 'cancelled' ), true ) ) {
			$this->release( $id, '', $to );
		}
	}

	/**
	 * Actual native deletion frees removed storage; erasing PII alone does not.
	 *
	 * @param int $id Deleted inquiry.
	 */
	public function deleted( int $id ): void {
		$this->release( $id );
	}

	/**
	 * Current business occupancy for the operations digest: unhandled inquiries
	 * and their logical bytes, from the same locked registry the admission bound
	 * checks.
	 *
	 * Read-only on an initialised registry, which production has been since
	 * 2026-10-22 (both keys are present). The very first call on a site without
	 * the registry runs the same native history read and disposition
	 * reconciliation as admission itself, and that one call persists the
	 * initialised state; it never deletes, charges or releases anything.
	 *
	 * @return array{unhandled: int, bytes: int}|WP_Error
	 */
	public static function occupancy(): array|WP_Error {
		$result = IntakeStore::edit(
			static function ( array &$state ): array {
				self::initialize( $state );
				$entries = is_array( $state['business'] ?? null ) ? $state['business'] : array();
				$bytes   = 0;
				foreach ( $entries as $entry ) {
					if ( is_array( $entry ) && is_int( $entry['bytes'] ?? null ) ) {
						$bytes += $entry['bytes'];
					}
				}
				return array(
					'unhandled' => count( $entries ),
					'bytes'     => $bytes,
				);
			},
			0
		);
		if ( ! is_array( $result ) || ! is_int( $result['unhandled'] ?? null ) || ! is_int( $result['bytes'] ?? null ) ) {
			return new WP_Error( 'business_occupancy_unreadable', 'The unhandled inquiry envelope could not be read.' );
		}
		return array(
			'unhandled' => $result['unhandled'],
			'bytes'     => $result['bytes'],
		);
	}

	/**
	 * Frozen business logical data, not a claim about InnoDB physical allocation.
	 *
	 * @param WC_Order $order Current native data.
	 * @throws CapacityFull The complete native payload cannot be encoded.
	 */
	public static function bytes( WC_Order $order ): int {
		$data = self::native_data( $order );
		$json = wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		if ( ! is_string( $json ) ) {
			throw new CapacityFull( self::problem() ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Structured native error, never echoed here.
		}
		return strlen( $json );
	}

	/**
	 * Read current native getters, not WC_Meta_Data::jsonSerialize's old snapshot.
	 * Metadata pending changes must count before Woo calls apply_changes().
	 *
	 * @param \WC_Data $native Native prepared order or one of its complete items.
	 * @return array<string,mixed> Logical business data without native row IDs.
	 */
	private static function native_data( \WC_Data $native ): array {
		$data = $native->get_data();
		unset( $data['id'], $data['order_id'], $data['number'], $data['date_created'], $data['date_modified'] );
		foreach ( $data as $key => $value ) {
			if ( 'meta_data' === $key ) {
				$data[ $key ] = array();
				foreach ( $native->get_meta_data() as $meta ) {
					if ( self::KEY !== $meta->key ) {
						$data[ $key ][] = array(
							'key'   => $meta->key,
							'value' => $meta->value,
						);
					}
				}
			} elseif ( in_array( $key, array( 'line_items', 'tax_lines', 'shipping_lines', 'fee_lines', 'coupon_lines' ), true ) && is_array( $value ) ) {
				$data[ $key ] = array();
				foreach ( $value as $item ) {
					if ( $item instanceof \WC_Data ) {
						$data[ $key ][] = self::native_data( $item );
					}
				}
			} elseif ( $native instanceof WC_Order && in_array( $key, array( 'billing', 'shipping' ), true ) ) {
				$data[ $key ] = $native->get_address( $key );
			} elseif ( is_callable( array( $native, 'get_' . $key ) ) ) {
				$data[ $key ] = $native->{ 'get_' . $key }( 'edit' );
			}
		}
		return $data;
	}

	/**
	 * Initialize from native open inquiries; preserve historical excess as debt.
	 * Existing review lanes remain in their own unchanged registry.
	 *
	 * @param array<string,mixed> $state Locked native registry.
	 * @throws \RuntimeException Invalid or unreadable authoritative native history.
	 */
	private static function initialize( array &$state ): void {
		if ( isset( $state['business'] ) ) {
			if ( ! is_array( $state['business'] ) ) {
				throw new \RuntimeException( 'business_capacity_invalid_state' );
			}
			foreach ( $state['business'] as $entry ) {
				if ( ! is_array( $entry ) || ! in_array( $entry['pool'] ?? '', array( 'ordinary', 'approved' ), true ) || ! is_int( $entry['bytes'] ?? null ) || $entry['bytes'] < 1 || ! is_int( $entry['order'] ?? null ) || $entry['order'] < 0 ) {
					throw new \RuntimeException( 'business_capacity_invalid_entry' );
				}
			}
			BusinessDisposition::reconcile( $state );
			return;
		}
		$state['business'] = array();
		$page              = 1;
		do {
			global $wpdb;
			$wpdb->flush();
			$orders = wc_get_orders(
				array(
					'status'  => array( 'pending', 'on-hold', Statuses::RECEIVED ),
					'limit'   => 100,
					'page'    => $page,
					'orderby' => 'ID',
					'order'   => 'ASC',
				)
			);
			$handle = $wpdb->__get( 'dbh' );
			// Woo HPOS may catch a native SQL exception and return an empty array.
			if ( ! is_array( $orders ) || '' !== $wpdb->last_error || ( $handle instanceof \mysqli && 0 !== $handle->errno ) ) {
				throw new \RuntimeException( 'business_capacity_history_unreadable' );
			}
			foreach ( $orders as $candidate ) {
				$order = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $candidate->get_id() );
				if ( ! $order instanceof WC_Order ) {
					throw new \RuntimeException( 'business_capacity_source_unreadable' ); }
				if ( in_array( $order->get_meta( '_linker_inquiry_source' ), array( 'contact', 'inquiry' ), true ) && ! $order->get_meta( Intake::META ) ) {
					$key                       = (string) $order->get_meta( self::KEY );
					$key                       = '' !== $key ? $key : 'legacy-' . $order->get_id();
					$state['business'][ $key ] = array(
						'pool'  => 'ordinary',
						'order' => $order->get_id(),
						'bytes' => self::bytes( $order ),
					);
				}
			}
			$count = count( $orders );
			++$page;
		} while ( 100 === $count );
		BusinessDisposition::reconcile( $state );
		IntakeStore::save( $state );
	}

	/**
	 * Native staff migration uses the same historical reader under IntakeStore.
	 *
	 * @param array<string,mixed> $state Locked native registry.
	 */
	public static function synchronize( array &$state ): void {
		self::initialize( $state );
	}

	/**
	 * Release only a proven processed/deleted native source, never a timer.
	 *
	 * @param int         $id Native source.
	 * @param string      $key Trusted first-save association.
	 * @param string|null $status Exact processed status that must still exist under the mutex.
	 */
	private function release( int $id, string $key = '', ?string $status = null ): void {
		IntakeStore::edit(
			static function ( array &$state ) use ( $id, $key, $status ): array {
				if ( null === $status ) {
					if ( ! self::source_missing( $id ) ) {
						return array(); }
					unset( $state['business_dispositions'][ $id ] );
				} else {
					$fresh = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $id );
					$actor = get_current_user_id();
					clean_user_cache( $actor );
					wp_cache_delete( $actor, 'user_meta' );
					if ( ! $fresh instanceof WC_Order || ! $fresh->has_status( $status ) || ! user_can( $actor, 'manage_woocommerce' ) ) {
						return array(); }
				}
				foreach ( $state['business'] ?? array() as $token => $entry ) {
					if ( (int) $entry['order'] === $id || ( '' !== $key && $token === $key ) ) {
						unset( $state['business'][ $token ] );
					}
				}
				IntakeStore::save( $state );
				return array();
			},
			1
		);
	}

	/** Confirm native absence separately from an unreadable cached business object.
	 *
	 * @param int $id Source whose native deletion may release retained debt.
	 * @throws \RuntimeException A failed read never proves deletion.
	 */
	public static function source_missing( int $id ): bool {
		global $wpdb;
		$hpos   = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled();
		$table  = $hpos ? $wpdb->prefix . 'wc_orders' : $wpdb->posts;
		$column = $hpos ? 'id' : 'ID';
		$wpdb->flush();
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Exact source existence under the capacity owner's connection fence, never object reconstruction.
		$found = $wpdb->get_var( $wpdb->prepare( 'SELECT %i FROM %i WHERE %i=%d', $column, $table, $column, $id ) );
		if ( '' !== $wpdb->last_error ) {
			throw new \RuntimeException( 'business_source_presence_unreadable' ); }
		return null === $found;
	}

	/** Accurate native refusal: no new order number or receipt claim. */
	private static function problem(): WP_Error {
		return new WP_Error( 'linker_business_capacity', self::message(), array( 'status' => 503 ) );
	}

	/** The ordinary form and tool consumers share the honest unsaved result. */
	public static function message(): string {
		/* translators: %s: public team email address. */
		return sprintf( __( 'Your request has not been saved. We cannot accept new requests on this website right now. Your entries and solution draft are still here. Please try again later or email %s.', 'linker-commerce' ), ( new Options() )->team_mailbox() );
	}
}
