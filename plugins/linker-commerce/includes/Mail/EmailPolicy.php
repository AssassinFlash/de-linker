<?php
/**
 * Which WooCommerce emails the site sends.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use WC_Email;

/**
 * The site sends this plugin's emails and two of WooCommerce's own. Every
 * other WooCommerce email is about orders, payment or shipping, which the site
 * does not have, and is switched off. The new-account mail is among them: a
 * registration starts pending, and RegistrationReceivedEmail is the
 * confirmation the customer receives. WooCommerce's own mail says the account
 * is ready.
 */
final class EmailPolicy {

	/**
	 * WooCommerce emails that stay on: the password reset, and the
	 * administrator's notice that a payment method was switched on (a security
	 * notice).
	 */
	public const KEEP = array( 'customer_reset_password', 'admin_payment_gateway_enabled' );

	/**
	 * Switches off the other WooCommerce emails; runs on woocommerce_email_classes,
	 * after every email was added.
	 *
	 * @param array<string, mixed> $emails Email objects by class.
	 * @return array<string, mixed>
	 */
	public function switch_off_others( array $emails ): array {
		foreach ( $emails as $email ) {
			if ( $email instanceof WC_Email && ! self::is_ours( $email ) && ! in_array( $email->id, self::KEEP, true ) ) {
				add_filter( 'woocommerce_email_enabled_' . $email->id, '__return_false' );
			}
		}
		return $emails;
	}

	/**
	 * Whether an email belongs to this plugin.
	 *
	 * @param WC_Email $email Email.
	 */
	private static function is_ours( WC_Email $email ): bool {
		return str_starts_with( get_class( $email ), 'Linker\\Commerce\\' );
	}
}
