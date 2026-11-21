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

/** WooCommerce checks its registration nonce before the public form filter runs. */
final class BotGuard {

	/**
	 * Error code of a refused registration.
	 */
	public const ERROR = 'linker_registration_bot';

	/**
	 * Prints the shared hidden field on the registration form.
	 */
	public function fields(): void {
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- PublicGuard builds escaped fixed markup.
		echo PublicGuard::fields();
	}

	/**
	 * Record a filled honeypot while retaining existing field errors.
	 *
	 * @param WP_Error $errors Errors so far.
	 */
	public function validate( WP_Error $errors ): WP_Error {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing,WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- WooCommerce checks its nonce. The honeypot is only compared with the empty string.
		$post = array( 'website' => wp_unslash( $_POST['website'] ?? '' ) );
		if ( ! PublicGuard::allows( $post ) ) {
			BlockedRegistrations::record( PublicGuard::REFUSAL_HONEYPOT );
			$errors->add( self::ERROR, __( 'We could not process this registration. Please check your entries and try again.', 'linker-commerce' ) );
		}
		return $errors;
	}
}
