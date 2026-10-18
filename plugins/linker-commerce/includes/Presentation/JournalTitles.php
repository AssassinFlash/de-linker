<?php
/**
 * Reviewed discovery labels without changing native document titles.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/** Only data: LC owns placement and WindPress owns the visual treatment. */
final class JournalTitles {

	/** Extend LC/Tangible's native post-field interface, without a new loop. */
	public static function register(): void {
		if ( ! function_exists( 'tangible_loop' ) ) {
			return;
		}
		$loop = tangible_loop();
		if ( $loop instanceof \stdClass && isset( $loop->add_field_filter ) && is_callable( $loop->add_field_filter ) ) {
			call_user_func( $loop->add_field_filter, 'post', array( self::class, 'field' ) );
		}
	}

	/**
	 * Read only this field; native fields continue through Tangible unchanged.
	 *
	 * @param mixed  $item The native loop's current item.
	 * @param string $field Requested field name.
	 */
	public static function field( mixed $item, string $field ): ?string {
		return 'journal_title' === $field && $item instanceof \WP_Post ? esc_html( self::label( $item ) ) : null;
	}

	/**
	 * Resolve copy by English source identity and the post's own native language.
	 *
	 * @param \WP_Post $post Native post, never a title inferred from the request.
	 */
	public static function label( \WP_Post $post ): string {
		$title = (string) get_the_title( $post );
		if ( ! function_exists( 'pll_get_post_language' ) || ! function_exists( 'pll_get_post' ) ) {
			return $title;
		}
		$language = pll_get_post_language( $post->ID );
		if ( ! in_array( $language, array( 'en', 'de' ), true ) ) {
			return $title;
		}
		$source = 'en' === $language ? $post : get_post( (int) pll_get_post( $post->ID, 'en' ) );
		if ( ! $source instanceof \WP_Post ) {
			return $title;
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Reviewed, checked-in presentation copy.
		$labels = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/content/journal-titles.json' ), true, 512, JSON_THROW_ON_ERROR );
		$entry  = $labels[ $source->post_name ] ?? null;
		return is_array( $entry ) && ( $entry['full'][ $language ] ?? '' ) === $title ? (string) $entry['label'][ $language ] : $title;
	}
}
