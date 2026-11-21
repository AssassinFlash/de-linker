<?php
/**
 * Delivery allowance for repeated receipts sent to the same address.
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
	 * @param bool            $spend Charge this source or only check current availability.
	 */
	public static function reason( string|array $email, int|string $order_id, string $kind = 'inquiry', bool $spend = true ): string {
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
		$subject = 1 === count( $subjects ) ? $subjects[0] : hash_hmac( 'sha256', 'public-recipients|' . (string) wp_json_encode( $subjects ), wp_salt( 'nonce' ) );
		$hex     = hash_hmac( 'sha256', 'public-receipt|' . $kind . '|' . $order_id, wp_salt( 'nonce' ) );
		$id      = substr( $hex, 0, 8 ) . '-' . substr( $hex, 8, 4 ) . '-4' . substr( $hex, 13, 3 ) . '-a' . substr( $hex, 17, 3 ) . '-' . substr( $hex, 20, 12 );
		$fp      = hash_hmac( 'sha256', $subject . '|' . $kind . '|' . $order_id, wp_salt( 'nonce' ) );
		return ReceiptRecipients::admit( array_map( array( Allowance::class, 'owner_for' ), $subjects ), $id, $fp, $spend );
	}
}
