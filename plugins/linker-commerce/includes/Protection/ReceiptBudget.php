<?php
/**
 * Independent target and site budgets for optional automated customer receipts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Refusing an optional receipt never refuses the business record or team mail. */
final class ReceiptBudget {
	/**
	 * Shared across public inquiry doors; target names/URLs never enter the journal.
	 * Initial 2/hour and 5/day target recommendations: issue #508 owner delegation.
	 * Existing 10/day site allocation remains independent of the host's rolling cap.
	 *
	 * @param string     $email Validated recipient.
	 * @param int|string $order_id Native source reference, stabilizes a repeated transition.
	 * @param string     $kind Native source kind, prevents unrelated id collisions.
	 */
	public static function take( string $email, int|string $order_id, string $kind = 'inquiry' ): bool {
		return '' === self::reason( $email, $order_id, $kind );
	}

	/**
	 * Empty reason admits the optional receipt; faults are distinct from quota.
	 *
	 * @param string|string[] $email Validated native recipient or frozen To list.
	 * @param int|string      $order_id Native source reference.
	 * @param string          $kind Native source kind.
	 */
	public static function reason( string|array $email, int|string $order_id, string $kind = 'inquiry' ): string {
		$subjects = array();
		if ( is_string( $email ) ) {
			// Existing callers keep their exact single-target identity/fingerprint.
			$subjects[] = Identity::recipient( $email );
		} else {
			$recipients = array();
			foreach ( $email as $recipient ) {
				// wp_mail parses the actual address from the same native Name <address> form.
				$address = preg_match( '/(.*)<(.+)>/', $recipient, $parts ) ? $parts[2] : $recipient;
				$address = strtolower( trim( $address ) );
				if ( ! is_email( $address ) ) {
					return 'unavailable';
				}
				$recipients[ $address ] = true;
			}
			$recipients = array_keys( $recipients );
			sort( $recipients, SORT_STRING );
			$subjects = array_map( array( Identity::class, 'recipient' ), $recipients );
		}
		if ( array() === $subjects ) {
			return 'unavailable';
		}
		$subject    = 1 === count( $subjects ) ? $subjects[0] : hash_hmac( 'sha256', 'public-recipients|' . (string) wp_json_encode( $subjects ), wp_salt( 'nonce' ) );
		$allowances = array();
		foreach ( $subjects as $target ) {
			$allowances[] = new Allowance( 'receipt_target_hour', $target, 2, HOUR_IN_SECONDS );
			$allowances[] = new Allowance( 'receipt_target_day', $target, 5, DAY_IN_SECONDS );
		}
		$allowances[] = new Allowance( 'receipt_site_day', 'site', 10, DAY_IN_SECONDS );
		$hex          = hash_hmac( 'sha256', 'public-receipt|' . $kind . '|' . $order_id, wp_salt( 'nonce' ) );
		$id           = substr( $hex, 0, 8 ) . '-' . substr( $hex, 8, 4 ) . '-4' . substr( $hex, 13, 3 ) . '-a' . substr( $hex, 17, 3 ) . '-' . substr( $hex, 20, 12 );
		$fp           = hash_hmac( 'sha256', $subject . '|' . $kind . '|' . $order_id, wp_salt( 'nonce' ) );
		$ledger       = new Ledger();
		$permit       = $ledger->reserve(
			$id,
			$fp,
			$allowances,
			60,
			array(),
			'customer_receipt'
		);
		if ( is_wp_error( $permit ) ) {
			$data = $permit->get_error_data();
			if ( 'linker_admission_quota' !== $permit->get_error_code() || ! is_array( $data ) ) {
				return 'unavailable';
			}
			return 'receipt_site_day' === ( $data['dimension'] ?? '' ) ? 'daily_cap' : 'target_cap';
		}
		if ( 'completed' === $permit['status'] ) {
			return '';
		}
		if ( is_wp_error( $ledger->dispatch( $id, $fp ) ) ) {
			return 'unavailable';
		}
		return is_wp_error( $ledger->complete( $id, $fp, is_int( $order_id ) ? $order_id : 0 ) ) ? 'unavailable' : '';
	}
}
