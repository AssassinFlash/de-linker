<?php
/**
 * One slug for an English term and its German version.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\SameSlug;

use Linker\I18n\Languages;

/**
 * Lets a term be saved with a slug that only a term of the other language
 * holds.
 *
 * `wp_update_term()` refuses a slug that any term of the taxonomy holds
 * ("The slug … is already in use by another term"); it looks with
 * `get_term_by( 'slug' )` right after the `wp_update_term_parent` filter.
 * This class narrows that one lookup to the term's own language. Of the ten
 * live German product categories, ems-monitoring keeps its English slug
 * (docs/research/2026-10-09/i18n-opensource-replication.md §5.2).
 */
final class TermSlugs {

	/**
	 * Language of the term `wp_update_term()` is checking, until its slug lookup runs.
	 *
	 * @var string|null
	 */
	private ?string $checking = null;

	/**
	 * Sets up the filters.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * Notes the language of the term being updated (filter `wp_update_term_parent`).
	 *
	 * @param int    $parent_id Parent term ID.
	 * @param int    $term_id   Term ID.
	 * @param string $taxonomy  Taxonomy.
	 */
	public function note( int $parent_id, int $term_id, string $taxonomy ): int {
		$this->checking = $this->languages->translates_taxonomy( $taxonomy ) ? $this->languages->of_term( $term_id ) : null;
		return $parent_id;
	}

	/**
	 * Limits the next slug lookup to the noted language (filter `get_terms_args`).
	 *
	 * @param array<string, mixed> $args Term query arguments.
	 * @return array<string, mixed>
	 */
	public function narrow( array $args ): array {
		if ( null === $this->checking || empty( $args['slug'] ) ) {
			return $args;
		}
		$args['lang']   = $this->checking;
		$this->checking = null;
		return $args;
	}
}
