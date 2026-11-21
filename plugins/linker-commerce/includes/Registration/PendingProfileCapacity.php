<?php
/**
 * Preserve the four public profile fields when a Woo account form needs correction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WP_Error;

/**
 * Request-local form values for the signed-in account that submitted them.
 */
final class PendingProfileCapacity {

	/** This request's submitted public account values only.
	 *
	 * @var array<string,string>
	 */
	private static array $account_input = array();

	/** Native authenticated owner of those request-local values.
	 *
	 * @var int
	 */
	private static int $account_owner = 0;

	/**
	 * Retain a refused native account value without persisting credentials.
	 *
	 * @param string $key Native account form field.
	 * @param string $fallback Confirmed native value on ordinary page loads.
	 */
	public static function account_value( string $key, string $fallback ): string {
		return get_current_user_id() === self::$account_owner ? ( self::$account_input[ $key ] ?? $fallback ) : $fallback;
	}

	/**
	 * Keep the original submitted values for a signed-in customer correcting the Woo form.
	 *
	 * @param WP_Error $errors Native validated form errors.
	 * @param object   $user Canonical native public fields; credentials are never copied.
	 */
	public static function account_errors( WP_Error $errors, object $user ): void {
		unset( $errors );
		self::$account_input = array();
		self::$account_owner = 0;
		$id                  = (int) ( $user->ID ?? 0 );
		// phpcs:disable WordPress.Security.NonceVerification -- Verify the original Woo form nonce and native user before retaining non-secret fields.
		$nonce = '';
		foreach ( array( 'save-account-details-nonce', '_wpnonce' ) as $key ) {
			if ( isset( $_REQUEST[ $key ] ) && is_string( $_REQUEST[ $key ] ) ) {
				$nonce = sanitize_text_field( wp_unslash( $_REQUEST[ $key ] ) );
				break;
			}
		}
		$action = isset( $_POST['action'] ) && is_string( $_POST['action'] ) ? sanitize_text_field( wp_unslash( $_POST['action'] ) ) : '';
		if ( $id < 1 || get_current_user_id() !== $id || 'save_account_details' !== $action || ! wp_verify_nonce( $nonce, 'save_account_details' ) ) {
			return;
		}
		self::$account_owner = $id;
		foreach ( array( 'account_first_name', 'account_last_name', 'account_display_name', 'account_email' ) as $key ) {
			if ( isset( $_POST[ $key ] ) && is_string( $_POST[ $key ] ) ) {
				self::$account_input[ $key ] = sanitize_text_field( wp_unslash( $_POST[ $key ] ) );
			}
		}
		// phpcs:enable WordPress.Security.NonceVerification
	}
}
