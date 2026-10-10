<?php
/**
 * Titles, URLs and term names of a product, in the page language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * The language of an ability request is `en` or `de`. Titles and permalinks
 * follow the translated product when Polylang is loaded (#9); otherwise the
 * stored post.
 */
final class CatalogText {

	/**
	 * `en` or `de`; anything else is English.
	 *
	 * @param mixed $lang Requested language.
	 * @return 'en'|'de'
	 */
	public static function lang( mixed $lang ): string {
		return is_string( $lang ) && str_starts_with( strtolower( $lang ), 'de' ) ? 'de' : 'en';
	}

	/**
	 * The product shown for `$lang`: the Polylang translation when there is one.
	 *
	 * @param int       $product_id Product ID.
	 * @param 'en'|'de' $lang       Language.
	 */
	public static function translated_id( int $product_id, string $lang ): int {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return $product_id;
		}
			$translated = pll_get_post( $product_id, 'de' === $lang ? 'de' : 'en' );

			return 0 < $translated ? $translated : $product_id;
	}

	/**
	 * Product title in `$lang`.
	 *
	 * @param int       $product_id Product ID.
	 * @param 'en'|'de' $lang       Language.
	 */
	public static function title( int $product_id, string $lang ): string {
		return (string) get_the_title( self::translated_id( $product_id, $lang ) );
	}

	/**
	 * Permalink of the product in `$lang` when translated, otherwise the stored post.
	 *
	 * @param int            $product_id Product ID.
	 * @param 'en'|'de'|null $lang    Language; omitted uses the stored post.
	 */
	public static function url( int $product_id, ?string $lang = null ): string {
		$id  = null === $lang ? $product_id : self::translated_id( $product_id, $lang );
		$url = get_permalink( $id );

		return is_string( $url ) ? $url : '';
	}

	/**
	 * Name of the product's single term in a taxonomy, null without one.
	 *
	 * @param int    $product_id Product ID.
	 * @param string $taxonomy   Taxonomy.
	 */
	public static function term_name( int $product_id, string $taxonomy ): ?string {
		$terms = get_the_terms( $product_id, $taxonomy );
		if ( ! is_array( $terms ) || 1 !== count( $terms ) ) {
			return null;
		}
			$name = reset( $terms )->name;

			return '' === $name ? null : $name;
	}

	/**
	 * Slugs of the product's terms in a taxonomy.
	 *
	 * @param int    $product_id Product ID.
	 * @param string $taxonomy   Taxonomy.
	 * @return list<string>
	 */
	public static function term_slugs( int $product_id, string $taxonomy ): array {
		$terms = get_the_terms( $product_id, $taxonomy );
		$slugs = array();
		foreach ( is_array( $terms ) ? $terms : array() as $term ) {
			if ( '' !== $term->slug ) {
				$slugs[] = $term->slug;
			}
		}

		return $slugs;
	}
}
