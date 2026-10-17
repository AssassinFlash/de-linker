<?php
/**
 * Decides, per field, what of the German stays and what is translated.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Plans one field of a German object from its English and its German: the
 * segments whose English did not change keep their German; changed English
 * is translated automatically. Unalignable fields keep their German.
 */
final class Planner {

	/**
	 * Sets up the planner.
	 *
	 * @param Segmenter $segmenter Splits values into segments.
	 * @param Aligner   $aligner   Lines up old and new English segments.
	 */
	public function __construct( private readonly Segmenter $segmenter, private readonly Aligner $aligner ) {}

	/**
	 * A value as a document.
	 *
	 * @param string $value Value.
	 * @param bool   $html  Whether it is HTML.
	 */
	public function split( string $value, bool $html ): Document {
		return $html ? $this->segmenter->html( $value ) : $this->segmenter->text( $value );
	}

	/**
	 * Plans one field.
	 *
	 * @param string                                                           $value    English value.
	 * @param bool                                                             $html     Whether the field is HTML.
	 * @param array{string, bool}|null                                         $current  German value, null when there is none.
	 * @param array{src: list<string>, out: list<string>, conflict: bool}|null $unit     The field's state, null when never written.
	 * @param bool                                                             $force    Legacy argument; cannot discard existing German.
	 */
	public function plan( string $value, bool $html, ?array $current, ?array $unit, bool $force ): FieldPlan {
		$english = $this->split( $value, $html );
		unset( $force );
		if ( null !== $unit && $unit['src'] === $english->hashes() ) {
			return FieldPlan::keep( $english, $current[0] ?? '' );
		}
		if ( null === $current || ( '' === trim( $current[0] ) && array() !== $english->segments ) ) {
			return FieldPlan::build( $english );
		}
		// Owner's PR #277 ruling: adopt existing German without translating it.
		if ( null === $unit ) {
			return FieldPlan::keep( $english, $current[0] );
		}
		$german = $this->split( $current[0], $html );
		if ( count( $unit['src'] ) !== count( $german->segments ) ) {
			return FieldPlan::blocked( $english, $current[0] );
		}
		$runs    = $this->aligner->runs( $unit['src'], $english->hashes() );
		$removed = array();
		$added   = array();
		foreach ( $runs as $run ) {
			if ( 'equal' !== $run[0] ) {
				array_push( $removed, ...array_slice( $unit['src'], $run[1], $run[2] - $run[1] ) );
				array_push( $added, ...array_slice( $english->hashes(), $run[3], $run[4] - $run[3] ) );
			}
		}
		// A sentence removed here and added elsewhere is a move, not a new sentence.
		if ( array() !== array_intersect( $removed, $added ) ) {
			return FieldPlan::blocked( $english, $current[0] );
		}
		$verbatim     = array();
		$mapping      = array();
		$splices      = array();
		$roles        = $english->segment_roles();
		$german_roles = $german->segment_roles();
		foreach ( $runs as $position => $run ) {
			if ( in_array( $run[0], array( 'insert', 'delete' ), true ) ) {
				$anchored = false;
				foreach ( array( $position - 1, $position + 1 ) as $neighbor ) {
					$anchor = $runs[ $neighbor ] ?? null;
					if ( null !== $anchor && 'equal' === $anchor[0] && $this->unique_anchor( $unit['src'], $english->hashes(), $anchor ) ) {
						$anchored = true;
						break;
					}
				}
				if ( ! $anchored ) {
					return FieldPlan::blocked( $english, $current[0] );
				}
				if ( 'delete' === $run[0] ) {
					$span = $german->span( $run[1], $run[2] );
					if ( null === $span ) {
						return FieldPlan::blocked( $english, $current[0] );
					}
					$splices[] = array( $span[0], $span[1], null );
				} else {
					$span = $english->span( $run[3], $run[4] );
					if ( null === $span ) {
						return FieldPlan::blocked( $english, $current[0] );
					}
					// Prefer the next unchanged sentence; the previous one anchors an append.
					$after = ! isset( $runs[ $position + 1 ] ) || 'equal' !== $runs[ $position + 1 ][0];
					$index = $after ? $run[1] - 1 : $run[2];
					$at    = $german->boundary( $index, $after, $span[2] );
					if ( null === $at ) {
						return FieldPlan::blocked( $english, $current[0] );
					}
					$splices[] = array( $at, $at, array( $span[0], $span[1] ) );
				}
				continue;
			}
			if ( $run[2] - $run[1] !== $run[4] - $run[3] ) {
				return FieldPlan::blocked( $english, $current[0] );
			}
			for ( $k = 0; $k < $run[2] - $run[1]; $k++ ) {
				$index = $run[3] + $k;
				$old   = $run[1] + $k;
				if ( $roles[ $index ] !== $german_roles[ $old ] ) {
					return FieldPlan::blocked( $english, $current[0] );
				}
				$mapping[ $index ] = $old;
				if ( 'equal' === $run[0] ) {
					$verbatim[ $index ] = $german->segments[ $old ]->raw;
					continue;
				}
				// An inline element spanning sentence boundaries cannot be replaced safely.
				$visible = (string) preg_replace( Segment::PLACEHOLDER, '', $english->segments[ $index ]->text );
				if ( 1 === preg_match( '/[.!?]\s+(?=\p{Lu})/u', $visible ) || $english->segments[ $index ]->markup_signature() !== $german->segments[ $old ]->markup_signature() ) {
					return FieldPlan::blocked( $english, $current[0] );
				}
			}
		}
		return FieldPlan::build( $english, $verbatim, $german, $mapping, $splices );
	}

	/**
	 * Adjacent equal runs locate an edit only if their sequence occurs once.
	 *
	 * @param array<int, string>                $old Previous English hashes.
	 * @param array<int, string>                $current Current English hashes.
	 * @param array{string, int, int, int, int} $run Equal run.
	 */
	private function unique_anchor( array $old, array $current, array $run ): bool {
		$needle = array_slice( $old, $run[1], $run[2] - $run[1] );
		foreach ( array( $old, $current ) as $hashes ) {
			$matches = 0;
			$last    = count( $hashes ) - count( $needle );
			for ( $i = 0; $i <= $last; $i++ ) {
				if ( array_slice( $hashes, $i, count( $needle ) ) === $needle ) {
					++$matches;
				}
			}
			if ( 1 !== $matches ) {
				return false;
			}
		}
		return true;
	}
}
