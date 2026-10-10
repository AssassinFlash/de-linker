<?php
/**
 * Translation on save of a product category.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * A new English product category is queued on save and translated into a
 * German category: German name and description, a slug from the German
 * name, its own German URL, listed in German only.
 *
 * @coversNothing
 */
final class TermTranslationTest extends SiteTestCase {

	private const SLUG = 'linker-i18n-test-category';

	/**
	 * Deletes the test categories.
	 */
	private static function remove(): void {
		self::php(
			'
			$english = get_term_by( "slug", $input["slug"], "product_cat" );
			if ( $english ) {
				$german = pll_get_term( $english->term_id, "de" );
				as_unschedule_all_actions( "linker_i18n_translate", array( "term", $english->term_id, false, 1 ), "linker-i18n" );
				if ( $german ) {
					wp_delete_term( $german, "product_cat" );
				}
				wp_delete_term( $english->term_id, "product_cat" );
			}
			return true;
			',
			array( 'slug' => self::SLUG )
		);
	}

	/**
	 * Removes what an earlier run left.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		self::stub();
		self::remove();
	}

	/**
	 * Deletes the test categories.
	 */
	public static function tearDownAfterClass(): void {
		if ( '' !== self::$site ) {
			self::remove();
		}
		parent::tearDownAfterClass();
	}

	/**
	 * Saved, queued, translated.
	 */
	public function test_category_is_translated_on_save(): void {
		$created = self::php(
			'
			$created = wp_insert_term( "Linker i18n test category", "product_cat", array( "slug" => $input["slug"], "description" => "Hybrid inverters for home storage." ) );
			$id      = $created["term_id"];
			return array( "id" => $id, "language" => pll_get_term_language( $id ), "status" => get_term_meta( $id, "_linker_i18n_status", true ) );
			',
			array( 'slug' => self::SLUG )
		);
		$this->assertIsArray( $created );
		$english = $created['id'];
		$this->assertIsInt( $english );
		$this->assertSame( 'en', $created['language'] );
		$this->assertSame( 'pending', $created['status'] );
		$this->assertSame( 1, self::run_jobs( 'term', $english, true ) );

		$german = self::php(
			'
			$id   = (int) pll_get_term( $input["id"], "de" );
			$term = get_term( $id );
			return array(
				"language"    => pll_get_term_language( $id ),
				"name"        => $term->name,
				"slug"        => $term->slug,
				"description" => $term->description,
				"link"        => get_term_link( $term ),
				"status"      => get_term_meta( $input["id"], "_linker_i18n_status", true ),
			);
			',
			array( 'id' => $english )
		);
		$this->assertIsArray( $german );
		$this->assertSame( 'de', $german['language'] );
		$this->assertSame( '[de] Linker i18n test category', $german['name'] );
		$this->assertSame( 'de-linker-i18n-test-category', $german['slug'] );
		$this->assertSame( '[de] Hybrid Wechselrichter for home storage.', $german['description'] );
		$this->assertSame( 'synced', $german['status'] );
		$this->assertSame( self::$site . '/de/produkt-kategorie/de-linker-i18n-test-category/', $german['link'] );
		$this->assertSame( 200, self::get( '/de/produkt-kategorie/de-linker-i18n-test-category/' )['status'] );

		$names = array_column( self::rest( '/wc/store/v1/products/categories?hide_empty=false&lang=de' ), 'name' );
		$this->assertContains( '[de] Linker i18n test category', $names );
		$this->assertNotContains( 'Linker i18n test category', $names );
	}
}
