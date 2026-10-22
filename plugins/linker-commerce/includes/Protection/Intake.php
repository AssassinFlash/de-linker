<?php
/**
 * Bounded native reception when verification cannot establish admission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\NotificationHold;
use WC_Order;
use WP_Error;

/** Trusted context is created before first save; no posted hold or label is read. */
final class Intake {
	public const META      = '_linker_review_intake';
	public const LANE_META = '_linker_review_lane';
	// Initial shape bounds, derived in docs/specs/542-safe-intake.md.
	private const MAX_BYTES = 32768;
	private const MAX_LINES = 20;

	/**
	 * Valid proof needs the persisted successful verification, not only its MAC.
	 *
	 * @param string   $proof Browser proof.
	 * @param string   $action Native door.
	 * @param Identity $identity Native subject.
	 * @param string   $id Logical business request.
	 */
	public static function verified( string $proof, string $action, Identity $identity, string $id ): bool {
		$checked = ( new Proof() )->read( $proof, 'verified', $action, $identity );
		if ( null === $checked ) {
			return false;
		}
		// A lookup checks the fingerprint; verification uses a private canonical
		// fingerprint, so inspect through a dedicated journal validity check.
		return ( new Ledger() )->proof_valid(
			array(
				'id'      => $checked['id'],
				'binding' => $identity->binding(),
				'action'  => $action,
				'single'  => true,
			),
			$id
		);
	}

