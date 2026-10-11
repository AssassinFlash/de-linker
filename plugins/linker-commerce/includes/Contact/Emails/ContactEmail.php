<?php
/**
 * Base of the contact form's emails.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact\Emails;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Mail\LocaleSwitch;
use WC_Email;

/**
 * The shell both contact emails share: an HTML email from a template of this
 * plugin (a theme may override it in woocommerce/emails/), rendered in the
 * language the message calls for — the visitor's for the receipt, the site's
 * for the team letter (docs/specs/11-commerce.md, Mail).
 *
 * The sending itself is the site's one mail pipeline: these are $wp_mail()
 * calls like every other, so the Outbox queues them, retries them and keeps
 * them under the host's quota.
 */
abstract class ContactEmail extends WC_Email {


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
		$this->template_base = plugin_dir_path( $plugin_file ) . 'templates/';
		$this->locale_switch = new LocaleSwitch();
		parent::__construct();
	}

	/**
	 * The language switch happens in notify_in().
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
				'submission'         => $this->object,
				'email_heading'      => $this->get_heading(),
				'additional_content' => $this->get_additional_content(),
				'sent_to_admin'      => ! $this->is_customer_email(),
				'plain_text'         => false,
				'email'              => $this,
			),
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
	 * Sends the email about one message, in a locale.
	 *
	 * @param Submission $submission The visitor's message.
	 * @param string     $locale     The WordPress locale to write in.
	 */
	protected function notify_in( Submission $submission, string $locale ): void {
		$this->object = $submission;
		$this->locale_switch->to( $locale );
		try {
			$this->send_notification();
		} finally {
			$this->locale_switch->back();
		}
	}
}
