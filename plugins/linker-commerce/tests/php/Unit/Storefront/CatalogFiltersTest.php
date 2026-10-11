<?php
/**
 * Tests for the catalogue filter's request reading.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\CatalogFilters;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The facets the request states: the search box's `q` beside the rail's
 * facets, the unsafe input sanitised away (#16 replica port).
 *
 * @covers \Linker\Commerce\Storefront\CatalogFilters::requested
 */
final class CatalogFiltersTest extends TestCase {

	/**
	 * The search term rides with the other facets.
	 */
	public function test_requested_reads_the_search_term(): void {
		$_GET = array(
			'q'       => 'GW5.1-BAT',
			'brand'   => 'goodwe',
			'kw_min'  => '5,5',
			'ignored' => 'x',
		);

		$selected = ( new CatalogFilters() )->requested();

		$this->assertSame( 'GW5.1-BAT', $selected['q'] ?? null );
		$this->assertSame( 'goodwe', $selected['brand'] ?? null );
		$this->assertSame( 5.5, $selected['kw_min'] ?? null );
		$this->assertArrayNotHasKey( 'ignored', $selected );
	}

	/**
	 * A request without a search term carries no q key.
	 */
	public function test_requested_omits_an_empty_search_term(): void {
		$_GET = array( 'q' => '' );

		$this->assertArrayNotHasKey( 'q', ( new CatalogFilters() )->requested() );
	}

	/**
	 * WP_Mock needs the unslash to answer its input.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction(
			'wp_unslash',
			array(
				'return' => static fn ( array $value ): array => $value,
			)
		);
		WP_Mock::userFunction(
			'sanitize_text_field',
			array(
				'return' => static fn ( string $value ): string => $value,
			)
		);
		WP_Mock::userFunction(
			'sanitize_key',
			array(
				'return' => static fn ( string $value ): string => $value,
			)
		);
	}

	/** Cleans the superglobal. */
	public function tearDown(): void {
		$_GET = array();
		parent::tearDown();
	}
}
