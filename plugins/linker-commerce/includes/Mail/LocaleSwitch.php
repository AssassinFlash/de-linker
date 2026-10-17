<?php
/**
 * Rendering an email or an admin response in a given language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * Switches WordPress, WooCommerce and this plugin to a locale while an email,
 * a Proforma invoice or an account review response is rendered, the way WooCommerce's own
 * wc_switch_to_site_locale() does it, and switches back afterwards.
 * WooCommerce's country list keeps the names of the language it was first
 * read in, so the switch also hands WooCommerce a fresh list for its duration:
 * an address rendered in German says "Deutschland" even when an English page
 * read the list before.
 */
final class LocaleSwitch {

	/**
	 * The locale switched to, while a switch is active.
	 *
	 * @var string
	 */
	private string $locale = '';

	/**
	 * Whether this scope actually pushed WordPress's locale stack. A nested
	 * email in the same language must not restore its caller's locale scope.
	 *
	 * @var bool
	 */
	private bool $switched = false;

	/**
	 * WooCommerce's country list from before the switch, while a switch is active.
	 *
	 * @var \WC_Countries|null
	 */
	private ?\WC_Countries $countries = null;

	/**
	 * Switches to a locale.
	 *
	 * @param string $locale Locale, e.g. de_DE_formal.
	 */
	public function to( string $locale ): void {
		$this->locale   = $locale;
		$this->switched = switch_to_locale( $locale );
		add_filter( 'plugin_locale', array( $this, 'plugin_locale' ) );
		$this->reload_domain();
		WC()->load_plugin_textdomain();
		$this->countries = WC()->countries;
		WC()->countries  = new \WC_Countries();
	}

	/**
	 * Switches back to the locale before the last switch.
	 */
	public function back(): void {
		if ( $this->switched ) {
			restore_previous_locale();
			$this->switched = false;
		}
		remove_filter( 'plugin_locale', array( $this, 'plugin_locale' ) );
		$this->locale = '';
		$this->reload_domain();
		WC()->load_plugin_textdomain();
		if ( null !== $this->countries ) {
			WC()->countries  = $this->countries;
			$this->countries = null;
		}
	}

	/**
	 * Loads this plugin's translations again for the active switch. WordPress
	 * reloads loaded text domains itself when the locale changes, but a switch
	 * to the site's default from a request in another language (Polylang's page
	 * language) is no change to WordPress, and the other language's strings
	 * would stay: a team email written from a German page must still be English.
	 * The file is loaded directly — load_plugin_textdomain() only registers a
	 * path (WordPress 7), and its lazy loading then reads the site's locale,
	 * not the one switched to.
	 */
	private function reload_domain(): void {
		unload_textdomain( 'linker-commerce' );
		$locale = '' === $this->locale ? determine_locale() : $this->locale;
		$mofile = dirname( __DIR__, 2 ) . '/languages/linker-commerce-' . $locale . '.mo';
		if ( is_readable( $mofile ) ) {
			load_textdomain( 'linker-commerce', $mofile );
		}
	}

	/**
	 * Locale of plugin translations while a switch is active.
	 *
	 * @param string $locale Locale WordPress determined.
	 */
	public function plugin_locale( string $locale ): string {
		return '' === $this->locale ? $locale : $this->locale;
	}

	/**
	 * The site's default language: the language of the team's emails.
	 */
	public static function site_default(): string {
		$locale = get_option( 'WPLANG' );
		return is_string( $locale ) && '' !== $locale ? $locale : 'en_US';
	}
}
