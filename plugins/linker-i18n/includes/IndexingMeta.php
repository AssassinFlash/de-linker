<?php
/**
 * Keep SEOPress's per-object indexing rule symmetric across a language pair.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use WP_Term;

/**
 * Mirrors `_seopress_robots_index` after metadata writes.
 *
 * Post saves do not necessarily update post content, so the normal
 * translation job is not a reliable observer for this metabox value. These
 * hooks cover adds, updates and deletes from either side of the pair. Terms
 * are included only for WordPress categories because that stored value is
 * the schema gate for the blog-category archive.
 */
final class IndexingMeta {

	/** SEOPress's per-object noindex value. */
	public const KEY = '_seopress_robots_index';

	/**
	 * Prevent a mirror write from re-entering this observer.
	 *
	 * @var bool
	 */
	private bool $writing = false;

	/**
	 * Sets up the mirror.
	 *
	 * @param Languages $languages The site's object pairs.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/** Adds the post and blog-category term observers. */
	public function register(): void {
		foreach ( array( 'added_post_meta', 'updated_post_meta' ) as $hook ) {
			add_action( $hook, array( $this, 'post_changed' ), 10, 4 );
		}
		add_action( 'deleted_post_meta', array( $this, 'post_deleted' ), 10, 4 );
		foreach ( array( 'added_term_meta', 'updated_term_meta' ) as $hook ) {
			// After Polylang's own term-meta synchronisation has finished.
			add_action( $hook, array( $this, 'term_changed' ), 99, 4 );
		}
		add_action( 'deleted_term_meta', array( $this, 'term_deleted' ), 99, 4 );
	}

	/**
	 * Mirrors a newly written post value.
	 *
	 * @param int    $meta_id    Metadata row ID, unused.
	 * @param int    $post_id    Post whose metadata changed.
	 * @param string $meta_key   Metadata key.
	 * @param mixed  $meta_value Stored value.
	 */
	public function post_changed( int $meta_id, int $post_id, string $meta_key, mixed $meta_value ): void {
		unset( $meta_id );
		$this->mirror_post( $post_id, $meta_key, $meta_value );
	}

	/**
	 * Mirrors a post deletion.
	 *
	 * @param mixed  $meta_ids   Deleted metadata row IDs, unused.
	 * @param int    $post_id    Post whose metadata changed.
	 * @param string $meta_key   Metadata key.
	 * @param mixed  $meta_value Deleted value, unused.
	 */
	public function post_deleted( mixed $meta_ids, int $post_id, string $meta_key, mixed $meta_value ): void {
		unset( $meta_ids, $meta_value );
		$this->mirror_post( $post_id, $meta_key, null );
	}

	/**
	 * Mirrors a newly written blog-category value.
	 *
	 * @param int    $meta_id  Metadata row ID, unused.
	 * @param int    $term_id  Term whose metadata changed.
	 * @param string $meta_key Metadata key.
	 * @param mixed  $meta_value Stored value.
	 */
	public function term_changed( int $meta_id, int $term_id, string $meta_key, mixed $meta_value ): void {
		unset( $meta_id );
		$this->mirror_term( $term_id, $meta_key, $meta_value );
	}

	/**
	 * Mirrors a blog-category deletion.
	 *
	 * @param mixed  $meta_ids   Deleted metadata row IDs, unused.
	 * @param int    $term_id    Term whose metadata changed.
	 * @param string $meta_key   Metadata key.
	 * @param mixed  $meta_value Deleted value, unused.
	 */
	public function term_deleted( mixed $meta_ids, int $term_id, string $meta_key, mixed $meta_value ): void {
		unset( $meta_ids, $meta_value );
		$this->mirror_term( $term_id, $meta_key, null );
	}

	/**
	 * Writes the same post value to the other language, or removes both.
	 *
	 * @param int    $post_id Post whose metadata changed.
	 * @param string $meta_key Metadata key.
	 * @param mixed  $value    New value; null means absence.
	 */
	private function mirror_post( int $post_id, string $meta_key, mixed $value ): void {
		if ( $this->writing || self::KEY !== $meta_key ) {
			return;
		}
		$language = $this->languages->of_post( $post_id );
		$other    = Languages::SOURCE === $language ? Languages::TARGET : Languages::SOURCE;
		if ( ! in_array( $language, array( Languages::SOURCE, Languages::TARGET ), true ) ) {
			return;
		}
		$counterpart = $this->languages->post_translation( $post_id, $other );
		if ( null === $counterpart ) {
			return;
		}
		$desired = $this->desired( $value );
		if ( get_post_meta( $counterpart, self::KEY, true ) === $desired ) {
			return;
		}
		$this->writing = true;
		try {
			if ( null === $desired ) {
				delete_post_meta( $counterpart, self::KEY );
			} else {
				update_post_meta( $counterpart, self::KEY, wp_slash( $desired ) );
			}
		} finally {
			$this->writing = false;
		}
	}

	/**
	 * Writes the same WordPress-category value to the other language, or
	 * removes both.
	 *
	 * @param int    $term_id  Term whose metadata changed.
	 * @param string $meta_key Metadata key.
	 * @param mixed  $value    New value; null means absence.
	 */
	private function mirror_term( int $term_id, string $meta_key, mixed $value ): void {
		if ( $this->writing || self::KEY !== $meta_key ) {
			return;
		}
		$term = get_term( $term_id );
		if ( ! $term instanceof WP_Term || 'category' !== $term->taxonomy ) {
			return;
		}
		$language = $this->languages->of_term( $term_id );
		$other    = Languages::SOURCE === $language ? Languages::TARGET : Languages::SOURCE;
		if ( ! in_array( $language, array( Languages::SOURCE, Languages::TARGET ), true ) ) {
			return;
		}
		$counterpart = $this->languages->term_translation( $term_id, $other );
		if ( null === $counterpart ) {
			return;
		}
		$desired = $this->desired( $value );
		if ( get_term_meta( $counterpart, self::KEY, true ) === $desired ) {
			return;
		}
		$this->writing = true;
		try {
			if ( null === $desired ) {
				delete_term_meta( $counterpart, self::KEY );
			} else {
				update_term_meta( $counterpart, self::KEY, wp_slash( $desired ) );
			}
		} finally {
			$this->writing = false;
		}
	}

	/**
	 * The stored value to mirror: SEOPress uses `yes`, while null/empty means
	 * the key must be absent on both objects.
	 *
	 * @param mixed $value Changed value.
	 */
	private function desired( mixed $value ): ?string {
		return is_string( $value ) && '' !== $value ? $value : null;
	}
}
