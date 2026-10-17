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
		if ( count( $unit['src'] ) !== count( $german->segments ) || count( $unit['src'] ) !== count( $english->segments ) || $english->segment_roles() !== $german->segment_roles() ) {
			return FieldPlan::blocked( $english, $current[0] );
		}
		$runs     = $this->aligner->runs( $unit['src'], $english->hashes() );
		$verbatim = array();
		foreach ( $runs as $run ) {
			// Insertion/deletion/reordering has no reliable German sentence slot.
			if ( $run[1] !== $run[3] || $run[2] !== $run[4] ) {
				return FieldPlan::blocked( $english, $current[0] );
			}
			for ( $k = 0; $k < $run[2] - $run[1]; $k++ ) {
				$index = $run[3] + $k;
				if ( 'equal' !== $run[0] ) {
					// An inline element may span a sentence boundary. Do not send
					// that unsplittable run as one replacement for several sentences.
					$visible = (string) preg_replace( Segment::PLACEHOLDER, '', $english->segments[ $index ]->text );
					if ( 1 === preg_match( '/[.!?]\s+(?=\p{Lu})/u', $visible ) || $english->segments[ $index ]->markup_signature() !== $german->segments[ $index ]->markup_signature() ) {
						return FieldPlan::blocked( $english, $current[0] );
					}
					continue;
				}
				$verbatim[ $index ] = $german->segments[ $run[1] + $k ]->raw;
			}
		}
		return FieldPlan::build( $english, $verbatim, $german );
	}
}
