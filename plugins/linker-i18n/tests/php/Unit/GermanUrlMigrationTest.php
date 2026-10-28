<?php
/**
 * Native historical redirects must stay public and in the requested language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\GermanUrlMigration;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Covers the native old-slug destination filter.
 *
 * @covers \Linker\I18n\GermanUrlMigration::old_post
 */
final class GermanUrlMigrationTest extends TestCase {
	/**
	 * Core's history lookup does not constrain either language or post status.
	 *
	 * @dataProvider historical_candidates
	 * @param string $language Requested language.
	 * @param string $candidate_language Historical candidate's language.
	 * @param string $status Historical candidate's status.
	 * @param bool   $replacement A published same-language history exists.
	 * @param int    $expected Allowed destination, or zero to retain the 404.
	 */
	public function test_history_requires_a_public_same_language_destination( string $language, string $candidate_language, string $status, bool $replacement, int $expected ): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => $language ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => true ) );
		WP_Mock::userFunction(
			'pll_get_post_language',
			array(
				'args'   => array( 11 ),
				'return' => $candidate_language,
			)
		);
		WP_Mock::userFunction(
			'get_post_status',
			array(
				'args'   => array( 11 ),
				'return' => $status,
			)
		);
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 11 ),
				'return' => 'product',
			)
		);
		WP_Mock::userFunction(
			'get_query_var',
			array(
				'return' => static fn( string $key ) => 'name' === $key ? 'former-product-name' : 0,
			)
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'args'   => array(
					array(
						'post_type'   => 'product',
						'post_status' => 'publish',
						'lang'        => $language,
						'numberposts' => 1,
						// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Assert the existing native history query.
						'meta_key'    => '_wp_old_slug',
						// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- The supplied old slug, not a second routing store.
						'meta_value'  => 'former-product-name',
					),
				),
				'return' => $replacement ? array( PolylangDouble::post( 22 ) ) : array(),
			)
		);
		self::assertSame( $expected, ( new GermanUrlMigration() )->old_post( 11 ) );
	}

	/**
	 * Both request languages share the same publication and history rule.
	 *
	 * @return array<string,array{string,string,string,bool,int}>
	 */
	public function historical_candidates(): array {
		return array(
			'English cannot redirect to a withdrawn German twin' => array( 'en', 'de', 'draft', false, 0 ),
			'English withdrawn history remains unavailable' => array( 'en', 'en', 'draft', false, 0 ),
			'German withdrawn history remains unavailable' => array( 'de', 'de', 'draft', false, 0 ),
			'English finds its own published history'      => array( 'en', 'de', 'publish', true, 22 ),
			'German finds its own published history'       => array( 'de', 'en', 'publish', true, 22 ),
			'English published history is unchanged'       => array( 'en', 'en', 'publish', false, 11 ),
			'German published history is unchanged'        => array( 'de', 'de', 'publish', false, 11 ),
		);
	}

	/** No history match stays a 404 instead of choosing another product. */
	public function test_missing_history_keeps_the_native_no_match(): void {
		self::assertSame( 0, ( new GermanUrlMigration() )->old_post( 0 ) );
	}

	/** A duplicate historical slug in another year must not win the fallback. */
	public function test_dated_old_slug_keeps_requested_date_components(): void {
		$this->dated_candidate();
		$queries = array();
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$queries ): array {
					$queries[] = $args;
					return array( PolylangDouble::post( 22 ) );
				},
			)
		);
		self::assertSame( 22, ( new GermanUrlMigration() )->old_post( 11 ) );
		self::assertCount( 1, $queries );
		self::assertSame(
			array(
				array(
					'year'     => 2024,
					'monthnum' => 2,
					'day'      => 8,
				),
			),
			$queries[0]['date_query']
		);
		self::assertSame( '_wp_old_slug', $queries[0]['meta_key'] );
		self::assertSame( 'old-story', $queries[0]['meta_value'] );
	}

	/** The Core lookup also accepts a partial date, independently per component. */
	public function test_dated_old_slug_keeps_partial_date(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'post' ) );
		WP_Mock::userFunction(
			'get_query_var',
			array( 'return' => static fn( string $key ) => 'name' === $key ? 'old-story' : ( 'day' === $key ? 8 : 0 ) )
		);
		$queries = array();
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$queries ): array {
					$queries[] = $args;
					return array( PolylangDouble::post( 22 ) );
				},
			)
		);
		self::assertSame( 22, ( new GermanUrlMigration() )->old_post( 11 ) );
		self::assertSame( array( array( 'day' => 8 ) ), $queries[0]['date_query'] );
	}

	/**
	 * Core tries the old date for the current slug, then for an old slug.
	 *
	 * @dataProvider old_date_cases
	 * @param int $match_number Query number containing the eligible candidate, or zero.
	 * @param int $expected Allowed destination, or zero for no match.
	 */
	public function test_old_date_fallback_preserves_native_order( int $match_number, int $expected ): void {
		$this->dated_candidate();
		$queries = array();
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$queries, $match_number ): array {
					$queries[] = $args;
					return count( $queries ) === $match_number ? array( PolylangDouble::post( 22 ) ) : array();
				},
			)
		);
		$previous_db     = $GLOBALS['wpdb'] ?? null;
		$GLOBALS['wpdb'] = (object) array( 'postmeta' => 'wp_postmeta' ); // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- WordPress database double.
		try {
			self::assertSame( $expected, ( new GermanUrlMigration() )->old_post( 11 ) );
		} finally {
			$GLOBALS['wpdb'] = $previous_db; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore the previous global.
		}
		self::assertCount( 0 === $match_number ? 3 : $match_number, $queries );
		self::assertSame( '_wp_old_slug', $queries[0]['meta_key'] );
		self::assertSame( '_wp_old_date', $queries[1]['meta_key'] );
		self::assertSame( array( 'old-story' ), $queries[1]['post_name__in'] );
		self::assertSame(
			array(
				array(
					'column'   => 'wp_postmeta.meta_value',
					'year'     => 2024,
					'monthnum' => 2,
					'day'      => 8,
				),
			),
			$queries[1]['date_query']
		);
		if ( count( $queries ) === 3 ) {
			self::assertSame( '_wp_old_date', $queries[2]['meta_key'] );
			self::assertSame(
				array(
					array(
						'key'   => '_wp_old_slug',
						'value' => 'old-story',
					),
				),
				$queries[2]['meta_query']
			);
			self::assertSame( $queries[1]['date_query'], $queries[2]['date_query'] );
		}
		foreach ( $queries as $query ) {
			self::assertSame( 'post', $query['post_type'] );
			self::assertSame( 'publish', $query['post_status'] );
			self::assertSame( 'de', $query['lang'] );
		}
	}

	/**
	 * Native old-date lookup outcomes.
	 *
	 * @return array<string,array{int,int}>
	 */
	public function old_date_cases(): array {
		return array(
			'current slug at old date' => array( 2, 22 ),
			'old slug at old date'     => array( 3, 22 ),
			'no eligible old date'     => array( 0, 0 ),
		);
	}

	/** A valid Core old-date candidate does not need an old-slug record. */
	public function test_valid_old_date_candidate_is_unchanged(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'post' ) );
		self::assertSame( 11, ( new GermanUrlMigration() )->old_post( 11 ) );
	}

	/** Polylang does not apply a language restriction to untranslatable types. */
	public function test_public_untranslated_attachment_keeps_native_redirect(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'attachment' ) );
		self::assertSame( 11, ( new GermanUrlMigration() )->old_post( 11 ) );
	}

	/** An attachment's inherited status is checked against its parent. */
	public function test_attachment_fallback_skips_unpublished_inherited_candidate(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'attachment' ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => static fn( int $id ) => 22 === $id ? 'publish' : 'draft' ) );
		WP_Mock::userFunction( 'get_query_var', array( 'return' => static fn( string $key ) => 'name' === $key ? 'old-image' : 0 ) );
		$queries = array();
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$queries ): array {
					$queries[] = $args;
					return array( PolylangDouble::post( 12 ), PolylangDouble::post( 22 ) );
				},
			)
		);
		self::assertSame( 22, ( new GermanUrlMigration() )->old_post( 11 ) );
		self::assertSame( array( 'publish', 'inherit' ), $queries[0]['post_status'] );
		self::assertSame( -1, $queries[0]['numberposts'] );
	}

	/** Prepares a published candidate belonging to the other request language. */
	private function dated_candidate(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_is_translated_post_type', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'post' ) );
		WP_Mock::userFunction(
			'get_query_var',
			array(
				'return' => static fn( string $key ) => array(
					'name'     => 'old-story',
					'year'     => 2024,
					'monthnum' => 2,
					'day'      => 8,
				)[ $key ] ?? 0,
			)
		);
	}
}
