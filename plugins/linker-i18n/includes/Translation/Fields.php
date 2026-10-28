<?php
/**
 * The translatable fields of posts and terms.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Says which fields of an object are text for people, and whether each is
 * HTML or plain text.
 */
final class Fields {

	/**
	 * SEOPress's per-post title and description fields (the site runs
	 * SEOPress; docs/research/2026-10-09/i18n-opensource-replication.md §7.2).
	 */
	public const SEO_META = array(
		'_seopress_titles_title',
		'_seopress_titles_desc',
		'_seopress_social_fb_title',
		'_seopress_social_fb_desc',
		'_seopress_social_twitter_title',
		'_seopress_social_twitter_desc',
	);

	/**
	 * Prefix of field names that are post meta.
	 */
	public const META = 'meta:';

	/** German post meta for the translation of a blog post's featured-image alt. */
	public const COVER_ALT = '_linker_i18n_cover_alt';

	/**
	 * The fields of a post: title, excerpt (a product's short description),
	 * content (a product's description) and the translatable meta that has
	 * a value.
	 *
	 * @param \WP_Post $post Post.
	 * @param bool     $target Whether this is the German post rather than the source.
	 * @return array<string, array{string, bool}> Field => [value, whether it is HTML].
	 */
	public function of_post( \WP_Post $post, bool $target = false ): array {
		$fields = array(
			'post_title'   => array( $post->post_title, false ),
			'post_excerpt' => array( $post->post_excerpt, true ),
			'post_content' => array( $post->post_content, true ),
		);
		foreach ( $this->meta_keys( $post ) as $key ) {
			$value = get_post_meta( $post->ID, $key, true );
			if ( is_string( $value ) && '' !== trim( $value ) ) {
				$fields[ self::META . $key ] = array( $value, false );
			}
		}
		if ( 'post' === $post->post_type ) {
			$image = (int) get_post_thumbnail_id( $post->ID );
			$alt   = $target ? get_post_meta( $post->ID, self::COVER_ALT, true ) : ( $image ? get_post_meta( $image, '_wp_attachment_image_alt', true ) : '' );
			// Include emptiness: removing the source alt must clear its translation.
			$fields[ self::META . self::COVER_ALT ] = array( is_string( $alt ) ? $alt : '', false );
		}
		return $fields;
	}

	/**
	 * The fields of a term: name and description.
	 *
	 * @param \WP_Term $term Term.
	 * @return array<string, array{string, bool}> Field => [value, whether it is HTML].
	 */
	public function of_term( \WP_Term $term ): array {
		return array(
			'name'        => array( $term->name, false ),
			'description' => array( $term->description, true ),
		);
	}

	/**
	 * The meta keys translated for a post. Other plugins add theirs with the
	 * filter `linker_i18n_translatable_meta` (a key whose value is plain text).
	 *
	 * @param \WP_Post $post Post.
	 * @return list<string>
	 */
	public function meta_keys( \WP_Post $post ): array {
		/**
		 * Filters the meta keys whose plain-text values the German version of a post gets translated.
		 *
		 * @since 0.2.0
		 *
		 * @param string[] $keys Meta keys.
		 * @param \WP_Post $post The English post.
		 */
		$keys = apply_filters( 'linker_i18n_translatable_meta', self::SEO_META, $post );
		return array_values( $keys );
	}
}
