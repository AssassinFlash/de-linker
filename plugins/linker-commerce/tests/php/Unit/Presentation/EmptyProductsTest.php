<?php
/**
 * An empty archive and a failed filter give different, truthful guidance.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The fragment supplies words; LC owns the empty surface and recovery action.
 *
 * @covers \Linker\Commerce\Presentation\ProductShortcodes
 */
final class EmptyProductsTest extends TestCase {

	/**
	 * Different empty causes retain their own message and nonempty stays silent.
	 *
	 * @return array<string, array{bool, array<string, string>, string}>
	 */
	public function provide_empty_states(): array {
		return array(
			'nonempty'             => array(
				true,
				array(
					'q'     => 'ESA',
					'brand' => 'goodwe',
				),
				'',
			),
			'empty section'        => array( false, array(), 'No products are listed here.' ),
			'sort is not a filter' => array( false, array( 'sort' => 'name' ), 'No products are listed here.' ),
			'no search match'      => array( false, array( 'q' => 'linker-owned-no-match' ), 'No products match your search. Try another search term.' ),
			'no filter match'      => array( false, array( 'phase' => 'three-phase' ), 'No products match the selected filters. Try changing or clearing a filter.' ),
			'no combined match'    => array(
				false,
				array(
					'q'     => 'ESA',
					'phase' => 'three-phase',
				),
				'No products match your search and selected filters. Try another search term or change a filter.',
			),
		);
	}

	/**
	 * No false clear-filter advice when the section itself is empty.
	 *
	 * @dataProvider provide_empty_states
	 * @param bool                  $products Whether the native loop has posts.
	 * @param array<string, string> $request  Current explicit search/filters.
	 * @param string                $expected Expected translated source text.
	 */
	public function test_empty_guidance( bool $products, array $request, string $expected ): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- an isolated request fixture, restored in finally.
		$before = $_GET;
		$_GET   = $request;
		WP_Mock::userFunction( 'have_posts', array( 'return' => $products ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return_arg' => 0 ) );
		try {
			$html = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_empty();
			if ( '' === $expected ) {
				$this->assertSame( '', $html );
			} else {
				$this->assertStringContainsString( $expected, $html );
				$this->assertStringNotContainsString( '<a ', $html );
				$this->assertStringNotContainsString( 'style=', $html );
			}
		} finally {
			$_GET = $before;
		}
	}
}
