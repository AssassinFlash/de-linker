<?php
/**
 * Native content for mixed search results.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\Publication;

/** Fields of the current post in the LiveCanvas results loop. */
final class SearchResult {

	/**
	 * Resolve the source product SKU or the current language's short description.
	 *
	 * @param mixed  $item Native loop item.
	 * @param string $field Requested field.
	 */
	public static function field( mixed $item, string $field ): ?string {
		if ( ! $item instanceof \WP_Post ) {
			return null;
		}
		if ( 'linker_search_sku' === $field ) {
			return 'product' === $item->post_type ? esc_html( (string) get_post_meta( Publication::canonical_id( $item->ID ), '_sku', true ) ) : '';
		}
		if ( 'linker_search_summary' !== $field ) {
			return null;
		}
		$text = $item->post_excerpt;
		if ( '' === trim( $text ) ) {
			$text = (string) get_post_meta( $item->ID, '_seopress_titles_desc', true );
		}
		if ( '' === trim( $text ) ) {
			$text = strip_shortcodes( $item->post_content );
		}
		return esc_html( wp_trim_words( wp_strip_all_tags( $text, true ), 24, '…' ) );
	}
}
