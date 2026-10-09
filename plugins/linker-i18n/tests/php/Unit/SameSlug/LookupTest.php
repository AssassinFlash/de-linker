<?php
/**
 * Tests for finding posts by slug in a language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\SameSlug;

use Linker\I18n\Languages;
use Linker\I18n\SameSlug\Lookup;
use Linker\I18n\Tests\Unit\PolylangDouble;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Lookup.
 *
 * @covers \Linker\I18n\SameSlug\Lookup
 */
final class LookupTest extends TestCase {

	/**
	 * The site: compare-products in English (19) and German (50), about (34)
	 * and ueber-uns (60) with the child page leistungsfaehigkeit (71), the
	 * product goodwe-gw60k-sts-g10 in English (28) and German (64).
	 */
	public function setUp(): void {
		parent::setUp();
		$posts = array(
			array( 19, 'page', 'compare-products', 0, 'en' ),
			array( 50, 'page', 'compare-products', 0, 'de' ),
			array( 34, 'page', 'about', 0, 'en' ),
			array( 60, 'page', 'ueber-uns', 0, 'de' ),
			array( 71, 'page', 'leistungsfaehigkeit', 60, 'de' ),
			array( 28, 'product', 'goodwe-gw60k-sts-g10', 0, 'en' ),
			array( 64, 'product', 'goodwe-gw60k-sts-g10', 0, 'de' ),
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $query ) use ( $posts ): array {
					$found = array_filter(
						$posts,
						static fn( array $post ): bool => $post[1] === $query['post_type'] && in_array( $post[2], $query['post_name__in'], true ) && ( '' === $query['lang'] || $post[4] === $query['lang'] ) && ( ! isset( $query['post_parent'] ) || $post[3] === $query['post_parent'] )
					);
					return array_values( array_map( static fn( array $post ): int => $post[0], $found ) );
				},
			)
		);
		WP_Mock::passthruFunction( 'sanitize_title_for_query' );
		WP_Mock::passthruFunction( 'sanitize_title' );
		PolylangDouble::mock( array(), array(), array(), array(), 'de', array( 'attachment' => false ) );
	}

	/**
	 * Page paths and product slugs resolve in the URL's language; a slug of
	 * the other language only is a 404.
	 *
	 * @return array<string, array{array<string, mixed>, array<string, mixed>}>
	 */
	public function provide_requests(): array {
		return array(
			'same slug, German'  => array(
				array(
					'pagename' => 'compare-products',
					'lang'     => 'de',
				),
				array(
					'lang'    => 'de',
					'page_id' => 50,
				),
			),
			'same slug, English' => array(
				array(
					'pagename' => 'compare-products',
					'lang'     => 'en',
				),
				array(
					'lang'    => 'en',
					'page_id' => 19,
				),
			),
			'child page'         => array(
				array(
					'pagename' => 'ueber-uns/leistungsfaehigkeit',
					'lang'     => 'de',
				),
				array(
					'lang'    => 'de',
					'page_id' => 71,
				),
			),
			'product, German'    => array(
				array(
					'product' => 'goodwe-gw60k-sts-g10',
					'lang'    => 'de',
				),
				array(
					'lang'      => 'de',
					'p'         => 64,
					'post_type' => 'product',
				),
			),
			'product, English'   => array(
				array(
					'product' => 'goodwe-gw60k-sts-g10',
					'lang'    => 'en',
				),
				array(
					'lang'      => 'en',
					'p'         => 28,
					'post_type' => 'product',
				),
			),
			'no slug'            => array( array( 'lang' => 'de' ), array( 'lang' => 'de' ) ),
		);
	}

	/**
	 * The query variables after the lookup.
	 *
	 * @dataProvider provide_requests
	 *
	 * @param array<string, mixed> $vars     Request query variables.
	 * @param array<string, mixed> $expected Expected query variables.
	 */
	public function test_request( array $vars, array $expected ): void {
		WP_Mock::userFunction( 'get_post_types', array( 'return' => array( 'product' => (object) array( 'query_var' => 'product' ) ) ) );

		$this->assertSame( $expected, ( new Lookup( new Languages() ) )->request( $vars ) );
	}

	/**
	 * /de/about/ is an English page under /de/: a 404, not the English page.
	 */
	public function test_english_page_under_de_is_404(): void {
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'about' ),
				'return' => PolylangDouble::post( 34, array( 'post_type' => 'page' ) ),
			)
		);

		$this->assertSame(
			'404',
			( new Lookup( new Languages() ) )->request(
				array(
					'pagename' => 'about',
					'lang'     => 'de',
				)
			)['error'] ?? null
		);
	}

	/**
	 * A slug no post has is left to WordPress (its own 404); a slug only an
	 * English post has is a 404 under /de/.
	 */
	public function test_slugs_without_german_post(): void {
		WP_Mock::userFunction( 'get_post_types', array( 'return' => array( 'product' => (object) array( 'query_var' => 'product' ) ) ) );
		$lookup = new Lookup( new Languages() );

		$this->assertSame(
			array(
				'name' => 'nothing',
				'lang' => 'de',
			),
			$lookup->request(
				array(
					'name' => 'nothing',
					'lang' => 'de',
				)
			)
		);
		$this->assertSame(
			array(
				'name'      => 'about',
				'post_type' => 'page',
				'lang'      => 'de',
				'error'     => '404',
			),
			$lookup->request(
				array(
					'name'      => 'about',
					'post_type' => 'page',
					'lang'      => 'de',
				)
			)
		);
	}
}
