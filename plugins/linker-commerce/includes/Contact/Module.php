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
 * A deployed page whose content still carries the old fallback is mounted at
 * render time: the cutover list does not run that migration, and the live
 * pages measured 2026-10-14 still print the fallback with no form.
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
		// Before do_shortcode (priority 11 on the_content, WordPress default):
		// the replacement has to be a shortcode by the time that filter runs.
		add_filter( 'the_content', array( $this, 'mount_form' ), 9 );
	}

		/**
		 * Replaces the contact page's old fallback mount with the form shortcode.
		 *
		 * The pages ship their markup in post content (page template `empty`,
		 * measured on the deployed /contact/ and /de/kontakt/ on 2026-10-14).
		 * That content still holds the previous runtime's mount — a visible
		 * fallback and a noscript line — because the migration that swaps them
		 * for `[linker_contact_form]` is not in the cutover list. The swap
		 * happens here, on the way out, so a deploy renders the form without a
		 * content write. A page that already carries the shortcode is left
		 * alone. Any other page is left alone: the mount marker belongs to
		 * these two pages.
		 *
		 * The fallback line stays in the page and is shown only when this
		 * shortcode is not registered — the form really cannot render. While
		 * the shortcode exists, the line is removed with the noscript note of
		 * the previous runtime.
		 *
		 * @param string $content The page content.
		 */
	public function mount_form( string $content ): string {
		if ( ! $this->is_contact_page() || ! str_contains( $content, 'data-linker-contact-mount' ) ) {
			return $content;
		}
		if ( str_contains( $content, '[' . Form::SHORTCODE ) ) {
			return $this->without_previous_fallback( $content );
		}
		if ( ! shortcode_exists( Form::SHORTCODE ) ) {
			return $content;
		}
		$mounted = (string) preg_replace(
			'/(<div\b[^>]*\bdata-linker-contact-mount\b[^>]*>)\s*<div\b[^>]*\bcp-contact-fallback\b[^>]*>.*?<\/div>\s*(<\/div>)/s',
			'$1[' . Form::SHORTCODE . ']$2',
			$content,
			1,
			$count
		);
		if ( 1 !== $count ) {
			return $content;
		}
		return $this->without_previous_fallback( $mounted );
	}

		/**
		 * Whether the request is one of the two contact pages.
		 *
		 * English is the page at `contact`. German is its Polylang twin
		 * (`pll_get_post`), which is `/de/kontakt/` on the deployed site — not
		 * a slug this code invents.
		 */
	private function is_contact_page(): bool {
		if ( ! is_page() ) {
			return false;
		}
		$page = get_queried_object();
		if ( ! $page instanceof \WP_Post || 'page' !== $page->post_type ) {
			return false;
		}
		$english = get_page_by_path( 'contact' );
		if ( ! $english instanceof \WP_Post ) {
			return ( 'contact' === $page->post_name );
		}
		if ( (int) $english->ID === (int) $page->ID ) {
			return true;
		}
		if ( ! function_exists( 'pll_get_post' ) ) {
			return false;
		}
			// 0 is "not translated" (Polylang 3.4+); it is not a page id.
			return pll_get_post( (int) $english->ID, 'de' ) === (int) $page->ID;
	}

		/**
		 * Drops the previous runtime's fallback line and its noscript note.
		 *
		 * Both describe a JavaScript form that is no longer what renders. The
		 * visible line is the one the 2026-10-14 recheck found in place of the
		 * form ("If the form is unavailable…" / "Falls das Formular nicht
		 * verfügbar ist…").
		 *
		 * @param string $content Page content that already mounts the form.
		 */
	private function without_previous_fallback( string $content ): string {
		$without_noscript = (string) preg_replace(
			'/\s*<noscript>\s*<p\b[^>]*\bcp-contact-fallback\b[^>]*>.*?<\/noscript>/s',
			'',
			$content,
			1
		);
		return (string) preg_replace(
			'/\s*<div\b[^>]*\bcp-contact-fallback\b[^>]*>.*?<\/div>/s',
			'',
			$without_noscript,
			1
		);
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
