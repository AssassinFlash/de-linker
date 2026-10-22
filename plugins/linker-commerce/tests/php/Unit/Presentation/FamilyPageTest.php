<?php
/**
 * Product-family pagination contract.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\FamilyPage;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Tests\TestCase;

/**
 * Shared page bounds and complete family membership.
 *
 * @covers \Linker\Commerce\Presentation\FamilyPage
 */
final class FamilyPageTest extends TestCase {

	/**
	 * SAJ's thirteen families cannot produce an empty second slice or 25–13.
	 */
	public function test_a_single_page_stays_complete_for_an_excessive_page(): void {
		$rows = $this->rows( 13 );
		$page = new FamilyPage( $rows, '2', ProductShortcodes::PER_PAGE_FAMILIES );
		self::assertSame( $rows, $page->rows );
		self::assertSame( array( 1, 1, 13, 1, 13 ), array( $page->current, $page->last, $page->total, $page->from, $page->to ) );
	}

	/**
	 * Three pages partition the complete family set without splitting models.
	 */
	public function test_pages_partition_families_and_retain_every_model(): void {
		$rows  = $this->rows( 65 );
		$first = new FamilyPage( $rows, '1', 24 );
		$next  = new FamilyPage( $rows, '2', 24 );
		$last  = new FamilyPage( $rows, '3', 24 );
		self::assertSame( $rows, array_merge( $first->rows, $next->rows, $last->rows ) );
		self::assertSame( array( 1, 24, 25, 48, 49, 65 ), array( $first->from, $first->to, $next->from, $next->to, $last->from, $last->to ) );
		self::assertSame( 65, \count( array_unique( array_column( array_merge( $first->rows, $next->rows, $last->rows ), 'lead' ) ) ) );
	}

	/**
	 * Public input cannot generate an impossible slice or overflow its offset.
	 *
	 * @dataProvider public_page_values
	 * @param mixed $requested Public page parameter.
	 * @param int   $expected  Normalized page.
	 */
	public function test_public_page_values_are_normalized_before_slicing( mixed $requested, int $expected ): void {
		$page = new FamilyPage( $this->rows( 65 ), $requested, 24 );
		self::assertSame( $expected, $page->current );
		self::assertNotEmpty( $page->rows );
		self::assertLessThanOrEqual( $page->to, $page->from );
		self::assertLessThanOrEqual( $page->total, $page->to );
	}

	/**
	 * Invalid and excessive public page inputs.
	 *
	 * @return array<string, array{mixed, int}>
	 */
	public function public_page_values(): array {
		return array(
			'absent'       => array( null, 1 ),
			'zero'         => array( '0', 1 ),
			'negative'     => array( '-2', 1 ),
			'text'         => array( 'second', 1 ),
			'partial'      => array( '2oops', 1 ),
			'fraction'     => array( '2.5', 1 ),
			'nonscalar'    => array( array( '2' ), 1 ),
			'boolean'      => array( true, 1 ),
			'leading-zero' => array( '02', 1 ),
			'valid'        => array( '2', 2 ),
			'integer'      => array( 2, 2 ),
			'past-last'    => array( '4', 3 ),
			'enormous'     => array( str_repeat( '9', 100 ), 3 ),
		);
	}

	/** Empty archives have one valid root and no misleading result range. */
	public function test_empty_archive_has_zero_bounds(): void {
		$page = new FamilyPage( array(), '9999999999999999999999999999', 24 );
		self::assertSame( array( 1, 1, 0, 0, 0 ), array( $page->current, $page->last, $page->total, $page->from, $page->to ) );
		self::assertSame( array(), $page->rows );
	}

	/**
	 * Complete families, each retaining two model identities.
	 *
	 * @param int $count Number of distinct families.
	 * @return array<int, array{lead: int, ids: array<int>}>
	 */
	private function rows( int $count ): array {
		$rows = array();
		for ( $i = 1; $i <= $count; $i++ ) {
			$rows[] = array(
				'lead' => $i,
				'ids'  => array( $i, 1000 + $i ),
			);
		}
		return $rows;
	}
}
