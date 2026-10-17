<?php
/**
 * A notification to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\Commerce\Settings\Options;
use WC_Email;
use WC_Order;
use WP_User;

/**
 * Base of the internal notifications: one message to the internal
 * notification address with a blind copy to each address of the settings
 * (Options::notify_to() and notify_bcc(); docs/specs/11-commerce.md, Mail:
 * "内部通知收件人"), in the site's default language, as HTML. A reply goes
 * to the customer the notification is about. Every new internal notification
 * extends this class, so its recipients follow the one rule.
 */
abstract class TeamEmail extends WC_Email {

	/**
	 * The language switch.
	 *
	 * @var LocaleSwitch
	 */
	protected LocaleSwitch $locale_switch;

	/**
	 * Sets up the email.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( string $plugin_file, protected readonly Options $options ) {
		$this->customer_email = false;
		$this->template_base  = plugin_dir_path( $plugin_file ) . 'templates/';
		$this->locale_switch  = new LocaleSwitch();
		parent::__construct();
	}

	/**
	 * Sends the notification about an object (an order or a customer).
	 *
	 * @param WC_Order|WP_User $subject What the notification is about.
	 */
	protected function notify( WC_Order|WP_User $subject ): void {
		$this->object    = $subject;
		$this->recipient = $this->options->notify_to();
		$this->locale_switch->to( LocaleSwitch::site_default() );
		try {
			$this->send_notification();
		} finally {
			$this->locale_switch->back();
		}
	}

	/**
	 * The language switch happens in notify().
	 */
	public function setup_locale(): void {}

	/**
	 * See setup_locale().
	 */
	public function restore_locale(): void {}

	/**
	 * Internal mail uses its own sender; WC_Email installs these getters as
	 * wp_mail filters while sending, and Outbox persists their values (#286).
	 *
	 * @param string $from_name Sender name passed by WordPress.
	 */
	public function get_from_name( $from_name = '' ) {
		return $this->options->notify_sender()['name'];
	}

	/**
	 * The internal sender address, independent of WooCommerce's customer mail.
	 *
	 * @param string $from_email Sender address passed by WordPress.
	 */
	public function get_from_address( $from_email = '' ) {
		return $this->options->notify_sender()['email'];
	}

	/**
	 * Content type, the reply address (the customer) and the blind copies.
	 */
	public function get_headers() {
		$header = 'Content-Type: ' . $this->get_content_type() . "\r\n";
		$reply  = $this->reply_to();
		if ( '' !== $reply ) {
			$header .= 'Reply-to: ' . $reply . "\r\n";
		}
		$bcc = $this->options->notify_bcc();
		if ( array() !== $bcc ) {
			$header .= 'Bcc: ' . implode( ', ', $bcc ) . "\r\n";
		}
		/** This filter is documented in woocommerce/includes/emails/class-wc-email.php */
		return apply_filters( 'woocommerce_email_headers', $header, $this->id, $this->object, $this ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own filter, applied as WC_Email::get_headers() applies it.
	}

	/**
	 * These emails are HTML only.
	 */
	public function get_email_type() {
		return 'html';
	}

	/**
	 * The only format offered in the email settings.
	 *
	 * @return array<string, string>
	 */
	public function get_email_type_options() {
		return array( 'html' => __( 'HTML', 'linker-commerce' ) );
	}

	/**
	 * The HTML body.
	 */
	public function get_content_html() {
		return wc_get_template_html(
			$this->template_html,
			array(
				'email_heading'      => $this->get_heading(),
				'additional_content' => $this->get_additional_content(),
				'sent_to_admin'      => true,
				'plain_text'         => false,
				'email'              => $this,
			) + $this->template_args(),
			'',
			$this->template_base
		);
	}

	/**
	 * Plain text is not offered.
	 */
	public function get_content_plain() {
		return '';
	}

	/**
	 * No default closing paragraph.
	 */
	public function get_default_additional_content() {
		return '';
	}

	/**
	 * Template arguments of a subclass.
	 *
	 * @return array<string, mixed>
	 */
	abstract protected function template_args(): array;

	/**
	 * "Name <address>" of the customer the notification is about, or ''.
	 */
	private function reply_to(): string {
		if ( $this->object instanceof WC_Order && is_email( $this->object->get_billing_email() ) ) {
			return trim( $this->object->get_formatted_billing_full_name() . ' <' . $this->object->get_billing_email() . '>' );
		}
		if ( $this->object instanceof WP_User && is_email( $this->object->user_email ) ) {
			$name = trim( get_user_meta( $this->object->ID, 'billing_first_name', true ) . ' ' . get_user_meta( $this->object->ID, 'billing_last_name', true ) );
			return trim( ( '' !== $name ? $name : $this->object->display_name ) . ' <' . $this->object->user_email . '>' );
		}
		return '';
	}
}
