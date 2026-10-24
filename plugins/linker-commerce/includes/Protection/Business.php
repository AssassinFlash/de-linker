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
		if ( 'off' === Configuration::active_mode() ) {
			return $work();
		}
		$config   = Configuration::current();
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return 'observe' === $config->mode ? $work() : $identity;
		}
		$id    = isset( $post['linker_request_id'] ) && is_string( $post['linker_request_id'] ) ? $post['linker_request_id'] : '';
		$proof = isset( $post['linker_proof'] ) && is_string( $post['linker_proof'] ) ? $post['linker_proof'] : '';
		$fp    = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fp ) ) {
			return $fp;
		}
		$ledger = new Ledger();
		if ( 'enforce' === $config->mode && wp_is_uuid( $id, 4 ) ) {
			$old = $ledger->lookup( $id, $fp );
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
			}
		}
		if ( 'enforce' === $config->mode && ! $current ) {
			return new WP_Error( 'linker_draft_changed', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ) );
		}
		if ( null !== $preflight ) {
			$error = $preflight();
			if ( $error instanceof WP_Error ) {
				return $error;
			}
		}
		$limits = apply_filters( 'linker_commerce_public_business_limits', array(), $action, $identity ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted business policy dimensions; BusinessPolicy owns the numeric policy.
		$carry  = apply_filters( 'linker_commerce_public_business_carry', array(), $action, $identity ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted account carry links, never browser values.
		$gate   = new Admission( $config, $ledger );
		// Initial native-write lease: bounded by the shared journal's 300-second ceiling (#519).
		$email  = $payload['email'] ?? ( $payload['details']['email'] ?? '' );
		$owners = is_string( $email ) && is_email( $email ) ? array( Allowance::owner_for( Identity::recipient( $email ) ) ) : array();
		if ( 'enforce' === $config->mode && in_array( $action, array( 'contact', 'inquiry' ), true ) ) {
			$required = Configuration::verification_required( $action );
			if ( $required && ! $config->ready() ) {
				return new WP_Error( 'linker_admission_configuration', __( 'Your request could not be processed. Please try again.', 'linker-commerce' ), array( 'status' => 503 ) );
			}
			$verified = $config->ready() && Intake::verified( $proof, $action, $identity, $id );
			if ( $required && ! $verified ) {
				return new WP_Error( 'linker_admission_proof', __( 'Your request could not be processed. Please try again.', 'linker-commerce' ), array( 'status' => 400 ) );
			}
			if ( Campaign::submitted( $payload ) ) {
				return new WP_Error( 'linker_admission_input', __( 'Your request could not be processed. Please try again.', 'linker-commerce' ), array( 'status' => 400 ) );
			}
			if ( ! $verified ) {
				return Intake::run( 'verification', $action, $id, $fp, $identity, $payload, BusinessPolicy::review_limits( $limits ), $carry, $owners, $work );
			}
		}
		$capacity = BusinessCapacity::preflight();
		if ( $capacity instanceof WP_Error ) {
			return $capacity;
		}
		$permit = $gate->reserve( $action, $proof, $id, $payload, $limits, 120, true, $carry, $owners );
		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		if ( ! empty( $permit['reused'] ) ) {
			return new WP_Error( 'linker_inquiry_pending', __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ) );
		}
		$sent = $gate->dispatch( $permit );
		if ( is_wp_error( $sent ) ) {
			return $sent;
		}
		$context = static fn (): array => array_merge(
			$permit,
			array(
				'action'  => $action,
				'binding' => $identity->binding(),
			)
		);
		add_filter( 'linker_commerce_public_business_context', $context );
		try {
			$result = $work();
			if ( $result instanceof WC_Order ) {
				$gate->complete( $permit, $result->get_id() );
			}
			return $result;
		} finally {
			remove_filter( 'linker_commerce_public_business_context', $context );
		}
	}

	/** Whether native handlers must use proof admission instead of the old connection gate. */
	public static function enabled(): bool {
		return 'off' !== Configuration::active_mode();
	}
}
