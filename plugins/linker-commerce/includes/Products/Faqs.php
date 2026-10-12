<?php
/**
 * The product FAQ field written by ticket #15.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * One reading of the product FAQ list (docs/specs/15-faq.md): the meta
 * `_linker_faqs`, a JSON list of {question, answer, question_de, answer_de,
 * citation{url, page, title?}}. The product edit box and tools/faq/import.py
 * write it; the product page reads it.
 */
final class Faqs {

	/**
	 * Product meta that holds the FAQ list.
	 */
	public const META_KEY = '_linker_faqs';

	/**
	 * The FAQ items of a product, in stored order; malformed rows are dropped.
	 *
	 * @param int $product_id Product ID.
	 * @return list<array{question: string, answer: string, question_de: string, answer_de: string, citation: array{url: string, page: int, title?: string}}>
	 */
	public static function of( int $product_id ): array {
		$value = get_post_meta( $product_id, self::META_KEY, true );
		if ( is_string( $value ) ) {
			$value = json_decode( $value, true );
		}

		return self::normalize( is_array( $value ) ? $value : array() );
	}

	/**
	 * The well-formed items of a decoded list.
	 *
	 * @param array<int|string, mixed> $items Decoded JSON.
	 * @return list<array{question: string, answer: string, question_de: string, answer_de: string, citation: array{url: string, page: int, title?: string}}>
	 */
	public static function normalize( array $items ): array {
		$out = array();
		foreach ( $items as $item ) {
			$row = self::item( $item );
			if ( null !== $row ) {
				$out[] = $row;
			}
		}

		return $out;
	}

	/**
	 * JSON of a list of items, the form stored in post meta. Rows that fail
	 * `item()` are dropped, so the caller may hand a decoded list as-is.
	 *
	 * @param array<int|string, mixed> $items Items already normalized or as posted.
	 */
	public static function encode( array $items ): string {
		return (string) wp_json_encode( self::normalize( $items ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
	}

	/**
	 * Copies a written list onto the Polylang twin, so the German product
	 * serves the same FAQ as the English one (docs/specs/15-faq.md: the
	 * German object follows #9). The one mirror every writer rides: the
	 * product edit box (FaqsMetaBox) and tools/faq/import.py. Silent without
	 * Polylang, without a twin, or when the post is its own twin.
	 *
	 * @param int    $post_id English or German product ID.
	 * @param string $json    Encoded list, as `encode()` returns it.
	 */
	public static function mirror_to_twin( int $post_id, string $json ): void {
		if ( ! function_exists( 'pll_get_post_language' ) || ! function_exists( 'pll_get_post' ) ) {
			return;
		}
		$language = pll_get_post_language( $post_id );
		$twin_of  = 'en' === $language ? 'de' : ( 'de' === $language ? 'en' : '' );
		if ( '' === $twin_of ) {
			return;
		}
		$twin = pll_get_post( $post_id, $twin_of );
		if ( $twin > 0 && (int) $twin !== $post_id ) {
			update_post_meta( (int) $twin, self::META_KEY, wp_slash( $json ) );
		}
	}

	/**
	 * One item, or null when it has no English question or no citation.
	 *
	 * @param mixed $item Decoded row.
	 * @return array{question: string, answer: string, question_de: string, answer_de: string, citation: array{url: string, page: int, title?: string}}|null
	 */
	private static function item( mixed $item ): ?array {
		if ( ! is_array( $item ) ) {
			return null;
		}
		$question = trim( (string) ( $item['question'] ?? '' ) );
		$citation = is_array( $item['citation'] ?? null ) ? $item['citation'] : array();
		$url      = trim( (string) ( $citation['url'] ?? '' ) );
		$page     = $citation['page'] ?? 0;
		$page     = is_numeric( $page ) ? (int) $page : 0;
		if ( '' === $question || '' === $url || $page < 1 ) {
			return null;
		}
		$row   = array(
			'question'    => $question,
			'answer'      => (string) ( $item['answer'] ?? '' ),
			'question_de' => (string) ( $item['question_de'] ?? '' ),
			'answer_de'   => (string) ( $item['answer_de'] ?? '' ),
			'citation'    => array(
				'url'  => $url,
				'page' => $page,
			),
		);
		$title = trim( (string) ( $citation['title'] ?? '' ) );
		if ( '' !== $title ) {
			$row['citation']['title'] = $title;
		}

		return $row;
	}
}
