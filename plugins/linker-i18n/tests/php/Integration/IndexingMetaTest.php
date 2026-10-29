<?php
/**
 * Real WordPress metadata writes keep an indexing pair symmetric.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * Post and blog-category metadata through WordPress's actual hooks.
 *
 * @coversNothing
 */
final class IndexingMetaTest extends SiteTestCase {

	/**
	 * An editor may change either side; the other side follows, including a
	 * delete made from the German twin.
	 */
	public function test_real_post_and_category_meta_mirror_both_directions(): void {
		$result = self::php(
			'
			$suffix = wp_generate_uuid4();
			$ids = array( "posts" => array(), "terms" => array() );
			try {
				foreach ( array( "en", "de" ) as $language ) {
					$post = wp_insert_post( array(
						"post_type" => "page",
						"post_status" => "draft",
						"post_title" => "Indexing meta fixture " . $language,
						"post_content" => "<p>fixture</p>",
					), true );
					if ( is_wp_error( $post ) ) { throw new RuntimeException( $post->get_error_message() ); }
					$ids["posts"][ $language ] = (int) $post;
					pll_set_post_language( (int) $post, $language );
				}
				pll_save_post_translations( $ids["posts"] );

				foreach ( array( "en", "de" ) as $language ) {
					$created = wp_insert_term( "Indexing category " . $language . " " . $suffix, "category", array( "slug" => "indexing-" . $language . "-" . $suffix ) );
					if ( is_wp_error( $created ) ) { throw new RuntimeException( $created->get_error_message() ); }
					$ids["terms"][ $language ] = (int) $created["term_id"];
					pll_set_term_language( (int) $created["term_id"], $language );
				}
				pll_save_term_translations( $ids["terms"] );

				update_post_meta( $ids["posts"]["en"], "_seopress_robots_index", "yes" );
				$post_english_to_german = get_post_meta( $ids["posts"]["de"], "_seopress_robots_index", true );
				delete_post_meta( $ids["posts"]["de"], "_seopress_robots_index" );
				$post_deleted_both = "" === get_post_meta( $ids["posts"]["en"], "_seopress_robots_index", true )
					&& "" === get_post_meta( $ids["posts"]["de"], "_seopress_robots_index", true );

				update_term_meta( $ids["terms"]["de"], "_seopress_robots_index", "yes" );
				$term_german_to_english = get_term_meta( $ids["terms"]["en"], "_seopress_robots_index", true );
				$term_german = get_term_meta( $ids["terms"]["de"], "_seopress_robots_index", true );
				delete_term_meta( $ids["terms"]["en"], "_seopress_robots_index" );
				$term_deleted_both = "" === get_term_meta( $ids["terms"]["en"], "_seopress_robots_index", true )
					&& "" === get_term_meta( $ids["terms"]["de"], "_seopress_robots_index", true );

				return array(
					"post_english_to_german" => $post_english_to_german,
					"post_deleted_both" => $post_deleted_both,
					"term_german_to_english" => $term_german_to_english,
					"term_german" => $term_german,
					"term_deleted_both" => $term_deleted_both,
				);
			} finally {
				foreach ( $ids["posts"] as $post ) {
					as_unschedule_all_actions( "linker_i18n_translate", array( "post", $post, false, 1 ), "linker-i18n" );
					wp_delete_post( $post, true );
				}
				foreach ( $ids["terms"] as $term ) {
					as_unschedule_all_actions( "linker_i18n_translate", array( "term", $term, false, 1 ), "linker-i18n" );
					wp_delete_term( $term, "category" );
				}
			}
			'
		);

		$this->assertIsArray( $result );
		$this->assertSame( 'yes', $result['post_english_to_german'] );
		$this->assertTrue( $result['post_deleted_both'] );
		$this->assertSame( 'yes', $result['term_german_to_english'] );
		$this->assertSame( 'yes', $result['term_german'] );
		$this->assertTrue( $result['term_deleted_both'] );
	}
}
