<?php
/**
 * The site's languages and translation groups, as Polylang holds them.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * The plugin's one door to Polylang's API: languages, the language of an
 * object, and the English–German pairs.
 *
 * English is the language every object is written in (Polylang's default
 * language, set by `wp linker-i18n setup`); German is the language this plugin
 * produces. The site has these two (AGENTS.md §1: "英德同等").
 */
final class Languages {

	/**
	 * The language objects are written in.
	 */
	public const SOURCE = 'en';

	/**
	 * The language the plugin produces.
	 */
	public const TARGET = 'de';

	/**
	 * Whether Polylang runs and has both languages.
	 */
	public function ready(): bool {
		if ( ! function_exists( 'pll_languages_list' ) ) {
			return false;
		}
		$slugs = pll_languages_list();
		return in_array( self::SOURCE, $slugs, true ) && in_array( self::TARGET, $slugs, true );
	}

	/**
	 * The language of the current request: the URL's on the front end, the
	 * `lang` parameter's in REST; English when neither names one.
	 */
	public function current(): string {
		$language = function_exists( 'pll_current_language' ) ? pll_current_language() : false;
		return is_string( $language ) ? $language : self::SOURCE;
	}

	/**
	 * Whether the slug names a language of the site.
	 *
	 * @param string $slug Language slug.
	 */
	public function exists( string $slug ): bool {
		return function_exists( 'pll_languages_list' ) && in_array( $slug, pll_languages_list(), true );
	}

	/**
	 * The slug of a WordPress locale, null when the site has no such language
	 * (Polylang answers a slug, a locale or a term id; the locale is what the
	 * order meta records).
	 *
	 * @param string $locale Locale such as de_DE_formal.
	 */
	public function slug_of_locale( string $locale ): ?string {
		if ( ! function_exists( 'PLL' ) ) {
			return null;
		}
		$language = PLL()->model->get_language( $locale );
		if ( ! $language instanceof \PLL_Language ) {
			return null;
		}
		return $language->get_prop( 'slug' );
	}

	/**
	 * The language of a post, null when it has none.
	 *
	 * @param int $post_id Post ID.
	 */
	public function of_post( int $post_id ): ?string {
		$language = pll_get_post_language( $post_id );
		return is_string( $language ) ? $language : null;
	}

	/**
	 * The language of a term, null when it has none.
	 *
	 * @param int $term_id Term ID.
	 */
	public function of_term( int $term_id ): ?string {
		$language = pll_get_term_language( $term_id );
		return is_string( $language ) ? $language : null;
	}

	/**
	 * The post's translation in a language, null when there is none.
	 *
	 * @param int    $post_id  Post ID.
	 * @param string $language Language slug.
	 */
	public function post_translation( int $post_id, string $language ): ?int {
		$translation = pll_get_post( $post_id, $language );
		// A translation group can name a post deleted without Polylang running.
		return $translation > 0 && get_post( $translation ) instanceof \WP_Post ? $translation : null;
	}

	/**
	 * The term's translation in a language, null when there is none.
	 *
	 * @param int    $term_id  Term ID.
	 * @param string $language Language slug.
	 */
	public function term_translation( int $term_id, string $language ): ?int {
		$translation = pll_get_term( $term_id, $language );
		// A translation group can name a term deleted without Polylang running.
		return $translation > 0 && get_term( $translation ) instanceof \WP_Term ? $translation : null;
	}

	/**
	 * The English post of a German one (itself when it is English); null when
	 * the post has no language.
	 *
	 * @param int $post_id Post ID.
	 */
	public function source_post( int $post_id ): ?int {
		$language = $this->of_post( $post_id );
		if ( null === $language ) {
			return null;
		}
		return self::SOURCE === $language ? $post_id : $this->post_translation( $post_id, self::SOURCE );
	}

	/**
	 * Gives a post a language.
	 *
	 * @param int    $post_id  Post ID.
	 * @param string $language Language slug.
	 */
	public function set_post_language( int $post_id, string $language ): void {
		pll_set_post_language( $post_id, $language );
	}

