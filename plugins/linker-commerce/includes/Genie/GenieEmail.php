<?php
/**
 * Base of Genie's two customer emails.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

use Linker\Commerce\Mail\LocaleSwitch;
use WC_Email;

/**
 * What the conversation email and the address confirmation share: an HTML
 * customer email from a template of this plugin (a theme may override it in
 * woocommerce/emails/), written in the language of the page it was asked
 * from, to one address. The sending is the site's one mail pipeline: a
 * wp_mail() call like every other, queued, retried and kept under the host's
 * quota by the Outbox.
 *
 * Each send is a new object (Module::send()): WC_Email keeps a default
 * subject in its settings the first time it is read, so a reused object would
 * keep the first email's language.
 */
abstract class GenieEmail extends WC_Email {

	/**
	 * The language switch.
	 *
	 * @var LocaleSwitch
	 */
	private LocaleSwitch $locale_switch;

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
	 * The template's own variables, beside the heading and the closing.
	 *
	 * @return array<string, mixed>
	 */
	abstract protected function template_args(): array;

	/**
	 * Sends the email to one address, in one language.
	 *
	 * @param string $to     The address.
	 * @param string $locale WordPress locale.
	 * @return bool Whether wp_mail() took it.
	 */
	protected function send_to( string $to, string $locale ): bool {
		$this->recipient = $to;
		$this->locale_switch->to( $locale );
		try {
			return $this->send_notification();
		} finally {
			$this->locale_switch->back();
		}
	}

	/**
	 * The language switch happens in send_to().
	 */
	public function setup_locale(): void {
	}

	/**
	 * See setup_locale().
	 */
	public function restore_locale(): void {
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
				'sent_to_admin'      => false,
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
}
