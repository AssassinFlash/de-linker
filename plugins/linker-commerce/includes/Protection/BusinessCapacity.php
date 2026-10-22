<?php
/**
 * Persistent normal inquiry occupancy, before Woo's first save (#568).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Statuses;
use WC_Order;
use WP_Error;

/** The review registry's native lock/CAS also serializes independent normal pools. */
final class BusinessCapacity {
	public const KEY = '_linker_business_capacity_key';
	/** First-save verification lives only within the trusted native request.
	 *
	 * @var array<string,array<string,string>>
	 */
	private static array $expected = array();
	// Owner-approved adjustable operating envelopes, docs/specs/568-global-business-intake.md.
	public const LIMITS = array(
		'ordinary' => array(
			'count' => 128,
			'bytes' => 33554432,
		),
		'approved' => array(
			'count' => 64,
			'bytes' => 16777216,
		),
	);

	/** Native completion/deletion, rather than elapsed time or SMTP, releases space. */
	public function register(): void {
		add_action( 'woocommerce_before_order_object_save', array( self::class, 'prepare' ), 99 );
		add_action( 'woocommerce_new_order', array( $this, 'bind' ), 30, 2 );
		add_action( 'woocommerce_order_status_changed', array( $this, 'status' ), 30, 4 );
		add_action( 'woocommerce_delete_order', array( $this, 'deleted' ) );
	}

