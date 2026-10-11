<?php
/**
 * The contact form of the /contact/ page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Contact\Emails\ReceiptEmail;
use Linker\Commerce\Contact\Emails\TeamMessageEmail;
use Linker\Commerce\Settings\Options;

/**
 * The contact page's form (ticket #68, GAP-8): the shortcode that renders it,
 * the handler that takes its submission, and the two emails — the receipt to
 * the visitor and the letter to the team mailbox with the settings' blind
 * copies. The site's previous contact form is not carried over: its
 * workspace, project bindings and receipts have no successor, the message
 * itself does.
 *
 * The mount is the page's own region: `[linker_contact_form]` stands inside
 * the `[data-linker-contact-mount]` of the /contact/ pages (EN and DE), where
 * the previous runtime rendered its form (tools/migrate/68-contact-form.py).
 */
final class Module {


	/**
	 * Sets up the module.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings (team mailbox, blind copies).
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly Options $options
	) {
	}

	/**
	 * Adds the module's hooks. The email objects are built per request and in
	 * the handler — WC_Email exists once WooCommerce is loaded, which is after
	 * this plugin's own load.
	 */
	public function register(): void {
		( new Form() )->register();
		( new Handler( $this->plugin_file, $this->options ) )->register();
		add_filter( 'woocommerce_email_classes', array( $this, 'add_emails' ) );
	}

	/**
	 * Adds the two contact emails; runs on woocommerce_email_classes, so
	 * WooCommerce knows them like its own (they appear under WooCommerce →
	 * Settings → Emails and a theme may override their templates).
	 *
	 * @param  array<string, object> $emails Email objects by class.
	 * @return array<string, object>
	 */
	public function add_emails( array $emails ): array {
		$emails[ ReceiptEmail::class ]     = new ReceiptEmail( $this->plugin_file );
		$emails[ TeamMessageEmail::class ] = new TeamMessageEmail( $this->plugin_file, $this->options );
		return $emails;
	}
}
