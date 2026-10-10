<?php
/**
 * Polylang's main object in unit tests.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

/**
 * What the plugin uses of PLL(): the current language, the model's languages,
 * the links model's root URLs, and the string translations it loads.
 */
final class PolylangInstance {

	/**
	 * Locales whose string translations were loaded, in order.
	 *
	 * @var list<string>
	 */
	public array $loaded = array();

	/**
	 * The model: the language objects by slug.
	 *
	 * @var object
	 */
	public object $model;

	/**
	 * The links model: the root URL of a language.
	 *
	 * @var object
	 */
	public object $links_model;

	/**
	 * Sets up the double.
	 *
	 * @param mixed $curlang Current language.
	 */
	public function __construct( public mixed $curlang ) {
		$this->model       = new class() {
			/**
			 * A language by slug.
			 *
			 * @param string $slug Slug.
			 * @return \PLL_Language|false
			 */
			public function get_language( string $slug ) {
				return in_array( $slug, array( 'en', 'de' ), true ) ? PolylangDouble::language( $slug ) : false;
			}
		};
		$this->links_model = new class() {
			/**
			 * The root URL of a language.
			 *
			 * @param string $language Language slug.
			 */
			public function home_url( string $language ): string {
				return 'en' === $language ? PolylangDouble::HOME : PolylangDouble::HOME . $language . '/';
			}
		};
	}

	/**
	 * Records a load of string translations.
	 *
	 * @param string $locale Locale.
	 */
	public function load_strings_translations( string $locale ): void {
		$this->loaded[] = $locale;
	}
}