	/**
	 * Gives a term a language.
	 *
	 * @param int    $term_id  Term ID.
	 * @param string $language Language slug.
	 */
	public function set_term_language( int $term_id, string $language ): void {
		pll_set_term_language( $term_id, $language );
	}

	/**
	 * Records an English post and its German version as one translation group.
	 *
	 * @param int $source_id English post ID.
	 * @param int $target_id German post ID.
	 */
	public function pair_posts( int $source_id, int $target_id ): void {
		pll_save_post_translations(
			array(
				self::SOURCE => $source_id,
				self::TARGET => $target_id,
			)
		);
	}

	/**
	 * Records an English term and its German version as one translation group.
	 *
	 * @param int $source_id English term ID.
	 * @param int $target_id German term ID.
	 */
	public function pair_terms( int $source_id, int $target_id ): void {
		pll_save_term_translations(
			array(
				self::SOURCE => $source_id,
				self::TARGET => $target_id,
			)
		);
	}

	/**
	 * Whether Polylang translates the post type.
	 *
	 * @param string $post_type Post type.
	 */
	public function translates_post_type( string $post_type ): bool {
		return pll_is_translated_post_type( $post_type );
	}

	/**
	 * Whether a post type belongs to the automatic content translator.
	 *
	 * @param string $post_type Post type.
	 */
	public function automatically_translates_post_type( string $post_type ): bool {
		return in_array( $post_type, TranslatedTypes::POST_TYPES, true ) && $this->translates_post_type( $post_type );
	}

	/**
	 * Whether Polylang translates the taxonomy.
	 *
	 * @param string $taxonomy Taxonomy.
	 */
	public function translates_taxonomy( string $taxonomy ): bool {
		return pll_is_translated_taxonomy( $taxonomy );
	}

	/**
	 * The WordPress locale of a language, e.g. de_DE_formal; empty when the
	 * language does not exist.
	 *
	 * @param string $language Language slug.
	 */
	public function locale( string $language ): string {
		$slugs   = pll_languages_list( array( 'fields' => 'slug' ) );
		$locales = pll_languages_list( array( 'fields' => 'locale' ) );
		$index   = array_search( $language, $slugs, true );
		return false !== $index && isset( $locales[ $index ] ) ? (string) $locales[ $index ] : '';
	}

	/**
	 * Makes a language the current one: WordPress's locale (gettext, dates),
	 * Polylang's current language and its string translations (the
	 * translated date and time formats). Undo with {@see self::leave()}.
	 *
	 * The string translations are loaded here, not left to the locale switch:
	 * in a REST request WordPress's locale can already be the target locale
	 * while Polylang holds the other language, and switch_to_locale() then
	 * does nothing.
	 *
	 * @param string $language Language slug.
	 * @return array{bool, mixed, string} Whether the locale was switched, Polylang's previous language and its locale ('' for none).
	 */
	public function enter( string $language ): array {
		$polylang        = PLL();
		$previous        = $polylang->curlang ?? null;
		$previous_locale = pll_current_language( 'locale' );
		$target          = $polylang->model->get_language( $language );
		if ( $target instanceof \PLL_Language ) {
			$polylang->curlang = $target;
		}
		$locale   = $this->locale( $language );
		$switched = '' !== $locale && switch_to_locale( $locale );
		$polylang->load_strings_translations( $locale );
		return array( $switched, $previous, is_string( $previous_locale ) ? $previous_locale : '' );
	}

	/**
	 * Undoes {@see self::enter()}.
	 *
	 * @param array{bool, mixed, string} $entered What enter() returned.
	 */
	public function leave( array $entered ): void {
		if ( $entered[0] ) {
			restore_previous_locale();
		}
		$polylang          = PLL();
		$polylang->curlang = $entered[1];
		$polylang->load_strings_translations( '' !== $entered[2] ? $entered[2] : determine_locale() );
	}

	/**
	 * The root URL of a language: http://host/ for English, http://host/de/
	 * for German. Polylang's links model, not pll_home_url(): with a static
	 * front page that answers with the front page's own link, which outside
	 * the front end is /de/home/.
	 *
	 * @param string $language Language slug.
	 */
	public function home_url( string $language ): string {
		return trailingslashit( PLL()->links_model->home_url( $language ) );
	}
}