	/**
	 * A count/empty-byte refusal before optional inquiry summarization or native work.
	 * Actual complete logical bytes are checked again at prepare(), before first save.
	 */
	public static function preflight(): ?WP_Error {
		$context = apply_filters( 'linker_commerce_public_business_context', null ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted server-only native context.
		if ( 'enforce' !== Configuration::active_mode() || ( is_array( $context ) && ! empty( $context['intake'] ) ) ) {
			return null;
		}
		$result = IntakeStore::edit(
			static function ( array &$state ): array|WP_Error {
				self::initialize( $state );
				return self::room( $state, TrustedCustomer::current() ? 'approved' : 'ordinary', 1 );
			},
			1
		);
		return $result instanceof WP_Error ? $result : null;
	}

	/**
	 * Charge full prepared Woo data, items, snapshot and evidence without truncation.
	 *
	 * @param WC_Order $order Native prepared inquiry, before its first save.
	 * @param int      $additional_bytes Proven generated-summary headroom, never a customer cut-off.
	 * @throws CapacityFull Explicit native failure; no received result is fabricated.
	 */
	public static function prepare( WC_Order $order, int $additional_bytes = 0 ): void {
		if ( 'enforce' !== Configuration::active_mode() || $order->get_id() > 0 || $order->get_meta( Intake::META ) || ! in_array( $order->get_meta( '_linker_inquiry_source' ), array( 'contact', 'proforma' ), true ) ) {
			return;
		}
		$key = (string) $order->get_meta( self::KEY );
		if ( '' !== $key ) {
			return;
		}
		$context = apply_filters( 'linker_commerce_public_business_context', null ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native source association, never browser fields.
		$key     = is_array( $context ) && wp_is_uuid( (string) ( $context['id'] ?? '' ), 4 ) ? (string) $context['id'] : wp_generate_uuid4();
		$pool    = TrustedCustomer::current() ? 'approved' : 'ordinary';
		$bytes   = self::bytes( $order ) + $additional_bytes;
		$result  = IntakeStore::edit(
			static function ( array &$state ) use ( $key, $pool, $bytes, $order ): array|WP_Error {
				self::initialize( $state );
				if ( isset( $state['business'][ $key ] ) ) {
					$entry = $state['business'][ $key ];
					return (int) $entry['order'] === $order->get_id() && (int) $entry['bytes'] === $bytes
						? array() : self::problem();
				}
				$room = self::room( $state, $pool, $bytes );
				if ( is_wp_error( $room ) ) {
					return $room;
				}
				$state['business'][ $key ] = array(
					'pool'  => $pool,
					'order' => $order->get_id(),
					'bytes' => $bytes,
				);
				IntakeStore::save( $state );
				return array();
			},
			1
		);
		if ( $result instanceof WP_Error ) {
			throw new CapacityFull( $result ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Structured WP_Error is escaped at the native form consumer.
		}
		$order->update_meta_data( self::KEY, $key );
		$legacy                 = $order->get_data_store() instanceof \WC_Data_Store && is_a( $order->get_data_store()->get_current_class_name(), \WC_Order_Data_Store_CPT::class, true );
		self::$expected[ $key ] = array();
		foreach ( $order->get_meta_data() as $meta ) {
			$value = $legacy && is_array( $meta->value ) ? wp_unslash( $meta->value ) : $meta->value;
			self::$expected[ $key ][ (string) $meta->key ] = self::digest( $value );
		}
	}

	/**
	 * Convert a proven pre-model envelope into its complete actual first-save data.
	 * The slot and paid/native throughput remain charged; only unused byte slack
	 * is replaced before this order has ever been saved.
	 *
	 * @param WC_Order $order Complete prepared native inquiry.
	 * @throws CapacityFull An unproven payload cannot exceed the reserved envelope.
	 */
	public static function finalize( WC_Order $order ): void {
		if ( $order->get_id() > 0 || ! $order->get_meta( self::KEY ) ) {
			return;
		}
		$key    = (string) $order->get_meta( self::KEY );
		$bytes  = self::bytes( $order );
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $key, $bytes ): array|WP_Error {
				$entry = $state['business'][ $key ] ?? null;
				if ( ! is_array( $entry ) || 0 !== $entry['order'] || $bytes > $entry['bytes'] ) {
					return self::problem();
				}
				$state['business'][ $key ]['bytes'] = $bytes;
				IntakeStore::save( $state );
				return array();
			},
			1
		);
		if ( $result instanceof WP_Error ) {
			throw new CapacityFull( $result ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Structured WP_Error is escaped at the native form consumer.
		}
		// Rebuild the first-save verification from the actual prepared metadata.
		$legacy                 = $order->get_data_store() instanceof \WC_Data_Store && is_a( $order->get_data_store()->get_current_class_name(), \WC_Order_Data_Store_CPT::class, true );
		self::$expected[ $key ] = array();
		foreach ( $order->get_meta_data() as $meta ) {
			self::$expected[ $key ][ (string) $meta->key ] = self::digest( $legacy && is_array( $meta->value ) ? wp_unslash( $meta->value ) : $meta->value );
		}
	}

	/**
	 * Woo may swallow a native save exception. Never announce received from its
	 * in-memory object alone: force native metadata readback before status/mail.
	 *
	 * @param WC_Order $order Native caller's saved object.
	 * @param string   $key Trusted first-save key when checkout reloads the object.
	 */
	public static function verify( WC_Order $order, string $key = '' ): ?WP_Error {
		$fresh = $order->get_id() > 0 ? wc_get_order( $order->get_id() ) : false;
		if ( ! $fresh instanceof WC_Order ) {
			return new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
		}
		$fresh->read_meta_data( true );
		$key = '' !== $key ? $key : (string) $order->get_meta( self::KEY );
		foreach ( self::$expected[ $key ] ?? array() as $name => $digest ) {
			if ( self::digest( $fresh->get_meta( $name ) ) !== $digest ) {
				return new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
			}
		}
		return null;
	}

	/**
	 * Native metadata scalars are strings after DB storage; arrays keep types.
	 *
	 * @param mixed $value Prepared or native value, never printed.
	 */
	private static function digest( mixed $value ): string {
		return hash( 'sha256', maybe_serialize( is_scalar( $value ) ? (string) $value : $value ) );
	}

	/**
	 * The first save's source association survives a lost acknowledgement.
	 *
	 * @param int            $id Actual saved order.
	 * @param WC_Order|false $order Native saved object.
	 */
	public function bind( int $id, WC_Order|false $order = false ): void {
		$order = $order instanceof WC_Order ? $order : wc_get_order( $id );
		$key   = $order instanceof WC_Order ? (string) $order->get_meta( self::KEY ) : '';
		if ( '' === $key ) {
			return;
		}
		IntakeStore::edit(
			static function ( array &$state ) use ( $key, $id ): array {
				if ( isset( $state['business'][ $key ] ) ) {
					$state['business'][ $key ]['order'] = $id;
					IntakeStore::save( $state );
				}
				return array();
			},
			1
		);
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
		$fresh = wc_get_order( $id );
		// A customer-controlled cancellation does not attest staff processing.
		// Proforma is the website's last handoff: subsequent trade is offline.
		if ( current_user_can( 'manage_woocommerce' ) && $fresh instanceof WC_Order && in_array( $to, array( Statuses::PROFORMA, 'completed', 'cancelled' ), true ) && $fresh->has_status( $to ) ) {
			$this->release( $id, (string) $fresh->get_meta( self::KEY ) );
		}
	}

	/**
	 * Actual native deletion frees removed storage; erasing PII alone does not.
	 *
	 * @param int $id Deleted inquiry.
	 */
	public function deleted( int $id ): void {
		if ( ! wc_get_order( $id ) ) {
			$this->release( $id );
		}
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
				if ( ! is_array( $entry ) || ! isset( self::LIMITS[ $entry['pool'] ?? '' ] ) || ! is_int( $entry['bytes'] ?? null ) || $entry['bytes'] < 1 || ! is_int( $entry['order'] ?? null ) || $entry['order'] < 0 ) {
					throw new \RuntimeException( 'business_capacity_invalid_entry' );
				}
			}
			BusinessDisposition::reconcile( $state );
			return;
		}
		$state['business'] = array();
		$page              = 1;
		do {
			$orders = wc_get_orders(
				array(
					'status'  => array( 'pending', 'on-hold', Statuses::RECEIVED ),
					'limit'   => 100,
					'page'    => $page,
					'orderby' => 'ID',
					'order'   => 'ASC',
				)
			);
			if ( ! is_array( $orders ) ) {
				throw new \RuntimeException( 'business_capacity_history_unreadable' );
			}
			foreach ( $orders as $order ) {
				if ( in_array( $order->get_meta( '_linker_inquiry_source' ), array( 'contact', 'proforma' ), true ) && ! $order->get_meta( Intake::META ) ) {
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
	 * Check count and actual encoded logical bytes atomically.
	 *
	 * @param array<string,mixed> $state Locked registry.
	 * @param string              $pool Staff-selected pool.
	 * @param int                 $bytes Complete prospective logical bytes.
	 * @return array<string,mixed>|WP_Error
	 */
	private static function room( array $state, string $pool, int $bytes ): array|WP_Error {
		$entries = array_filter( $state['business'], static fn ( array $entry ): bool => $pool === $entry['pool'] );
		return count( $entries ) >= self::LIMITS[ $pool ]['count'] || array_sum( array_column( $entries, 'bytes' ) ) + $bytes > self::LIMITS[ $pool ]['bytes']
			? self::problem() : array();
	}

	/**
	 * Release only a proven processed/deleted native source, never a timer.
	 *
	 * @param int    $id Native source.
	 * @param string $key Trusted first-save association.
	 */
	private function release( int $id, string $key = '' ): void {
		IntakeStore::edit(
			static function ( array &$state ) use ( $id, $key ): array {
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

	/** Accurate native refusal: no new order number or receipt claim. */
	private static function problem(): WP_Error {
		return new WP_Error( 'linker_business_capacity', self::message(), array( 'status' => 503 ) );
	}

	/** The ordinary form and tool consumers share the honest unsaved result. */
	public static function message(): string {
		return __( 'Your request has not been saved. We cannot accept new requests on this website right now. Your entries and solution draft are still here. Please try again later or email sales@de-linker.com.', 'linker-commerce' );
	}
}
