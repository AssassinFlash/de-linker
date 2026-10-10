<?php
/**
 * Lines up the segments of an old and a new English text.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Compares two sequences of segment fingerprints the way a diff does: the
 * longest common subsequence stays, the rest is replaced, deleted or
 * inserted. Only the changed segments of an edited page go to the
 * translator; the German of the others is kept.
 */
final class Aligner {

	/**
	 * The edit that turns $old into $current, as runs of
	 * [operation, old start, old end, new start, new end] (ends exclusive);
	 * operation is equal, replace, delete or insert.
	 *
	 * @param array<int, string> $old Old fingerprints.
	 * @param array<int, string> $current New fingerprints.
	 * @return list<array{string, int, int, int, int}>
	 */
	public function runs( array $old, array $current ): array {
		$n      = count( $old );
		$m      = count( $current );
		$length = array_fill( 0, $n + 1, array_fill( 0, $m + 1, 0 ) );
		for ( $i = $n - 1; $i >= 0; $i-- ) {
			for ( $j = $m - 1; $j >= 0; $j-- ) {
				$length[ $i ][ $j ] = $old[ $i ] === $current[ $j ] ? $length[ $i + 1 ][ $j + 1 ] + 1 : max( $length[ $i + 1 ][ $j ], $length[ $i ][ $j + 1 ] );
			}
		}
		$runs = array();
		$i    = 0;
		$j    = 0;
		$from = array( 0, 0 );
		while ( $i < $n || $j < $m ) {
			if ( $i < $n && $j < $m && $old[ $i ] === $current[ $j ] ) {
				$this->change( $runs, $from[0], $i, $from[1], $j );
				$start = array( $i, $j );
				while ( $i < $n && $j < $m && $old[ $i ] === $current[ $j ] ) {
					++$i;
					++$j;
				}
				$runs[] = array( 'equal', $start[0], $i, $start[1], $j );
				$from   = array( $i, $j );
			} elseif ( $j < $m && ( $i >= $n || $length[ $i ][ $j + 1 ] >= $length[ $i + 1 ][ $j ] ) ) {
				++$j;
			} else {
				++$i;
			}
		}
		$this->change( $runs, $from[0], $i, $from[1], $j );
		return $runs;
	}

	/**
	 * Adds the run between two matches, when there is one.
	 *
	 * @param array<int, array{string, int, int, int, int}> $runs  Runs so far.
	 * @param int                                           $i1    Old start.
	 * @param int                                           $i2    Old end.
	 * @param int                                           $j1    New start.
	 * @param int                                           $j2    New end.
	 *
	 * @phpstan-param list<array{string, int, int, int, int}> $runs
	 * @phpstan-param-out list<array{string, int, int, int, int}> $runs
	 */
	private function change( array &$runs, int $i1, int $i2, int $j1, int $j2 ): void {
		if ( $i1 < $i2 && $j1 < $j2 ) {
			$runs[] = array( 'replace', $i1, $i2, $j1, $j2 );
		} elseif ( $i1 < $i2 ) {
			$runs[] = array( 'delete', $i1, $i2, $j1, $j2 );
		} elseif ( $j1 < $j2 ) {
			$runs[] = array( 'insert', $i1, $i2, $j1, $j2 );
		}
	}
}
