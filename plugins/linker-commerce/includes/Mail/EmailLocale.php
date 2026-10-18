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
 * WooCommerce renders customer emails in the site language. Password reset
 * emails use the stored recipient locale once Woo has identified the user,
 * including staff and scheduled contexts. Other customer emails retain their
 * caller scope; CustomerOrderEmail chooses the recorded inquiry language.
 */
final class EmailLocale {

	/**
	 * Native password emails reveal their user after setup_locale has run.
	 *
	 * @var array<int,LocaleSwitch>
	 */
	private array $password_scopes = array();

	/**
	 * Chooses the stored recipient locale before native Woo renders a password email.
	 *
	 * @param string   $recipient Native recipient, preserved for Outbox routing.
	 * @param mixed    $recipient_user Native email object, a user for password reset.
	 * @param WC_Email $email Native password email.
	 */
	public function password_recipient( string $recipient, $recipient_user, WC_Email $email ): string {
		$key = spl_object_id( $email );
		if ( $recipient_user instanceof \WP_User && ! isset( $this->password_scopes[ $key ] ) ) {
			$scope = new LocaleSwitch();
			$scope->to( get_user_locale( $recipient_user ) );
			$this->password_scopes[ $key ] = $scope;
		}
		return $recipient;
	}

	/**
	 * Whether WooCommerce may switch an email to the site language; runs on
	 * woocommerce_allow_switching_email_locale and woocommerce_allow_restoring_email_locale.
	 *
	 * @param bool     $allow WooCommerce's default.
	 * @param WC_Email $email The email.
	 */
	public function allow( bool $allow, WC_Email $email ): bool {
		$key = spl_object_id( $email );
		if ( isset( $this->password_scopes[ $key ] ) && 'woocommerce_allow_restoring_email_locale' === current_filter() ) {
			$this->password_scopes[ $key ]->back();
			unset( $this->password_scopes[ $key ] );
		}
		return $email->is_customer_email() ? false : $allow;
	}
}
