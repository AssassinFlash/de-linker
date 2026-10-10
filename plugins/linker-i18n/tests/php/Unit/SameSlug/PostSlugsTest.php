<?php
/**
 * Tests for one slug per language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\SameSlug;

use Linker\I18n\Languages;
use Linker\I18n\SameSlug\PostSlugs;
use Linker\I18n\SameSlug\TermSlugs;
use Linker\I18n\Tests\Unit\PolylangDouble;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for PostSlugs and TermSlugs.
 *
 * @covers \Linker\I18n\SameSlug\PostSlugs
 * @covers \Linker\I18n\SameSlug\TermSlugs
 */
final class PostSlugsTest extends TestCase {

	/**
	 * The posts that hold the asked slug, as the database would answer.
	 *
	 * @param array<int, int> $holders Post IDs.
	 */
	private function database( array $holders ): void {
		$wpdb        = Mockery::mock( 'wpdb' );
		$wpdb->posts = 'wp_posts';
		$wpdb->shouldReceive( 'prepare' )->andReturn( 'SQL' );
		$wpdb->shouldReceive( 'get_col' )->andReturn( array_map( 'strval', $holders ) );
		$GLOBALS['wpdb']          = $wpdb; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the database double.
		$rewrite                  = Mockery::mock( 'WP_Rewrite' );
		$rewrite->feeds           = array( 'feed', 'rss2' );
		$rewrite->pagination_base = 'page';
		$GLOBALS['wp_rewrite']    = $rewrite; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the rewrite double.
	}

	/**
	 * Clears the doubles.
	 */
	public function tearDown(): void {
		unset( $GLOBALS['wpdb'], $GLOBALS['wp_rewrite'] );
		parent::tearDown();
	}

	/**
	 * The German product keeps the English product's slug.
	 */
	public function test_slug_held_by_the_other_language_is_given_back(): void {
		PolylangDouble::mock(
			array(
				64 => 'de',
				28 => 'en',
			)
		);
		$this->database( array( 28 ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => false ) );
		WP_Mock::expectFilter( 'wp_unique_post_slug_is_bad_flat_slug', false, 'goodwe-gw60k-sts-g10', 'product' );

		$this->assertSame( 'goodwe-gw60k-sts-g10', ( new PostSlugs( new Languages() ) )->unique( 'goodwe-gw60k-sts-g10-2', 64, 'publish', 'product', 0, 'goodwe-gw60k-sts-g10' ) );
	}

	/**
	 * A slug held in the same language stays unique as WordPress made it.
	 */
	public function test_slug_held_in_the_same_language_stays_unique(): void {
		PolylangDouble::mock(
			array(
				64 => 'de',
				65 => 'de',
				28 => 'en',
			)
		);
		$this->database( array( 28, 65 ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => false ) );
		WP_Mock::expectFilter( 'wp_unique_post_slug_is_bad_flat_slug', false, 'x', 'product' );

		$this->assertSame( 'x-2', ( new PostSlugs( new Languages() ) )->unique( 'x-2', 64, 'publish', 'product', 0, 'x' ) );
	}

	/**
	 * A post without a language yet, or a reserved slug, is WordPress's business.
	 */
	public function test_no_language_or_reserved_slug_is_left_alone(): void {
		PolylangDouble::mock( array( 28 => 'en' ) );
		$this->database( array( 28 ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => true ) );
		$slugs = new PostSlugs( new Languages() );

		$this->assertSame( 'about-2', $slugs->unique( 'about-2', 99, 'publish', 'page', 0, 'about' ) );

		PolylangDouble::mock(
			array(
				50 => 'de',
				28 => 'en',
			)
		);
		$this->assertSame( 'feed-2', $slugs->unique( 'feed-2', 50, 'publish', 'page', 0, 'feed' ) );
		$this->assertSame( 'page2-2', $slugs->unique( 'page2-2', 50, 'publish', 'page', 0, 'page2' ) );
	}

	/**
	 * The slug check of wp_update_term() is narrowed to the term's language, once.
	 */
	public function test_term_slug_check_is_narrowed_to_the_language(): void {
		PolylangDouble::mock(
			array(),
			array(),
			array(
				156 => 'de',
				44  => 'en',
			)
		);
		$slugs = new TermSlugs( new Languages() );

		$this->assertSame( 0, $slugs->note( 0, 156, 'product_cat' ) );
		$this->assertSame(
			array(
				'slug' => 'ems-monitoring',
				'lang' => 'de',
			),
			$slugs->narrow( array( 'slug' => 'ems-monitoring' ) )
		);
		$this->assertSame( array( 'slug' => 'ems-monitoring' ), $slugs->narrow( array( 'slug' => 'ems-monitoring' ) ) );
		$this->assertSame( array( 'name' => 'x' ), $slugs->narrow( array( 'name' => 'x' ) ) );
	}
}
