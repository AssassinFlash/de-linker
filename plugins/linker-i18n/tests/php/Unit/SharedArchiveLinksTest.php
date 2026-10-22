<?php
/**
 * Native empty shared-archive translation policy boundaries.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\TranslatedTypes;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * A zero count may expose only the already-valid shared archive root.
 *
 * @covers \Linker\I18n\TranslatedTypes
 */
final class SharedArchiveLinksTest extends TestCase {

	/**
	 * Only real shared product roots may override a zero target-language count.
	 *
	 * @return array<string, array{array<string, mixed>, bool}>
	 */
	public function provide_empty_roots(): array {
		return array(
			'shared Woo brand'       => array( array(), false ),
			'shared attribute brand' => array( array( 'taxonomy' => 'pa_brand' ), false ),
			'shared series'          => array( array( 'taxonomy' => 'pa_series' ), false ),
			'English target'         => array( array( 'language' => 'en' ), false ),
			'already visible'        => array( array( 'hide' => false ), false ),
			'secondary query'        => array( array( 'main' => false ), true ),
			'unknown or 404'         => array( array( 'is_404' => true ), true ),
			'paged archive'          => array( array( 'is_paged' => true ), true ),
			'feed'                   => array( array( 'is_feed' => true ), true ),
			'native search'          => array( array( 'is_search' => true ), true ),
			'no queried term'        => array( array( 'term' => false ), true ),
			'invalid term ID'        => array( array( 'term_id' => 0 ), true ),
			'unrelated taxonomy'     => array( array( 'taxonomy' => 'category' ), true ),
			'translated taxonomy'    => array( array( 'translated' => true ), true ),
			'not registered'         => array( array( 'registered' => false ), true ),
			'not public'             => array( array( 'public' => false ), true ),
			'not queryable'          => array( array( 'queryable' => false ), true ),
			'not a product type'     => array( array( 'object_type' => array( 'post' ) ), true ),
			'no query variable'      => array( array( 'query_var' => false ), true ),
			'explicit unrelated'     => array( array( 'post_type' => 'post' ), true ),
			'explicit all types'     => array( array( 'post_type' => 'any' ), true ),
			'array product types'    => array( array( 'post_type' => array( 'product' ) ), true ),
			'empty product type'     => array( array( 'post_type' => '' ), true ),
			'wrong count term'       => array( array( 'argument_slug' => 'another-brand' ), true ),
			'missing count term'     => array( array( 'argument_slug' => null ), true ),
			'unknown language'       => array( array( 'language' => 'unknown' ), true ),
		);
	}

	/**
	 * Leave URL generation to Polylang and preserve every unrelated decision.
	 *
	 * @dataProvider provide_empty_roots
	 * @param array<string, mixed> $overrides Counterexample differences.
	 * @param bool                 $expected  Expected native hide decision.
	 */
	public function test_empty_root_policy( array $overrides, bool $expected ): void {
		$case           = array_merge(
			array(
				'hide'          => true,
				'main'          => true,
				'is_404'        => false,
				'is_paged'      => false,
				'is_feed'       => false,
				'is_search'     => false,
				'term'          => true,
				'term_id'       => 436,
				'taxonomy'      => 'product_brand',
				'translated'    => false,
				'registered'    => true,
				'public'        => true,
				'queryable'     => true,
				'object_type'   => array( 'product' ),
				'post_type'     => 'product',
				'argument_slug' => 'dehn',
				'language'      => 'de',
			),
			$overrides
		);
		$term           = Mockery::mock( 'WP_Term' );
		$term->term_id  = $case['term_id'];
		$term->taxonomy = $case['taxonomy'];
		$term->slug     = 'dehn';
		$taxonomy       = (object) array(
			'public'             => $case['public'],
			'publicly_queryable' => $case['queryable'],
			'object_type'        => $case['object_type'],
			'query_var'          => $case['query_var'] ?? $case['taxonomy'],
		);
		WP_Mock::userFunction( 'is_main_query', array( 'return' => $case['main'] ) );
		foreach ( array( 'is_404', 'is_paged', 'is_feed', 'is_search' ) as $condition ) {
			WP_Mock::userFunction( $condition, array( 'return' => $case[ $condition ] ) );
		}
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $case['term'] ? $term : null ) );
		WP_Mock::userFunction( 'pll_is_translated_taxonomy', array( 'return' => $case['translated'] ) );
		WP_Mock::userFunction( 'get_taxonomy', array( 'return' => $case['registered'] ? $taxonomy : false ) );
		WP_Mock::userFunction( 'pll_languages_list', array( 'return' => array( 'en', 'de' ) ) );

		$this->assertSame(
			$expected,
			( new TranslatedTypes() )->hide_shared_archive(
				$case['hide'],
				$case['language'],
				array(
					'post_type'       => $case['post_type'],
					$case['taxonomy'] => $case['argument_slug'],
				)
			)
		);
	}
}
