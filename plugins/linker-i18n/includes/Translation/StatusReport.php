<?php
/**
 * Shared read-only projection of translation failures for the daily digest.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

use Linker\I18n\Languages;
use Linker\I18n\TranslatedTypes;

/**
 * Reports English content only; templates and German duplicates stay out.
 */
final class StatusReport {

	/**
	 * Failures needing attention, in stable source-ID order within each kind.
	 *
	 * @return list<array{kind: string, id: int, title: string, reason: string, edit_url: string}>
	 */
	public function issues(): array {
		$state = new State();
		$rows  = array();
		$posts = get_posts(
			array(
				'post_type'    => TranslatedTypes::POST_TYPES,
				'post_status'  => array( 'publish', 'future', 'private', 'draft', 'pending' ),
				'lang'         => Languages::SOURCE,
				'numberposts'  => -1,
				'orderby'      => 'ID',
				'order'        => 'ASC',
				'meta_key'     => State::STATUS, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- native metadata is the translation state authority.
				'meta_value'   => array( State::FAILED, State::STRUCTURE_MISMATCH ), // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- current exceptions only, no independent counter.
				'meta_compare' => 'IN',
			)
		);
		foreach ( $posts as $post ) {
			$rows[] = array(
				'kind'     => State::POST,
				'id'       => $post->ID,
				'title'    => $post->post_title,
				'reason'   => State::STRUCTURE_MISMATCH === $state->status( State::POST, $post->ID ) ? State::structure_reason() : $state->note( State::POST, $post->ID ),
				'edit_url' => admin_url( 'post.php?post=' . $post->ID . '&action=edit' ),
			);
		}
		$terms = get_terms(
			array(
				'taxonomy'   => TranslatedTypes::TAXONOMIES,
				'lang'       => Languages::SOURCE,
				'hide_empty' => false,
				'orderby'    => 'term_id',
				'order'      => 'ASC',
				// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- native metadata is the term failure authority.
				'meta_query' => array(
					array(
						'key'     => State::STATUS,
						'value'   => array( State::FAILED, State::STRUCTURE_MISMATCH ),
						'compare' => 'IN',
					),
				), // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- the same authority for term failures.
			)
		);
		foreach ( is_array( $terms ) ? $terms : array() as $term ) {
			$rows[] = array(
				'kind'     => State::TERM,
				'id'       => $term->term_id,
				'title'    => $term->name,
				'reason'   => State::STRUCTURE_MISMATCH === $state->status( State::TERM, $term->term_id ) ? State::structure_reason() : $state->note( State::TERM, $term->term_id ),
				'edit_url' => admin_url( 'term.php?taxonomy=' . rawurlencode( $term->taxonomy ) . '&tag_ID=' . $term->term_id ),
			);
		}
		return $rows;
	}
}
