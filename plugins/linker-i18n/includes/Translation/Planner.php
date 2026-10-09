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
 * segments whose English did not change keep their German, a segment a
 * person edited is never overwritten (when its English changed, it stays and
 * waits for a review; the whole field does when the segments no longer line
 * up), and the rest goes to the translator.
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
	 * @param array<int, int>|string                                           $reviewed Segments a person edited.
	 * @param bool                                                             $force    Translate every segment again.
	 */
	public function plan( string $value, bool $html, ?array $current, ?array $unit, array|string $reviewed, bool $force ): FieldPlan {
		$english = $this->split( $value, $html );
		if ( $force || null === $current || ( '' === trim( $current[0] ) && array() !== $english->segments ) ) {
			return FieldPlan::build( $english );
		}
		$german = $this->split( $current[0], $html );
		if ( null === $unit ) {
			// German nobody recorded: a person wrote it (Polylang's "add translation"). It is kept, as reviewed.
			$unit = array(
				'src'      => $english->hashes(),
				'out'      => $german->hashes(),
				'conflict' => false,
			);
			return FieldPlan::keep( $english, $current[0], false, '*', $unit );
		}
		$reviewed    = $this->absorb( $unit['out'], $german, $reviewed );
		$runs        = $this->aligner->runs( $unit['src'], $english->hashes() );
		$changes     = array_filter( $runs, static fn( array $run ): bool => 'equal' !== $run[0] );
		$unit['out'] = $german->hashes();
		if ( array() === $changes ) {
			return FieldPlan::keep( $english, $current[0], false, $reviewed, $unit );
		}
		if ( is_string( $reviewed ) ) {
			// A person reworked the field: all of it is theirs.
			$unit['conflict'] = true;
			return FieldPlan::keep( $english, $current[0], true, $reviewed, $unit );
		}
		// The German lines up with the English it was made from segment by
		// segment only when both have as many segments (absorb() found the
		// German's segments to be the ones last written).
		$aligned = count( $unit['src'] ) === count( $german->segments );

		// German a person edited whose English changed stays as it is and
		// remembers the English it was made from. That needs the changed run to
		// pair old and new segments one to one; otherwise the whole field stays.
		$held = array();
		foreach ( $changes as $run ) {
			if ( $run[1] === $run[2] || array() === array_intersect( range( $run[1], $run[2] - 1 ), $reviewed ) ) {
				continue; // An insertion, or no German a person edited.
			}
			if ( ! $aligned || $run[2] - $run[1] !== $run[4] - $run[3] ) {
				$unit['conflict'] = true;
				return FieldPlan::keep( $english, $current[0], true, $reviewed, $unit );
			}
			for ( $k = 0; $k < $run[2] - $run[1]; $k++ ) {
				if ( in_array( $run[1] + $k, $reviewed, true ) ) {
					$held[ $run[3] + $k ] = $unit['src'][ $run[1] + $k ];
				}
			}
		}

		$texts    = array();
		$verbatim = array();
		$edited   = array();
		foreach ( $runs as $run ) {
			for ( $k = 0; $aligned && $k < $run[2] - $run[1]; $k++ ) {
				$index = $run[3] + $k;
				if ( 'equal' !== $run[0] && ! isset( $held[ $index ] ) ) {
					continue;
				}
				$segment = $german->segments[ $run[1] + $k ];
				if ( Segment::placeholders( $segment->text ) === Segment::placeholders( $english->segments[ $index ]->text ) ) {
					$texts[ $index ] = $segment->text;
				} else {
					$verbatim[ $index ] = $segment->raw;
				}
				if ( in_array( $run[1] + $k, $reviewed, true ) ) {
					$edited[] = $index;
				}
			}
		}
		return FieldPlan::build( $english, $texts, $verbatim, $edited, $held );
	}

	/**
	 * Adds the segments whose German differs from what was last written to
	 * the reviewed ones; '*' when the German no longer has the same segments.
	 *
	 * @param array<int, string>     $out      Fingerprints of the German last written.
	 * @param Document               $german   The German as it is now.
	 * @param array<int, int>|string $reviewed Segments already reviewed.
	 * @return array<int, int>|string
	 */
	public function absorb( array $out, Document $german, array|string $reviewed ): array|string {
		if ( is_string( $reviewed ) ) {
			return '*';
		}
		$hashes = $german->hashes();
		if ( count( $hashes ) !== count( $out ) ) {
			return '*';
		}
		foreach ( $hashes as $index => $hash ) {
			if ( $hash !== $out[ $index ] && ! in_array( $index, $reviewed, true ) ) {
				$reviewed[] = $index;
			}
		}
		sort( $reviewed );
		return $reviewed;
	}
}
