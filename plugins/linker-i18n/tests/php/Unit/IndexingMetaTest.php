<?php
/**
 * SEO indexing meta stays symmetric across a language pair.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\IndexingMeta;
use Linker\I18n\Languages;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for IndexingMeta.
 *
 * @covers \Linker\I18n\IndexingMeta
 */
final class IndexingMetaTest extends TestCase {

	private const KEY = '_seopress_robots_index';

	/** Every metadata mutation is mirrored in both directions. */
	public function test_register_adds_both_post_and_term_observers(): void {
		$meta = new IndexingMeta( new Languages() );
		foreach (
			array(
				array( 'added_post_meta', 'post_changed' ),
				array( 'updated_post_meta', 'post_changed' ),
				array( 'deleted_post_meta', 'post_deleted' ),
				array( 'added_term_meta', 'term_changed', 99 ),
				array( 'updated_term_meta', 'term_changed', 99 ),
				array( 'deleted_term_meta', 'term_deleted', 99 ),
			) as $hook
		) {
			WP_Mock::expectActionAdded( $hook[0], array( $meta, $hook[1] ), $hook[2] ?? 10, 4 );
		}

		$meta->register();

		$this->assertConditionsMet();
	}

	/**
	 * A robots change on either singular writes the actual counterpart meta.
	 *
	 * @dataProvider postDirections
	 * @param int $changed Post whose meta changed.
	 * @param int $counterpart Post that must receive the value.
	 */
	public function test_post_robots_meta_mirrors_in_both_directions( int $changed, int $counterpart ): void {
		$this->posts();
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( $counterpart, self::KEY, true ),
				'return' => '',
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times'  => 1,
				'args'   => array( $counterpart, self::KEY, 'yes' ),
				'return' => 17,
			)
		);

		( new IndexingMeta( new Languages() ) )->post_changed( 1, $changed, self::KEY, 'yes' );

		$this->assertConditionsMet();
	}

	/**
	 * The same update works from German back to English.
	 *
	 * @return array<string, array{int, int}>
	 */
	public function postDirections(): array {
		return array(
			'English to German' => array( 5, 9 ),
			'German to English' => array( 9, 5 ),
		);
	}

	/**
	 * Deleting either singular's robots meta removes the counterpart's key.
	 *
	 * @dataProvider postDirections
	 * @param int $changed Post whose meta was deleted.
	 * @param int $counterpart Post that must lose the key.
	 */
	public function test_post_robots_meta_deletion_mirrors_in_both_directions( int $changed, int $counterpart ): void {
		$this->posts();
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( $counterpart, self::KEY, true ),
				'return' => 'yes',
			)
		);
		WP_Mock::userFunction(
			'delete_post_meta',
			array(
				'times'  => 1,
				'args'   => array( $counterpart, self::KEY ),
				'return' => true,
			)
		);

		( new IndexingMeta( new Languages() ) )->post_deleted( array( 1 ), $changed, self::KEY, 'yes' );

		$this->assertConditionsMet();
	}

	/**
	 * Category term robots meta follows the same two-way rule because it is
	 * the schema gate's input.
	 *
	 * @dataProvider termDirections
	 * @param int $changed Term whose meta changed.
	 * @param int $counterpart Term that must receive the value.
	 */
	public function test_term_robots_meta_mirrors_in_both_directions( int $changed, int $counterpart ): void {
		$this->terms();
		WP_Mock::userFunction(
			'get_term_meta',
			array(
				'args'   => array( $counterpart, self::KEY, true ),
				'return' => '',
			)
		);
		WP_Mock::userFunction(
			'update_term_meta',
			array(
				'times'  => 1,
				'args'   => array( $counterpart, self::KEY, 'yes' ),
				'return' => 18,
			)
		);

		( new IndexingMeta( new Languages() ) )->term_changed( 1, $changed, self::KEY, 'yes' );

		$this->assertConditionsMet();
	}

	/**
	 * Deleting either term's value removes both stored keys.
	 *
	 * @dataProvider termDirections
	 * @param int $changed Term whose meta was deleted.
	 * @param int $counterpart Term that must lose the key.
	 */
	public function test_term_robots_meta_deletion_mirrors_in_both_directions( int $changed, int $counterpart ): void {
		$this->terms();
		WP_Mock::userFunction(
			'get_term_meta',
			array(
				'args'   => array( $counterpart, self::KEY, true ),
				'return' => 'yes',
			)
		);
		WP_Mock::userFunction(
			'delete_term_meta',
			array(
				'times'  => 1,
				'args'   => array( $counterpart, self::KEY ),
				'return' => true,
			)
		);

		( new IndexingMeta( new Languages() ) )->term_deleted( array( 1 ), $changed, self::KEY, 'yes' );

		$this->assertConditionsMet();
	}

	/**
	 * Another meta key is not this mirror's concern.
	 */
	public function test_unrelated_meta_is_ignored(): void {
		WP_Mock::userFunction( 'pll_get_post_language', array( 'times' => 0 ) );

		( new IndexingMeta( new Languages() ) )->post_changed( 1, 5, '_thumbnail_id', 44 );

		$this->assertConditionsMet();
	}

	/**
	 * An English post and its German twin.
	 */
	private function posts(): void {
		WP_Mock::passthruFunction( 'wp_slash' );
		PolylangDouble::mock(
			array(
				5 => 'en',
				9 => 'de',
			),
			array( 5 => 9 ),
			array(),
			array(),
			'en',
			array(),
			array(
				5 => array( 'post_type' => 'page' ),
				9 => array( 'post_type' => 'page' ),
			)
		);
	}

	/**
	 * English and German twins of one category.
	 */
	private function terms(): void {
		WP_Mock::passthruFunction( 'wp_slash' );
		PolylangDouble::mock(
			array(),
			array(),
			array(
				20 => 'en',
				21 => 'de',
			),
			array( 20 => 21 ),
			'en',
			array(
				'category' => true,
			),
			array(),
			array(
				20 => array(
					'taxonomy' => 'category',
					'name'     => 'Monitoring',
				),
				21 => array(
					'taxonomy' => 'category',
					'name'     => 'Überwachung',
				),
			)
		);
	}

	/**
	 * The term mirror is entered from either side.
	 *
	 * @return array<string, array{int, int}>
	 */
	public function termDirections(): array {
		return array(
			'English to German' => array( 20, 21 ),
			'German to English' => array( 21, 20 ),
		);
	}
}
