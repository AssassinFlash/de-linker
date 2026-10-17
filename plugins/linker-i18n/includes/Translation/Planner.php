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
 * is translated automatically. Unalignable fields are rebuilt from English.
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
	 * @param bool                                                             $force    Translate every segment again.
	 */
	public function plan( string $value, bool $html, ?array $current, ?array $unit, bool $force ): FieldPlan {
		$english = $this->split( $value, $html );
		if ( $force || null === $current || ( '' === trim( $current[0] ) && array() !== $english->segments ) ) {
			return FieldPlan::build( $english );
		}
		$german = $this->split( $current[0], $html );
		// No baseline or a changed German structure: translate the whole field.
		// Historical review flags are data to recover, not a translation lock.
		if ( null === $unit || $unit['conflict'] || count( $unit['src'] ) !== count( $german->segments ) ) {
			return FieldPlan::build( $english );
		}
		$runs = $this->aligner->runs( $unit['src'], $english->hashes() );
		if ( array() === array_filter( $runs, static fn( array $run ): bool => 'equal' !== $run[0] ) ) {
			return FieldPlan::keep( $english, $current[0] );
		}

		$texts    = array();
		$verbatim = array();
		foreach ( $runs as $run ) {
			for ( $k = 0; $k < $run[2] - $run[1]; $k++ ) {
				$index = $run[3] + $k;
				if ( 'equal' !== $run[0] ) {
					continue;
				}
				$segment = $german->segments[ $run[1] + $k ];
				if ( Segment::placeholders( $segment->text ) === Segment::placeholders( $english->segments[ $index ]->text ) ) {
					$texts[ $index ] = $segment->text;
				} else {
					$verbatim[ $index ] = $segment->raw;
				}
			}
		}
		return FieldPlan::build( $english, $texts, $verbatim );
	}
}
