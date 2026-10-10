<?php
/**
 * The language of WooCommerce's own customer emails.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use WC_Email;

/**
 * WooCommerce renders customer emails in the site language. The ones this site
 * keeps (account created, password reset) are sent while the customer's own
 * request runs, in the language the customer reads the site in; that language
 * stays. This plugin's customer emails choose the inquiry's language themselves
 * (CustomerOrderEmail).
 */
final class EmailLocale {

	/**
	 * Whether WooCommerce may switch an email to the site language; runs on
	 * woocommerce_allow_switching_email_locale and woocommerce_allow_restoring_email_locale.
	 *
	 * @param bool     $allow WooCommerce's default.
	 * @param WC_Email $email The email.
	 */
	public function allow( bool $allow, WC_Email $email ): bool {
		return $email->is_customer_email() ? false : $allow;
	}
}
