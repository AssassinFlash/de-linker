<?php
/**
 * Admission around the native inquiry write, shared by both browser doors.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Settings\Options;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\ConnectionFence;
use WC_Order;
use WP_Error;

/** The Woo order owns the receipt for its original submission. */
final class Business {

	/** Logical submissions currently writing on this PHP connection.
	 *
	 * @var array<string,true>
	 */
	private static array $writing = array();

	/**
	 * Submit a validated contact or product inquiry, or recover its original receipt.
	 *
	 * @param string                          $action Native form action.
	 * @param array<string,mixed>             $post Unslashed form transport.
	 * @param array<string,mixed>             $payload Validated semantic input.
	 * @param callable(): (WC_Order|WP_Error) $work Woo writer.
	 * @param bool                            $current Whether the customer's draft still matches the form.
	 * @param (callable():?WP_Error)|null     $preflight Read-only checks for a new submission.
	 */
	public static function run( string $action, array $post, array $payload, callable $work, bool $current = true, ?callable $preflight = null ): WC_Order|WP_Error {
		$id = is_string( $post['linker_request_id'] ?? null ) ? $post['linker_request_id'] : '';
		return self::write_once(
			$id,
			$action,
			$payload,
			$work,
			static function () use ( $action, $post, $payload, $current, $preflight ) {
				if ( 'inquiry' === $action && '1' === ( $post['linker_inquiry_receipt_only'] ?? '' ) ) {
					return self::unconfirmed_receipt();
				}
				if ( ! $current ) {
					return new WP_Error( 'linker_draft_changed', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ) );
				}
				if ( null !== $preflight ) {
					$error = $preflight();
					if ( $error instanceof WP_Error ) {
						return $error;
					}
				}
				if ( Campaign::submitted( $payload ) ) {
					return new WP_Error( 'linker_admission_input', self::verification_message( 'failed' ), array( 'status' => 400 ) );
				}
				return Turnstile::check( $action, $post );
			}
		);
	}

	/**
	 * Bind a native write and its result to this submission's owner and exact input.
	 *
	 * @param string                          $id Logical request UUID.
	 * @param string                          $action Server-selected business action.
	 * @param array<string,mixed>             $payload Verified customer input.
	 * @param callable(): (WC_Order|WP_Error) $write Native writer.
	 * @param callable                        $before_write Validation before a new write; returns true, null or WP_Error.
	 * @param Identity|null                   $owner Verified identity from the native customer or conversation.
	 * @param callable(WC_Order):mixed|null   $on_order Idempotently associate the confirmed native order with the originating customer action.
	 */
	public static function write_once( string $id, string $action, array $payload, callable $write, callable $before_write, ?Identity $owner = null, ?callable $on_order = null ): WC_Order|WP_Error {
		$id = strtolower( $id );
		if ( ! wp_is_uuid( $id, 4 ) || ! in_array( $action, array( 'contact', 'inquiry', 'genie_contact', 'genie_inquiry' ), true ) ) {
			return new WP_Error( 'linker_admission_input', self::verification_message( 'failed' ) );
		}
		if ( isset( self::$writing[ $id ] ) ) {
			return self::unconfirmed_receipt();
		}
		$identity = $owner ?? Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$fingerprint = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fingerprint ) ) {
			return $fingerprint;
		}
		$binding = $identity->binding();
		$result  = null;
		$submit  = static function () use ( $id, $action, $fingerprint, $binding, $write, $before_write, $on_order ) {
			$order = BusinessRecord::find( $id, $fingerprint, $binding );
			if ( is_wp_error( $order ) ) {
				return $order;
			}
			if ( null === $order ) {
				$valid = $before_write();
				if ( is_wp_error( $valid ) ) {
					return $valid;
				}
				if ( true !== $valid && null !== $valid ) {
					return self::unconfirmed_receipt();
				}
				$context = static fn (): array => array(
					'enforced'    => true,
					'id'          => $id,
					'fingerprint' => $fingerprint,
					'action'      => $action,
					'binding'     => $binding,
				);
				add_filter( 'linker_commerce_public_business_context', $context, PHP_INT_MAX );
				try {
					$saved = $write();
				} catch ( \Throwable $error ) {
					$saved = self::unconfirmed_receipt();
				} finally {
					remove_filter( 'linker_commerce_public_business_context', $context, PHP_INT_MAX );
				}
				if ( is_wp_error( $saved ) ) {
					$order = BusinessRecord::find( $id, $fingerprint, $binding );
					if ( ! $order instanceof WC_Order ) {
						return $saved;
					}
				} else {
					$order = BusinessRecord::recover( $id, $fingerprint, $binding, array( 'outcome' => $saved->get_id() ) );
					if ( ! $order ) {
						return self::unconfirmed_receipt();
					}
				}
			}
			if ( $order->has_status( 'pending' ) && $order->get_meta( Intake::META ) ) {
				$order->update_meta_data( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META, 'review_hold' );
				WC()->mailer();
				if ( ! $order->update_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED ) ) {
					return self::unconfirmed_receipt();
				}
				$order = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
				if ( ! $order instanceof WC_Order || ! $order->has_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED ) ) {
					return self::unconfirmed_receipt();
				}
			}
			if ( null !== $on_order ) {
				$linked = $on_order( $order );
				if ( is_wp_error( $linked ) ) {
					return $linked;
				}
			}
			return $order;
		};

		self::$writing[ $id ] = true;
		try {
			Lock::run(
				'inquiry-submission-' . $id,
				static function () use ( $submit, &$result ): void {
					$result = ConnectionFence::run( $submit );
				},
				0,
				true
			);
		} catch ( \Throwable $error ) {
			return self::unconfirmed_receipt();
		} finally {
			unset( self::$writing[ $id ] );
		}
		return $result ?? self::unconfirmed_receipt();
	}

	/**
	 * The browser and the native refusal say the same thing about the same
	 * attempt: verification stopped this request, so nothing was sent. The
	 * contact door renders this same sentence for its own verification states.
	 *
	 * @param string $outcome `failed` when the check refused, `unavailable` when it could not run.
	 */
	public static function verification_message( string $outcome ): string {
		return 'unavailable' === $outcome
			/* translators: %s: public team email address. */
			? sprintf( __( 'Verification is temporarily unavailable. No request has been sent in this attempt. Your entries are still here. Please try again or email %s.', 'linker-commerce' ), ( new Options() )->team_mailbox() )
			: __( 'Verification could not be completed. No request has been sent in this attempt. Your entries are still here. Please try again.', 'linker-commerce' );
	}

	/** A receipt lookup may recover an original order and must never start another. */
	private static function unconfirmed_receipt(): WP_Error {
		return new WP_Error( 'linker_inquiry_pending', __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ) );
	}

	/** Whether native handlers must use proof admission instead of the old connection gate. */
	public static function enabled(): bool {
		return 'off' !== Configuration::active_mode();
	}
}
