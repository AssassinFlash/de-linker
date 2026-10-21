<?php
/**
 * Rendering an email or an admin response in a given language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\I18n\Languages;

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
	 * The companion language plugin's current-language scope, when present.
	 *
	 * @var array{bool,mixed,string}|null
	 */
	private ?array $language_scope = null;

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
		$this->locale = $locale;
		if ( class_exists( Languages::class ) ) {
			$languages = new Languages();
			if ( $languages->ready() ) {
				$slug = $languages->slug_of_locale( $locale );
				if ( null !== $slug ) {
					$this->language_scope = $languages->enter( $slug );
				}
			}
		}
		$this->switched = switch_to_locale( $locale );
		add_filter( 'plugin_locale', array( $this, 'plugin_locale' ) );
		$this->reload_domain();
		// The companion plugin's enter() already switched WordPress to the
		// same locale, so switch_to_locale() above is a no-op and WordPress
		// does not reload the loaded text domains. WooCommerce's own domain
		// would stay in the previous language; its country list would render
		// English names inside a German card. Reload that domain here.
		$this->reload_woocommerce_domain();
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
		if ( null !== $this->language_scope ) {
			( new Languages() )->leave( $this->language_scope );
			$this->language_scope = null;
		}
		remove_filter( 'plugin_locale', array( $this, 'plugin_locale' ) );
		$this->locale = '';
		$this->reload_domain();
		$this->reload_woocommerce_domain();
		if ( null !== $this->countries ) {
			WC()->countries  = $this->countries;
			$this->countries = null;
		}
	}

	/**
	 * Loads WooCommerce's own translations for the active locale. The caller
	 * may already have switched WordPress to this locale through the companion
	 * plugin, so WordPress's own switch is a no-op and does not reload loaded
	 * domains; the file is read directly, as this plugin's own domain is.
	 */
	private function reload_woocommerce_domain(): void {
		$locale = '' === $this->locale ? determine_locale() : $this->locale;
		unload_textdomain( 'woocommerce' );
		$files = array();
		if ( defined( 'WP_LANG_DIR' ) ) {
			$files[] = WP_LANG_DIR . '/plugins/woocommerce-' . $locale . '.mo';
		}
		if ( defined( 'WP_PLUGIN_DIR' ) ) {
			$files[] = WP_PLUGIN_DIR . '/woocommerce/i18n/languages/woocommerce-' . $locale . '.mo';
		}
		foreach ( $files as $mofile ) {
			if ( is_readable( $mofile ) ) {
				load_textdomain( 'woocommerce', $mofile );
				return;
			}
		}
		WC()->load_plugin_textdomain();
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

	/**
	 * The team's notification language: Chinese for the internal team (#74).
	 */
	public static function team_default(): string {
		$locale = get_option( 'linker_commerce_team_locale' );
		return is_string( $locale ) && '' !== $locale ? $locale : self::site_default();
	}
}
