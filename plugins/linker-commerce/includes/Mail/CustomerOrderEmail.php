<?php
/**
 * An email to the customer about one inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\Commerce\Inquiry\OrderLocale;
use WC_Email;
use WC_Order;

/**
 * Base of the customer emails about an inquiry: sent to the billing address, in
 * the language the customer used for the inquiry, as HTML, from a template of
 * this plugin (a theme may override it in woocommerce/emails/).
 */
abstract class CustomerOrderEmail extends WC_Email {

	/**
	 * The language switch.
	 *
	 * @var LocaleSwitch
	 */
	protected LocaleSwitch $locale_switch;

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->customer_email = true;
		$this->template_base  = plugin_dir_path( $plugin_file ) . 'templates/';
		$this->locale_switch  = new LocaleSwitch();
		parent::__construct();
	}

	/**
	 * Sends the email about an order.
	 *
	 * @param int                $order_id Order id.
	 * @param WC_Order|false|int $order    Order, when the caller has it.
	 */
	public function trigger( $order_id, $order = false ): void {
		$order = $order instanceof WC_Order ? $order : wc_get_order( (int) $order_id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$this->object                         = $order;
		$this->recipient                      = $order->get_billing_email();
		$this->placeholders['{order_number}'] = $order->get_order_number();

		$this->locale_switch->to( OrderLocale::of( $order ) );
		try {
			$this->send_notification();
		} finally {
			$this->locale_switch->back();
		}
	}

	/**
	 * The language switch happens in trigger(); WooCommerce's switch to the site
	 * language stays off for these emails.
	 */
	public function setup_locale(): void {}

	/**
	 * See setup_locale().
	 */
	public function restore_locale(): void {}

	/**
	 * Read stored settings for each render so an unsaved default follows this
	 * inquiry's active locale in a shared background mailer instance.
	 */
	public function get_subject() {
		$this->init_settings();
		return parent::get_subject();
	}

	/** The heading follows the current inquiry language; see get_subject(). */
	public function get_heading() {
		$this->init_settings();
		return parent::get_heading();
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
				'order'              => $this->object,
				'email_heading'      => $this->get_heading(),
				'additional_content' => $this->get_additional_content(),
				'sent_to_admin'      => false,
				'plain_text'         => false,
				'email'              => $this,
			) + $this->template_args(),
			'',
			$this->template_base
		);
	}

	/**
	 * Plain text is not offered; WooCommerce asks for it only for plain or multipart emails.
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
	 * Further template arguments of a subclass.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array();
	}
}
