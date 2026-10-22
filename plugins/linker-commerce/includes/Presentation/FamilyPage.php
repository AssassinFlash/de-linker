<?php
/**
 * One consistent slice of the archive's product families.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * The grid, count and pager read the same validated family page.
 *
 * @phpstan-type FamilyRow array{lead: int, ids: array<int>}
 */
final class FamilyPage {

	/**
	 * The families displayed on this page, with every in-scope model intact.
	 *
	 * @var array<int, FamilyRow>
	 */
	public readonly array $rows;

	/**
	 * Total matching families.
	 *
	 * @var int
	 */
	public readonly int $total;

	/**
	 * Last valid page; an empty archive still has its root page.
	 *
	 * @var int
	 */
	public readonly int $last;

	/**
	 * Validated current page.
	 *
	 * @var int
	 */
	public readonly int $current;

	/**
	 * First displayed family number, or zero for an empty archive.
	 *
	 * @var int
	 */
	public readonly int $from;

	/**
	 * Last displayed family number, or zero for an empty archive.
	 *
	 * @var int
	 */
	public readonly int $to;

	/**
	 * Keep the existing family grouping and validate before offset arithmetic.
	 *
	 * Excessive positive page numbers resolve to the last page. Invalid or
	 * nonpositive input resolves to the first. This also handles a decimal
	 * string larger than PHP_INT_MAX without first casting it to an integer.
	 *
	 * @param array<int, FamilyRow> $rows      Complete ordered family rows.
	 * @param mixed                 $requested Public page parameter.
	 * @param int                   $per_page  Existing family page size.
	 * @throws \InvalidArgumentException When the page size is not positive.
	 */
	public function __construct( array $rows, mixed $requested, int $per_page ) {
		if ( $per_page < 1 ) {
			throw new \InvalidArgumentException( 'A family page needs a positive page size.' );
		}
		$this->total   = \count( $rows );
		$this->last    = max( 1, (int) ceil( $this->total / $per_page ) );
		$this->current = $this->page_number( $requested );
		$this->from    = 0 === $this->total ? 0 : ( $this->current - 1 ) * $per_page + 1;
		$this->to      = min( $this->total, $this->current * $per_page );
		$this->rows    = \array_slice( $rows, ( $this->current - 1 ) * $per_page, $per_page );
	}

	/**
	 * A bounded integer, without accepting nonscalar or partial numbers.
	 *
	 * @param mixed $requested Public page parameter.
	 */
	private function page_number( mixed $requested ): int {
		if ( ! \is_int( $requested ) && ! \is_string( $requested ) ) {
			return 1;
		}
		$value = (string) $requested;
		if ( 1 !== preg_match( '/^[1-9][0-9]*$/D', $value ) ) {
			return 1;
		}
		$last = (string) $this->last;
		if ( \strlen( $value ) > \strlen( $last ) || ( \strlen( $value ) === \strlen( $last ) && strcmp( $value, $last ) > 0 ) ) {
			return $this->last;
		}
		return (int) $value;
	}
}
