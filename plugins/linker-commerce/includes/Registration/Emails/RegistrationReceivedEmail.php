<?php
/**
 * Confirmation to the customer that the registration was received.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Prepared;

/**
 * Sent to the address the customer registered with, when the account is
 * created and waiting for review. The team notification is NewCustomerEmail;
 * this one is the customer's own confirmation that the account is pending.
 * WooCommerce's own new-account mail stays off: it tells the customer the
 * account is ready, which a pending account is not.
 */
final class RegistrationReceivedEmail extends CustomerApprovalEmail {
	/**
	 * Capture configured acknowledgement without spending its receipt policy.
	 *
	 * @param \WP_User $user Prospective public identity, without a password.
	 * @param string   $locale Customer's current native locale.
	 */
	public function preview( \WP_User $user, string $locale ): ?Message {
		$this->object    = $user;
		$this->recipient = $user->user_email;
		$this->locale_switch->to( $locale );
		try {
			return Prepared::capture( fn () => $this->send_notification() );
		} finally {
			$this->locale_switch->back();
			$this->object = false;
		}
	}

	/**
	 * Email id.
	 */
	public const ID = 'linker_registration_received';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id             = self::ID;
		$this->title          = __( 'Registration received', 'linker-commerce' );
		$this->description    = __( 'Sent to the customer when the account is registered and waiting for review.', 'linker-commerce' );
		$this->template_html  = 'emails/linker-registration-received.php';
		$this->customer_email = true;
		add_action( Fields::REGISTERED_ACTION . '_notification', array( $this, 'trigger' ) );
		parent::__construct( $plugin_file );
	}

	/**
	 * Unused: this email speaks on registration, not on a later state change.
	 */
	protected function target_status(): string {
		return '';
	}

	/**
	 * Sends the confirmation to the registered address. Runs on the
	 * registration action's "_notification" form, which carries the new
	 * customer id. The later arguments exist so a shared listener shape does
	 * not fail; this email does not read them.
	 *
	 * @param int    $user_id  Customer.
	 * @param string $previous Unused.
	 * @param string $current  Unused.
	 * @param string $reason   Unused.
	 */
	public function trigger( $user_id, $previous = '', $current = '', $reason = '' ): void {
		unset( $previous, $current, $reason );
		$user = get_userdata( (int) $user_id );
		if ( ! $user instanceof \WP_User ) {
			return;
		}
		if ( 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode() && '' !== \Linker\Commerce\Protection\ReceiptBudget::reason( $user->user_email, $user->ID, 'registration' ) ) {
			return;
		}
		$this->object    = $user;
		$this->recipient = $user->user_email;

		$this->locale_switch->to( get_user_locale( $user->ID ) );
		try {
			$this->send_notification();
		} finally {
			$this->locale_switch->back();
		}
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode()
			? __( 'Registration received', 'linker-commerce' )
			: __( 'We received your partner registration', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Registration received', 'linker-commerce' );
	}
}