	/**
	 * Native admission still enforces browser/account/connection dimensions.
	 *
	 * @param string                                         $lane Server-selected review class.
	 * @param string                                         $action Native business action.
	 * @param string                                         $id Stable request UUID.
	 * @param string                                         $fingerprint Bound semantic HMAC.
	 * @param Identity                                       $identity Native subject.
	 * @param array<string,mixed>                            $payload Validated semantic input.
	 * @param Allowance[]                                    $limits Existing sourced policy.
	 * @param list<array{source:Allowance,target:Allowance}> $carry Existing account carry.
	 * @param string[]                                       $owners Existing native privacy owners.
	 * @param callable(): (WC_Order|WP_Error)                $work Native writer.
	 * @return WC_Order|WP_Error
	 */
	public static function run( string $lane, string $action, string $id, string $fingerprint, Identity $identity, array $payload, array $limits, array $carry, array $owners, callable $work ): WC_Order|WP_Error {
		if ( ! wp_is_uuid( $id, 4 ) || ! isset( IntakeStore::CAPACITY[ $lane ] ) ) {
			return new WP_Error( 'linker_admission_input', __( 'Please check your entries and send the form again.', 'linker-commerce' ) );
		}
		$json = wp_json_encode( $payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		if ( ! is_string( $json ) || strlen( $json ) > self::MAX_BYTES || ( 'inquiry' === $action && WC()->cart->get_cart_contents_count() > 0 && count( WC()->cart->get_cart() ) > self::MAX_LINES ) ) {
			return new WP_Error( 'linker_intake_size', __( 'This request is too large to save for review. Your entries and solution draft are still here. Please email sales@de-linker.com.', 'linker-commerce' ) );
		}
		$result = self::problem( new WP_Error( 'linker_intake_busy' ) );
		// Only this logical request stays locked across its native/model work.
		// The site-wide capacity mutex covers reservation and binding separately.
		Lock::run(
			'intake-write-' . $id,
			static function () use ( $lane, $action, $id, $fingerprint, $identity, $limits, $carry, $owners, $work, &$result ): void {
				$result = IntakeStore::edit(
					static function ( array &$state ) use ( $lane, $action, $id, $fingerprint, $identity, $limits, $carry, $owners ): WC_Order|WP_Error|array {
						$ledger = new Ledger();
						$entry  = $state['entries'][ $id ] ?? null;
						if ( is_array( $entry ) ) {
							if ( $entry['fingerprint'] !== $fingerprint || $entry['binding'] !== $identity->binding() || $entry['action'] !== $action ) {
								return new WP_Error( 'linker_admission_payload_changed', __( 'Your entries changed. Please reload the form before sending a new request.', 'linker-commerce' ) );
							}
							$recovered = BusinessRecord::recover( $id, $fingerprint, $identity->binding(), array( 'outcome' => (int) $entry['order'] ) );
							if ( $recovered instanceof WC_Order ) {
								$state['entries'][ $id ]['order'] = $recovered->get_id();
								IntakeStore::save( $state );
								$ledger->complete( $id, $fingerprint, $recovered->get_id() );
								return $recovered;
							}
							// A started writer may have dispatched the optional paid summary.
							// Without an associated native record its outcome is unknown: do
							// not automatically retry work or refund its persistent slot.
							if ( ! empty( $entry['creating'] ) ) {
								return self::problem( new WP_Error( 'linker_intake_pending' ) );
							}
							$receipt = $ledger->lookup( $id, $fingerprint );
							if ( is_wp_error( $receipt ) || ! in_array( $receipt['status'], array( 'reserved', 'dispatched', 'unresolved' ), true ) || (int) $entry['order'] > 0 ) {
								return self::problem( new WP_Error( 'linker_intake_pending' ) );
							}
							if ( 'reserved' === $receipt['status'] ) {
								$dispatch = $ledger->dispatch( $id, $fingerprint );
								if ( is_wp_error( $dispatch ) ) {
									return self::problem( $dispatch );
								}
							}
							return self::begin( $state, $id, $entry['lane'] );
						}
						$old = $ledger->lookup( $id, $fingerprint );
						if ( ! is_wp_error( $old ) && 'completed' === $old['status'] && 0 === (int) $old['outcome'] ) {
							return self::grouped( $id );
						}
						if ( is_array( $old ) ) {
							$recovered = BusinessRecord::recover( $id, $fingerprint, $identity->binding(), $old );
							if ( $recovered instanceof WC_Order ) {
								return $recovered;
							}
						}
						$used = count( array_filter( $state['entries'], static fn ( array $record ): bool => $record['lane'] === $lane ) );
						if ( $used >= IntakeStore::CAPACITY[ $lane ] && 'campaign' !== $lane ) {
							return self::full();
						}
						$permit = $ledger->reserve( $id, $fingerprint, $limits, 120, $carry, $action, $identity->binding(), array_values( array_unique( array_merge( $identity->owners(), $owners ) ) ) );
						if ( is_wp_error( $permit ) ) {
							return self::problem( $permit );
						}
						if ( 'campaign' === $lane ) {
							$state['campaign_count'] = min( PHP_INT_MAX - 1, (int) $state['campaign_count'] ) + 1;
							if ( $used >= IntakeStore::CAPACITY[ $lane ] ) {
								$sent = $ledger->dispatch( $id, $fingerprint );
								if ( is_wp_error( $sent ) ) {
									return self::problem( $sent );
								}
								IntakeStore::save( $state );
								$ledger->complete( $id, $fingerprint, 0 );
								return self::grouped( $id );
							}
						}
						$state['entries'][ $id ] = array(
							'lane'        => $lane,
							'action'      => $action,
							'order'       => 0,
							'fingerprint' => $fingerprint,
							'binding'     => $identity->binding(),
							'at'          => time(),
							'owners'      => array_values( array_unique( array_merge( $identity->owners(), $owners ) ) ),
						);
						IntakeStore::save( $state );
						$sent = $ledger->dispatch( $id, $fingerprint );
						if ( is_wp_error( $sent ) ) {
							return self::problem( $sent );
						}
						return self::begin( $state, $id, $lane );
					}
				);
				if ( is_array( $result ) && isset( $result['write_lane'] ) ) {
					$result = self::write( (string) $result['write_lane'], $id, $fingerprint, $identity, $work );
				}
			}
		);
		return $result instanceof WC_Order || $result instanceof WP_Error ? $result : self::full();
	}

	/**
	 * Persist the creating occupation before releasing the global capacity mutex.
	 *
	 * @param array<string,mixed> $state Locked registry.
	 * @param string              $id Native operation.
	 * @param string              $lane Already reserved review lane.
	 * @return array{write_lane:string}
	 */
	private static function begin( array &$state, string $id, string $lane ): array {
		$state['entries'][ $id ]['creating'] = true;
		IntakeStore::save( $state );
		return array( 'write_lane' => $lane );
	}

	/**
	 * Execute under only the per-operation mutex, then bind under a short site lock.
	 *
	 * @param string                          $lane Stored review class.
	 * @param string                          $id Bound request UUID.
	 * @param string                          $fingerprint Semantic HMAC.
	 * @param Identity                        $identity Native subject.
	 * @param callable(): (WC_Order|WP_Error) $work Native writer.
	 * @return WC_Order|WP_Error
	 */
	private static function write( string $lane, string $id, string $fingerprint, Identity $identity, callable $work ): WC_Order|WP_Error {
		$context = static fn (): array => array(
			'enforced'    => true,
			'id'          => $id,
			'fingerprint' => $fingerprint,
			'binding'     => $identity->binding(),
			'intake'      => $lane,
		);
		add_filter( 'linker_commerce_public_business_context', $context );
		try {
			$order = $work();
			if ( $order instanceof WC_Order ) {
				$stored = $order->get_id() > 0 ? BusinessRecord::recover( $id, $fingerprint, $identity->binding(), array( 'outcome' => $order->get_id() ) ) : null;
				if ( ! $stored instanceof WC_Order ) {
					return new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
				}
				$order = $stored;
				$bound = IntakeStore::edit(
					static function ( array &$state ) use ( $id, $fingerprint, $identity, $order ): array|WP_Error {
						$entry = $state['entries'][ $id ] ?? null;
						if ( ! is_array( $entry ) || $entry['fingerprint'] !== $fingerprint || $entry['binding'] !== $identity->binding() ) {
							return self::problem( new WP_Error( 'linker_intake_pending' ) );
						}
						$state['entries'][ $id ]['order'] = $order->get_id();
						IntakeStore::save( $state );
						return array();
					}
				);
				if ( $bound instanceof WP_Error ) {
					return $bound;
				}
				( new Ledger() )->complete( $id, $fingerprint, $order->get_id() );
			}
			return $order;
		} catch ( \Throwable $error ) {
			// No transaction is owned here; leave any caller's transaction intact.
			return self::problem( new WP_Error( 'linker_intake_pending' ) );
		} finally {
			remove_filter( 'linker_commerce_public_business_context', $context );
		}
	}

	/**
	 * Called before first native save and before any model snapshot or receipt.
	 *
	 * @param WC_Order $order Prepared inquiry.
	 */
	public static function prepare( WC_Order $order ): bool {
		$context = apply_filters( 'linker_commerce_public_business_context', null ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted Business context, removed in finally.
		if ( ! is_array( $context ) || ! isset( IntakeStore::CAPACITY[ $context['intake'] ?? '' ] ) ) {
			return false;
		}
		$lane = (string) $context['intake'];
		$data = array(
			'lane' => $lane,
			'at'   => time(),
			'rule' => 'verification' === $lane ? '' : Campaign::VERSION,
		);
		$order->update_meta_data( self::META, $data );
		$order->update_meta_data( self::LANE_META, $lane );
		$order->update_meta_data(
			NotificationHold::META,
			array(
				'reason' => 'verification' === $lane ? 'verification_review' : 'confirmed_campaign_review',
				'rule'   => $data['rule'],
				'at'     => $data['at'],
			)
		);
		$order->update_meta_data( Queue::PENDING, 'held' );
		return true;
	}

	/**
	 * Internal journal codes retain diagnostics; native customers get translated text.
	 *
	 * @param WP_Error $error Private storage/admission diagnostic.
	 */
	private static function problem( WP_Error $error ): WP_Error {
		$message = 'linker_admission_quota' === $error->get_error_code()
			? __( 'The message limit has been reached. Your entries are still here. You can try again later or email sales@de-linker.com.', 'linker-commerce' )
			: __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' );
		return new WP_Error( $error->get_error_code(), $message, $error->get_error_data() );
	}

	/**
	 * No PII or model labels: only actual native inquiries awaiting staff review.
	 * Confirmed campaign samples and unsaved reservations do not create alerts.
	 *
	 * @phpstan-impure
	 *
	 * @return array{count:int,oldest:int,url:string}|WP_Error
	 */
	public static function pending_summary(): array|WP_Error {
		$result = IntakeStore::edit(
			static function ( array &$state ): array {
				$orders = array();
				$oldest = 0;
				foreach ( $state['entries'] as $id => $entry ) {
					if ( ! in_array( $entry['lane'], array( 'verification', 'individual' ), true ) || ! empty( $entry['erased'] ) ) {
						continue;
					}
					$order_id = (int) $entry['order'];
					$order    = $order_id > 0 ? wc_get_order( $order_id ) : ( ! empty( $entry['fingerprint'] ) && ! empty( $entry['binding'] ) ? BusinessRecord::recover( $id, $entry['fingerprint'], $entry['binding'], array( 'outcome' => 0 ) ) : null );
					if ( ! $order instanceof WC_Order || isset( $orders[ $order->get_id() ] ) ) {
						continue;
					}
					$order->read_meta_data( true );
					if ( ! $order->get_meta( self::META ) || ! \Linker\Commerce\Mail\NotificationHold::held( $order ) || $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) ) {
						continue;
					}
					$orders[ $order->get_id() ] = true;
					$at                         = (int) $entry['at'];
					$oldest                     = 0 === $oldest ? $at : min( $oldest, $at );
				}
				return array(
					'count'  => count( $orders ),
					'oldest' => $oldest,
					'url'    => admin_url( \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ? 'admin.php?page=wc-orders&linker_intake_review=1' : 'edit.php?post_type=shop_order&linker_intake_review=1' ),
				);
			}
		);
		if ( $result instanceof WP_Error ) {
			return $result;
		}
		if ( ! is_array( $result ) || ! is_int( $result['count'] ?? null ) || ! is_int( $result['oldest'] ?? null ) || ! is_string( $result['url'] ?? null ) ) {
			return new WP_Error( 'intake_summary_unavailable' );
		}
		return array(
			'count'  => $result['count'],
			'oldest' => $result['oldest'],
			'url'    => $result['url'],
		);
	}

	/** Capacity refusal is honest and retains the native form fields. */
	private static function full(): WP_Error {
		return new WP_Error( 'linker_intake_full', __( 'Your request has not been saved because the review queue is full. Your entries are still here. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
	}

	/**
	 * A grouped counter is not an independent saved inquiry.
	 *
	 * @param string $id Actual attempt UUID, not a representative order key.
	 */
	private static function grouped( string $id ): WP_Error {
		return new WP_Error( 'linker_intake_grouped', __( 'This message matches a repeated spam submission. We have not saved a separate inquiry or sent an email. Your entries are still here. For an individual review, select the review option in this form or email sales@de-linker.com.', 'linker-commerce' ), array( 'reference' => $id ) );
	}
}
