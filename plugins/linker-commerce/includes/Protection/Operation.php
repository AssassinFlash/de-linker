<?php
/**
 * Native non-message admission; permissions and field validation stay upstream.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Counts inexpensive native mutations separately from actual inquiries and chat. */
final class Operation {
	/**
	 * Initial operating allocations are recorded in the #520 specification.
	 *
	 * @param string              $action Native action.
	 * @param array<string,mixed> $post Unslashed transport.
	 * @param array<string,mixed> $payload Allowlisted semantic fields, no passwords.
	 * @return array<string,mixed>|WP_Error Dispatched permit.
	 */
	public static function begin( string $action, array $post, array $payload ): array|WP_Error {
		$config = Configuration::current();
		if ( 'off' === $config->mode ) {
			return array( 'enforced' => false );
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return 'observe' === $config->mode ? array( 'enforced' => false ) : $identity;
		}
		$subject  = '' === $identity->account ? $identity->browser : $identity->account;
		$capacity = match ( $action ) {
			'registration' => 5,
			'comment' => 10,
			'password_reset' => 5,
			'login' => 20,
			default => 120,
		};
		$window     = in_array( $action, array( 'registration', 'comment' ), true ) ? DAY_IN_SECONDS : HOUR_IN_SECONDS;
		$limits     = array( new Allowance( $action . '_subject', $subject, $capacity, $window ) );
		$address    = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		$connection = hash_hmac( 'sha256', 'direct-connection|' . $address, wp_salt( 'auth' ) );
		$limits[]   = new Allowance( $action . '_connection_hour', $connection, 100, HOUR_IN_SECONDS );
		if ( 'registration' === $action ) {
			// Shared public-registration allocation: docs/specs/569-registration-capacity.md.
			$site     = hash_hmac( 'sha256', 'registration-site', wp_salt( 'auth' ) );
			$limits[] = new Allowance( 'registration_site_hour', $site, 16, HOUR_IN_SECONDS );
			$limits[] = new Allowance( 'registration_site_day', $site, 32, DAY_IN_SECONDS );
		}
		if ( isset( $payload['email'] ) && is_string( $payload['email'] ) && 'password_reset' === $action ) {
			$target   = Identity::recipient( $payload['email'] );
			$limits[] = new Allowance( $action . '_target_hour', $target, 2, HOUR_IN_SECONDS );
			$limits[] = new Allowance( $action . '_target_day', $target, 5, DAY_IN_SECONDS );
		}
		$id     = isset( $post['linker_request_id'] ) && is_string( $post['linker_request_id'] ) ? $post['linker_request_id'] : '';
		$proof  = isset( $post['linker_proof'] ) && is_string( $post['linker_proof'] ) ? $post['linker_proof'] : '';
		$gate   = new Admission( $config );
		$email  = $payload['email'] ?? '';
		$owners = is_string( $email ) && is_email( $email ) ? array( Allowance::owner_for( Identity::recipient( $email ) ) ) : array();
		$permit = $gate->reserve( $action, $proof, $id, $payload, $limits, 120, true, array(), $owners );
		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		if ( ! empty( $permit['reused'] ) ) {
			return new WP_Error( 'linker_admission_already_completed', __( 'This request has already been processed. Please check the result before sending it again.', 'linker-commerce' ) );
		}
		$sent = $gate->dispatch( $permit );
		return is_wp_error( $sent ) ? $sent : $permit;
	}

	/**
	 * Finish only after the native write/send boundary succeeded.
	 *
	 * @param array<string,mixed> $permit Server permit.
	 * @param int                 $outcome Native user/record id.
	 */
	public static function finish( array $permit, int $outcome = 0 ): void {
		( new Admission( Configuration::current() ) )->complete( $permit, $outcome );
	}
}
