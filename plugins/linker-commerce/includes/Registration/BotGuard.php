<?php
/**
 * Bot checks on the public registration form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Inquiry\PublicGuard;
use WP_Error;

/**
 * The registration form is public, so it carries the same protections as the
 * two inquiry doors (AGENTS.md §5, shared rules): the signed start time, the
 * honeypot and the atomic per-connection limit of Inquiry\PublicGuard. Both
 * run on `woocommerce_process_registration_errors`, before WooCommerce creates
 * the account or any email exists, and both leave a counted refusal (#225).
 *
 * The trap fields print inside WooCommerce's own form through
 * `woocommerce_register_form`; WooCommerce's registration nonce is checked
 * before this hook runs.
 */
final class BotGuard {

	/**
	 * Error code of a refused registration.
	 */
	public const ERROR = 'linker_registration_bot';

	/**
	 * Reason key of the per-connection limit; the other reasons are
	 * PublicGuard's.
	 */
	public const LIMIT = 'limit';

	/**
	 * Prints the trap and the signed start; runs on woocommerce_register_form.
	 */
	public function fields(): void {
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- PublicGuard builds escaped fixed markup.
		echo ( new PublicGuard() )->fields();
	}

	/**
	 * Refuses a bot or an over-limit connection, and counts the refusal.
	 * The trap, the missing/forged clock and the too-fast check are counted
	 * whatever the field errors are: a filled trap is a bot even when the rest
	 * of the form is also incomplete. The per-connection allowance is only
	 * spent by a form whose fields already pass, so a customer correcting a
	 * field does not lose an attempt.
	 *
	 * @param WP_Error $errors Errors so far.
	 */
	public function validate( WP_Error $errors ): WP_Error {
		$guard = new PublicGuard();
		// The request's own field names are strings; the loop gives the guard
		// the string-keyed request it documents.
		$post = array();
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- WooCommerce checked its registration nonce before this filter runs.
		foreach ( (array) wp_unslash( $_POST ) as $key => $value ) {
			if ( is_string( $key ) ) {
				$post[ $key ] = $value;
			}
		}
		$protected = \Linker\Commerce\Protection\Business::enabled();
		$refusal   = $guard->refusal( $post, ! $protected );
		if ( '' !== $refusal ) {
			BlockedRegistrations::record( $refusal );
			$errors->add( self::ERROR, __( 'We could not process this registration. Please check your entries and try again.', 'linker-commerce' ) );
			return $errors;
		}
		if ( $errors->has_errors() ) {
			return $errors;
		}
		if ( ! $protected && ! $guard->take() ) {
			BlockedRegistrations::record( self::LIMIT );
			$errors->add( self::ERROR, __( 'We received several registrations from this connection. Please try again later or write to sales@de-linker.com.', 'linker-commerce' ) );
		}
		return $errors;
	}
}
