<?php
/**
 * Native non-message admission; permissions and field validation stay upstream.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Limits repeated password reset mail to its registered recipient. */
final class Operation {
	/**
	 * Reserve a native password reset before WordPress dispatches its email.
	 *
	 * @param array<string,mixed> $payload Allowlisted semantic fields, no passwords.
	 * @return array<string,mixed>|WP_Error Dispatched permit.
	 */
	public static function password_reset( array $payload ): array|WP_Error {
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$target = Identity::recipient( $payload['email'] );
		$limits = array(
			new Allowance( 'password_reset_target_hour', $target, 2, HOUR_IN_SECONDS ),
			new Allowance( 'password_reset_target_day', $target, 5, DAY_IN_SECONDS ),
		);
		$id     = wp_generate_uuid4();
		$fp     = Fingerprint::make( $identity, 'password_reset', $payload );
		if ( is_wp_error( $fp ) ) {
			return $fp;
		}
		$owners   = $identity->owners();
		$owners[] = Allowance::owner_for( $target );
		$ledger   = new Ledger();
		$result   = $ledger->reserve( $id, $fp, $limits, 120, array(), 'password_reset', $identity->binding(), $owners );
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
