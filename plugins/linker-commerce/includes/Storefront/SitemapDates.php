<?php
/**
 * Modification dates of public WooCommerce and journal archives by language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/** One aggregate serves the whole sitemap, including parents with models only in child terms. */
final class SitemapDates {
	/**
	 * GMT dates by archive, term and language.
	 *
	 * @var array<string,array<int,array<string,string>>>
	 */
	private array $dates = array();

	/** Read the native language and catalogue relationships together. */
	public function __construct() {
		global $wpdb;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- The archive maxima need one grouped read across post, language and catalog terms.
		$rows = $wpdb->get_results(
			"SELECT p.post_type, t.taxonomy, t.term_id, l.slug AS lang, MAX(p.post_modified_gmt) AS modified
			FROM {$wpdb->posts} p
			JOIN {$wpdb->term_relationships} lr ON lr.object_id = p.ID
			JOIN {$wpdb->term_taxonomy} lt ON lt.term_taxonomy_id = lr.term_taxonomy_id AND lt.taxonomy = 'language'
			JOIN {$wpdb->terms} l ON l.term_id = lt.term_id
			JOIN {$wpdb->term_relationships} r ON r.object_id = p.ID
			JOIN {$wpdb->term_taxonomy} t ON t.term_taxonomy_id = r.term_taxonomy_id
			WHERE p.post_type IN ('post','product') AND p.post_status = 'publish' AND p.post_password = ''
			AND l.slug IN ('en','de') AND t.taxonomy IN ('language','category','product_cat','product_brand')
			AND NOT EXISTS (
				SELECT 1 FROM {$wpdb->term_relationships} vr
				JOIN {$wpdb->term_taxonomy} vt ON vt.term_taxonomy_id = vr.term_taxonomy_id AND vt.taxonomy = 'product_visibility'
				JOIN {$wpdb->terms} v ON v.term_id = vt.term_id AND v.slug = 'exclude-from-catalog'
				WHERE vr.object_id = p.ID
			)
			GROUP BY p.post_type, t.taxonomy, t.term_id, l.slug"
		);
		// phpcs:enable WordPress.DB.DirectDatabaseQuery
		foreach ( $rows as $row ) {
			$date = ( new \DateTimeImmutable( $row->modified, new \DateTimeZone( 'UTC' ) ) )->format( DATE_ATOM );
			if ( 'language' === $row->taxonomy ) {
				$this->dates[ $row->post_type ][0][ $row->lang ] = $date;
				continue;
			}
			$this->dates[ $row->taxonomy ][ $row->term_id ][ $row->lang ] = $date;
			$this->dates[ $row->taxonomy ][0][ $row->lang ]               = max( $date, $this->dates[ $row->taxonomy ][0][ $row->lang ] ?? '' );
		}
	}

	/**
	 * Most recent modification among the members of one archive.
	 *
	 * @param string $group Post type or taxonomy.
	 * @param int    $id    Term ID, or zero for the whole archive.
	 * @param string $lang  Language slug.
	 * @throws \RuntimeException If the taxonomy cannot be read.
	 */
	public function latest( string $group, int $id, string $lang ): string {
		$date = $this->dates[ $group ][ $id ][ $lang ] ?? '';
		if ( $id && in_array( $group, array( 'category', 'product_cat' ), true ) ) {
			$children = get_term_children( $id, $group );
			if ( $children instanceof \WP_Error ) {
				throw new \RuntimeException( esc_html( $children->get_error_message() ) );
			}
			foreach ( $children as $child ) {
				$date = max( $date, $this->dates[ $group ][ $child ][ $lang ] ?? '' );
			}
		}
		return $date;
	}
}
