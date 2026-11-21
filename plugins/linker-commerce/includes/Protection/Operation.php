<?php
/**
 * Native non-message admission; permissions and field validation stay upstream.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Binds public account writes and limits repeated reset mail to one address. */
final class Operation {
	/**
	 * Reserve the validated native action before WordPress changes an account or sends mail.
	 *
	 * @param string              $action Native action.
	 * @param array<string,mixed> $payload Allowlisted semantic fields, no passwords.
	 * @return array<string,mixed>|WP_Error Dispatched permit.
	 */
	public static function begin( string $action, array $payload ): array|WP_Error {
		if ( ! in_array( $action, array( 'registration', 'password_reset' ), true ) ) {
			return new WP_Error( 'linker_admission_input', __( 'Your request could not be processed. Please try again.', 'linker-commerce' ) );
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$limits = array();
		if ( 'registration' === $action ) {
			$subject    = '' === $identity->account ? $identity->browser : $identity->account;
			$address    = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
			$connection = hash_hmac( 'sha256', 'direct-connection|' . $address, wp_salt( 'auth' ) );
			$limits[]   = new Allowance( 'registration_subject', $subject, 5, DAY_IN_SECONDS );
			$limits[]   = new Allowance( 'registration_connection_hour', $connection, 100, HOUR_IN_SECONDS );
		}
		if ( isset( $payload['email'] ) && is_string( $payload['email'] ) && 'password_reset' === $action ) {
			$target   = Identity::recipient( $payload['email'] );
			$limits[] = new Allowance( $action . '_target_hour', $target, 2, HOUR_IN_SECONDS );
			$limits[] = new Allowance( $action . '_target_day', $target, 5, DAY_IN_SECONDS );
		}
		$id     = wp_generate_uuid4();
		$fp     = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fp ) ) {
			return $fp;
		}
		$email  = $payload['email'] ?? '';
		$owners = $identity->owners();
		if ( is_string( $email ) && is_email( $email ) ) {
			$owners[] = Allowance::owner_for( Identity::recipient( $email ) );
		}
		$ledger = new Ledger();
		$result = $ledger->reserve( $id, $fp, $limits, 120, array(), $action, $identity->binding(), $owners );
		if ( is_wp_error( $result ) ) {
			return $result;
		}
		$sent = $ledger->dispatch( $id, $fp );
		return is_wp_error( $sent ) ? $sent : array(
			'enforced'    => true,
			'id'          => $id,
			'fingerprint' => $fp,
		);
	}

	/**
	 * Finish only after the native write/send boundary succeeded.
	 *
	 * @param array<string,mixed> $permit Server permit.
	 * @param int                 $outcome Native user/record id.
	 */
	public static function finish( array $permit, int $outcome = 0 ): void {
		( new Ledger() )->complete( $permit['id'], $permit['fingerprint'], $outcome );
	}
}
