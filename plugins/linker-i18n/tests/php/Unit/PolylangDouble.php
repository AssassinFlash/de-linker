<?php
/**
 * A stand-in for Polylang's API in unit tests.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Mockery;
use WP_Mock;

/**
 * Mocks the pll_*() functions and PLL() over a small site: English and
 * German, http://example.test/ and http://example.test/de/, and the
 * languages and translation pairs a test gives.
 */
final class PolylangDouble {

	public const HOME = 'http://example.test/';

	/**
	 * The site's languages and their locales.
	 */
	private const LOCALES = array(
		'en' => 'en_US',
		'de' => 'de_DE_formal',
	);

	/**
	 * The PLL() object of the current test.
	 *
	 * @var PolylangInstance
	 */
	public static PolylangInstance $polylang;

	/**
	 * The pll_set_post_language() calls of the current test: post ID => language.
	 *
	 * @var array<int, string>
	 */
	public static array $set_post_language = array();

	/**
	 * The pll_save_post_translations() calls of the current test, in order.
	 *
	 * @var list<array<string, int>>
	 */
	public static array $saved_post_translations = array();

	/**
	 * The language objects of the current test, by slug: one object per
	 * language, so a test can tell which one is current.
	 *
	 * @var array<string, \PLL_Language>
	 */
	private static array $languages = array();

	/**
	 * Mocks Polylang.
	 *
	 * @param array<int, string>               $post_languages Post ID => language.
	 * @param array<int, int>                  $post_pairs     English post ID => German post ID.
	 * @param array<int, string>               $term_languages Term ID => language.
	 * @param array<int, int>                  $term_pairs     English term ID => German term ID.
	 * @param string                           $current        The current language.
	 * @param array<string, bool>              $translated     Post type or taxonomy => whether Polylang translates it.
	 * @param array<int, array<string, mixed>> $posts Fields of the post get_post() returns, by ID.
	 */
	public static function mock( array $post_languages = array(), array $post_pairs = array(), array $term_languages = array(), array $term_pairs = array(), string $current = 'en', array $translated = array(), array $posts = array() ): void {
		$translates = static fn( string $type ): bool => $translated[ $type ] ?? in_array( $type, array( 'page', 'post', 'product', 'product_cat', 'category', 'pa_phase' ), true );
		$pair       = static function ( array $pairs, array $languages, int $id, string $language ) {
			if ( ( $languages[ $id ] ?? null ) === $language ) {
				return $id;
			}
			if ( 'de' === $language && isset( $pairs[ $id ] ) ) {
				return $pairs[ $id ];
			}
			$english = array_search( $id, $pairs, true );
			return 'en' === $language && false !== $english ? $english : 0;
		};
		WP_Mock::userFunction(
			'pll_languages_list',
			array(
				'return' => static fn( array $args = array() ): array => 'locale' === ( $args['fields'] ?? 'slug' ) ? array_values( self::LOCALES ) : array_keys( self::LOCALES ),
			)
		);
			WP_Mock::userFunction(
				'pll_current_language',
				array(
					'return' => static function ( string $field = 'slug' ) use ( $current ): string {
						// The current language is the one PLL() holds, so a test
						// that moves it (as Languages::enter() does) is answered
						// the same way Polylang answers.
						$held = self::$polylang->curlang->get_prop( 'slug' );
						$slug = is_string( $held ) && '' !== $held ? $held : $current;
						return 'locale' === $field ? self::LOCALES[ $slug ] : $slug;
					},
				)
			);
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => static fn( int $id ) => $post_languages[ $id ] ?? false ) );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => static fn( int $id ) => $term_languages[ $id ] ?? false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn( int $id, string $language ) => $pair( $post_pairs, $post_languages, $id, $language ) ) );
		WP_Mock::userFunction( 'pll_get_term', array( 'return' => static fn( int $id, string $language ) => $pair( $term_pairs, $term_languages, $id, $language ) ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => $translates ) );
		WP_Mock::userFunction( 'pll_is_translated_taxonomy', array( 'return' => $translates ) );
		WP_Mock::userFunction( 'get_post', array( 'return' => static fn( $id ) => isset( $post_languages[ (int) $id ] ) || isset( $posts[ (int) $id ] ) ? self::post( (int) $id, $posts[ (int) $id ] ?? array() ) : null ) );
		self::$set_post_language       = array();
		self::$saved_post_translations = array();
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => static function ( int $id, string $slug ): bool {
					self::$set_post_language[ $id ] = $slug;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'pll_save_post_translations',
			array(
				'return' => static function ( array $map ): void {
					self::$saved_post_translations[] = $map;
				},
			)
		);
		WP_Mock::userFunction( 'get_term', array( 'return' => static fn( $id ) => isset( $term_languages[ (int) $id ] ) ? self::term( (int) $id ) : null ) );
		self::$languages = array();
		self::$polylang  = new PolylangInstance( self::language( $current ) );
		WP_Mock::userFunction( 'PLL', array( 'return' => self::$polylang ) );
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
	}

	/**
	 * The language object of a slug.
	 *
	 * @param string $slug Language slug.
	 */
	public static function language( string $slug ): \PLL_Language {
		if ( ! isset( self::$languages[ $slug ] ) ) {
			$language = Mockery::mock( \PLL_Language::class );
			// The slug is the object's own answer; a test can override the expectation.
			$language->shouldReceive( 'get_prop' )->with( 'slug' )->andReturn( $slug )->byDefault();
			self::$languages[ $slug ] = $language;
		}
		return self::$languages[ $slug ];
	}

	/**
	 * A post object (WordPress's class does not exist in unit tests).
	 *
	 * @param int                  $id     Post ID.
	 * @param array<string, mixed> $fields Other fields.
	 * @return \WP_Post
	 */
	public static function post( int $id, array $fields = array() ) {
		$post     = Mockery::mock( 'WP_Post' );
		$post->ID = $id;
		foreach ( $fields as $field => $value ) {
			$post->$field = $value;
		}
		return $post;
	}

	/**
	 * A term object.
	 *
	 * @param int                  $id     Term ID.
	 * @param array<string, mixed> $fields Other fields.
	 * @return \WP_Term
	 */
	public static function term( int $id, array $fields = array() ) {
		$term          = Mockery::mock( 'WP_Term' );
		$term->term_id = $id;
		foreach ( $fields as $field => $value ) {
			$term->$field = $value;
		}
		return $term;
	}
}
