<?php
/**
 * A value split into what the translator sees and what it does not.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * A title, a description or an HTML body as a sequence of parts: markup kept
 * byte for byte, segments to translate, and tags with translatable
 * attributes. Printing it with no translations gives the value back.
 */
final class Document {

	/**
	 * Sets up the document.
	 *
	 * @param array<int, string|int|TagPart> $parts    Markup to keep (string), a segment (its index) or a tag with segment attributes.
	 * @param array<int, Segment>            $segments The segments, in reading order.
	 *
	 * @phpstan-param list<Segment> $segments
	 */
	public function __construct( public readonly array $parts, public readonly array $segments ) {}

	/**
	 * The segments' fingerprints, in order.
	 *
	 * @return list<string>
	 */
	public function hashes(): array {
		return array_map( static fn( Segment $segment ): string => $segment->hash(), $this->segments );
	}

	/**
	 * The value with segments replaced by translations; a segment without a
	 * translation keeps its own bytes.
	 *
	 * @param array<int, string> $translations Segment index => translated text (with placeholders).
	 * @param array<int, string> $verbatim     Segment index => bytes to print as they are.
	 */
	public function render( array $translations, array $verbatim = array() ): string {
		$out = '';
		foreach ( $this->parts as $part ) {
			if ( is_int( $part ) ) {
				$segment = $this->segments[ $part ];
				if ( isset( $verbatim[ $part ] ) ) {
					$out .= $verbatim[ $part ];
				} else {
					$out .= isset( $translations[ $part ] ) ? $segment->render( $translations[ $part ], $translations ) : $segment->raw;
				}
			} elseif ( $part instanceof TagPart ) {
				$out .= $part->render( $translations, $verbatim );
			} else {
				$out .= $part;
			}
		}
		return $out;
	}
}
