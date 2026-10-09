<?php
/**
 * Polylang's configuration for the site.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Puts Polylang into the configuration the site runs with
 * (docs/specs/9-i18n.md, "Polylang 配置"): English as the default language
 * without a URL prefix, German under /de/ with the formal locale, the
 * language from the directory, no browser-language redirect, media not
 * translated, and the synchronised fields. It goes through Polylang's own
 * REST API (pll/v1/languages and pll/v1/settings, free since Polylang 3.7;
 * docs/research/2026-10-09/i18n-opensource-replication.md §2.2), applied by
 * `wp linker-i18n setup` on a local instance and at the cutover, never
 * clicked in the settings screen.
 */
final class Setup {

	/**
	 * The languages. de_DE_formal is the Sie form of WordPress's and
	 * WooCommerce's German language packs (AGENTS.md §3).
	 */
	public const LANGUAGES = array(
		array(
			'name'       => 'English',
			'slug'       => Languages::SOURCE,
			'locale'     => 'en_US',
			'flag'       => 'gb',
			'term_group' => 0,
		),
		array(
			'name'       => 'Deutsch',
			'slug'       => Languages::TARGET,
			'locale'     => 'de_DE_formal',
			'flag'       => 'de',
			'term_group' => 1,
		),
	);

	/**
	 * Polylang options: English is the default language; the language comes
	 * from the directory (force_lang 1), English without /en/ (hide_default),
	 * no /language/ in URLs (rewrite); the German front page at /de/ rather
	 * than /de/<page slug>/ (redirect_lang: "The front page URL contains the
	 * language code instead of the page name"; /de/ is the live German home);
	 * no browser detection (a redirect by a guessed language makes pages
	 * uncacheable and is against Google's advice; §6.3 of the research);
	 * media shared by both languages; and the synchronised fields: taxonomies,
	 * page parent and template, menu order, featured image, comment status.
	 */
	public const OPTIONS = array(
		'default_lang'  => Languages::SOURCE,
		'force_lang'    => 1,
		'hide_default'  => true,
		'rewrite'       => true,
		'redirect_lang' => true,
		'browser'       => false,
		'media_support' => false,
		'sync'          => array( 'taxonomies', 'post_parent', '_wp_page_template', 'menu_order', '_thumbnail_id', 'comment_status' ),
	);

	/**
	 * Creates or corrects the languages and sets the options. Needs a user who
	 * may manage options (`wp linker-i18n setup --user=<admin>`).
	 *
	 * @return array<int, string> What was done or went wrong, for the command line.
	 */
	public function apply(): array {
		$log      = array();
		$existing = array();
		$listed   = $this->request( 'GET', '/pll/v1/languages' );
		foreach ( is_array( $listed ) ? $listed : array() as $language ) {
			if ( is_array( $language ) && isset( $language['slug'], $language['term_id'] ) ) {
				$existing[ (string) $language['slug'] ] = $language;
			}
		}
		foreach ( self::LANGUAGES as $language ) {
			$current = $existing[ $language['slug'] ] ?? null;
			if ( null === $current ) {
				$log[] = $this->outcome( $this->request( 'POST', '/pll/v1/languages', $language ), 'added language ' . $language['slug'] . ' (' . $language['locale'] . ')' );
			} elseif ( ( $current['locale'] ?? '' ) !== $language['locale'] || ( $current['name'] ?? '' ) !== $language['name'] ) {
				$log[] = $this->outcome( $this->request( 'PUT', '/pll/v1/languages/' . (int) $current['term_id'], $language ), 'updated language ' . $language['slug'] . ' (' . $language['locale'] . ')' );
			}
		}
		$log[] = $this->drop_default_terms();
		$log[] = $this->outcome( $this->request( 'POST', '/pll/v1/settings', self::OPTIONS ), 'options set' );
		// Polylang caches each language's home URL, which depends on the options.
		PLL()->model->clean_languages_cache();
		$log[] = $this->german_formats();
		flush_rewrite_rules( false );
		return $log;
	}

