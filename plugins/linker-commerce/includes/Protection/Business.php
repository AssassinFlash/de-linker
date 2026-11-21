<?php
/**
 * Admission around the native inquiry write, shared by both browser doors.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WC_Order;
use WP_Error;

/** Native storage remains authoritative for the result; the journal owns admission. */
final class Business {

	/**
	 * Validate fields/nonce first; only the winning dispatched request runs work.
	 *
	 * @param string                          $action Server action.
	 * @param array<string,mixed>             $post Unslashed transport.
	 * @param array<string,mixed>             $payload Validated semantic input, without credentials.
	 * @param callable(): (WC_Order|WP_Error) $work Native writer.
	 * @param bool                            $current Whether the submitted draft still matches the current draft.
	 * @param (callable():?WP_Error)|null     $preflight Optional read-only native checks, after completed-record recovery.
	 * @return WC_Order|WP_Error Native result or explicit refusal.
	 */
	public static function run( string $action, array $post, array $payload, callable $work, bool $current = true, ?callable $preflight = null ): WC_Order|WP_Error {
		$receipt_only = 'inquiry' === $action && '1' === ( $post['linker_inquiry_receipt_only'] ?? '' );
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$id = isset( $post['linker_request_id'] ) && is_string( $post['linker_request_id'] ) ? $post['linker_request_id'] : '';
		$fp    = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fp ) ) {
			return $fp;
		}
		$ledger = new Ledger();
		if ( wp_is_uuid( $id, 4 ) ) {
			$old = $ledger->lookup( $id, $fp );
			if ( is_wp_error( $old ) && 'linker_admission_unknown_receipt' !== $old->get_error_code() ) {
				// A failed lookup cannot establish that the original write is absent.
				return new WP_Error( $old->get_error_code(), __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ), $old->get_error_data() );
			}
			if ( ! is_wp_error( $old ) && $action === $old['purpose'] && $identity->binding() === $old['binding'] ) {
				$order = BusinessRecord::recover( $id, $fp, $identity->binding(), $old );
				if ( $order instanceof WC_Order ) {
					if ( $order->has_status( 'pending' ) && $order->get_meta( Intake::META ) ) {
						$order->update_meta_data( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META, 'review_hold' );
						WC()->mailer();
						$order->update_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED );
					}
					$ledger->complete( $id, $fp, $order->get_id() );
					return $order;
				}
				// Match Admission's existing-receipt fence before asking for a
				// fresh proof. Reserved/dispatched/unresolved and a completed
				// receipt without a verifiable native result are not a new write.
				return new WP_Error( 'linker_inquiry_pending', __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ) );
			}
		}
		if ( $receipt_only ) {
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
		$check = Turnstile::check( $action, $post );
		if ( is_wp_error( $check ) ) {
			return $check;
		}
		if ( Campaign::submitted( $payload ) ) {
			return new WP_Error( 'linker_admission_input', self::verification_message( 'failed' ), array( 'status' => 400 ) );
		}
		$limits  = apply_filters( 'linker_commerce_public_business_limits', array(), $action, $identity ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Current native customer and connection.
		$carry   = apply_filters( 'linker_commerce_public_business_carry', array(), $action, $identity ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Preserve customer's native login association.
		$email   = $payload['email'] ?? ( $payload['details']['email'] ?? '' );
		$owners  = is_string( $email ) && is_email( $email ) ? array( Allowance::owner_for( Identity::recipient( $email ) ) ) : array();
		$permit  = $ledger->reserve( $id, $fp, $limits, 120, $carry, $action, $identity->binding(), array_merge( $identity->owners(), $owners ) );
		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		$sent = $ledger->dispatch( $id, $fp );
		if ( is_wp_error( $sent ) ) {
			return self::unconfirmed_receipt();
		}
		$context = static fn (): array => array(
			'enforced'    => true,
			'id'          => $id,
			'fingerprint' => $fp,
			'action'      => $action,
			'binding'     => $identity->binding(),
		);
		add_filter( 'linker_commerce_public_business_context', $context );
		try {
			$result = $work();
			if ( $result instanceof WC_Order ) {
				$ledger->complete( $id, $fp, $result->get_id() );
			}
			return $result;
		} finally {
			remove_filter( 'linker_commerce_public_business_context', $context );
		}
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
			? __( 'Verification is temporarily unavailable. No request has been sent in this attempt. Your entries are still here. Please try again or email sales@de-linker.com.', 'linker-commerce' )
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