	/**
	 * Deletes the default terms Polylang makes for German when the language is
	 * created (Polylang's src/default-term.php: an "Uncategorized" with the
	 * slug uncategorized-de for every taxonomy with a default_<taxonomy>
	 * option - category from WordPress, product_cat from WooCommerce). The
	 * German shop has nothing in them and their archives are not among the
	 * site's German URLs, so the migration's verify reports them; WordPress's
	 * own default terms stay. Empty German terms only: one that holds objects
	 * is somebody's content.
	 *
	 * @return string What was removed, for the command line.
	 */
	public function drop_default_terms(): string {
		$removed = array();
		foreach ( PLL()->model->get_translated_taxonomies() as $taxonomy ) {
			if ( '' === $taxonomy ) {
				continue;
			}
			$default = (int) get_option( 'default_' . $taxonomy );
			$german  = $default ? pll_get_term( $default, Languages::TARGET ) : 0;
			if ( $german === $default ) {
				continue;
			}
			$term = $german > 0 ? get_term( $german ) : null;
			if ( $term instanceof \WP_Term && 0 === $term->count ) {
				$removed[] = $taxonomy . ':' . $term->slug;
				wp_delete_term( $term->term_id, $taxonomy );
			}
		}
		return array() === $removed
			? 'default terms: none to remove'
			: 'default terms removed: ' . implode( ', ', $removed );
	}

	/**
	 * German date and time formats: WordPress's German (Formal) core
	 * translation turns the default "F j, Y" and "g:i a" into "j. F Y" and
	 * "G:i" (de_DE_formal.po, msgid from wp-admin/includes/schema.php).
	 */
	public const GERMAN_FORMATS = array(
		'date_format' => 'j. F Y',
		'time_format' => 'G:i',
	);

	/**
	 * Sets the German date and time formats as Polylang string translations of
	 * the site's formats (Polylang translates both options per language).
	 *
	 * @return string What was done, for the command line.
	 */
	public function german_formats(): string {
		$language = PLL()->model->get_language( Languages::TARGET );
		if ( ! $language instanceof \PLL_Language ) {
			return 'error: no German language';
		}
		$strings = new \PLL_MO();
		$strings->import_from_db( $language );
		foreach ( self::GERMAN_FORMATS as $option => $format ) {
			$strings->add_entry( $strings->make_entry( (string) get_option( $option ), $format ) );
		}
		$strings->export_to_db( $language );
		return 'German date and time formats set';
	}

	/**
	 * Gives every post and term of a translated type that has no language the
	 * default language, English. Polylang's front end shows only objects with
	 * a language (§2.4 of the research).
	 */
	public function assign_default(): void {
		PLL()->model->set_language_in_mass();
		// Polylang's mass assignment writes term_relationships directly,
		// without the object-cache invalidation wp_set_object_terms() does:
		// with a persistent object cache (Redis, as the cutover plans for
		// production; docs/specs/17-cutover.md) a page whose language was read
		// before this - the front page, the posts page, the shop page, which
		// every request reads - keeps its cached "no language" answer, and the
		// German versions cannot pair with them. One flush, once, here.
		wp_cache_flush();
	}

	/**
	 * Runs a request against the site's own REST API.
	 *
	 * @param string               $method HTTP method.
	 * @param string               $route  Route.
	 * @param array<string, mixed> $params Body parameters.
	 * @return mixed The response data, or a WP_Error.
	 */
	private function request( string $method, string $route, array $params = array() ) {
		$request = new \WP_REST_Request( $method, $route );
		foreach ( $params as $key => $value ) {
			$request->set_param( $key, $value );
		}
		$response = rest_do_request( $request );
		return $response->is_error() ? $response->as_error() : $response->get_data();
	}

	/**
	 * A line for the log.
	 *
	 * @param mixed  $result  Response data or a WP_Error.
	 * @param string $success What was done.
	 */
	private function outcome( $result, string $success ): string {
		return is_wp_error( $result ) ? 'error: ' . $result->get_error_message() : $success;
	}
}
