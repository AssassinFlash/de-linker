<?php
/**
 * A piece of text the translator sees.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Text with its markup replaced by placeholders: `<t1>`…`</t1>` for an
 * inline element, `<t2/>` for a line break or an image, `<k3/>` for what
 * must come back unchanged (model names, figures with letters, shortcodes,
 * code, addresses).
 */
final class Segment {

	/**
	 * Matches one placeholder.
	 */
	public const PLACEHOLDER = '/<(\/?)([tk])(\d+)(\/?)>/';

	/**
	 * Sets up the segment.
	 *
	 * @param string                        $text Text with placeholders, runs of white space collapsed to one space.
	 * @param string                        $raw  The segment's bytes in the original value.
	 * @param array<string, string|TagPart> $map  Placeholder ("t1", "/t1", "t2/", "k3/") => the markup or text it stands for, ready to print.
	 * @param bool                          $html Whether the text goes back into HTML (and is encoded there).
	 */
	public function __construct(
		public readonly string $text,
		public readonly string $raw,
		public readonly array $map,
		public readonly bool $html
	) {}

	/**
	 * A fingerprint of what the segment says: its text, its markup and the
	 * names it keeps. Link targets are left out: a German segment is printed
	 * with the English segment's markup and its links are then pointed at
	 * the German pages, so a changed or localised link is not a change of
	 * the text.
	 */
	public function hash(): string {
		$parts = array( $this->text );
		foreach ( $this->map as $placeholder => $value ) {
			$markup  = $value instanceof TagPart ? $value->tag->raw : $value;
			$parts[] = $placeholder . '=' . preg_replace( '/\shref\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)/i', '', $markup );
		}
		return sha1( implode( "\0", $parts ) );
	}

	/**
	 * The placeholders in a text, in order.
	 *
	 * @param string $text Text.
	 * @return list<string> Placeholders as map keys ("t1", "/t1", "t2/", "k3/").
	 */
	public static function placeholders( string $text ): array {
		preg_match_all( self::PLACEHOLDER, $text, $matches, PREG_SET_ORDER );
		return array_map(
			static fn( array $found ): string => $found[1] . $found[2] . $found[3] . $found[4],
			$matches
		);
	}

	/**
	 * Inline tag names by placeholder, including their paired closing slots.
	 * Attribute values and protected model/number placeholders are excluded.
	 *
	 * @return array<string, string>
	 */
	public function markup_signature(): array {
		$signature = array();
		foreach ( $this->map as $key => $value ) {
			if ( ! str_starts_with( ltrim( $key, '/' ), 't' ) ) {
				continue;
			}
			$raw = $value instanceof TagPart ? $value->tag->raw : $value;
			if ( 1 === preg_match( '/^<\/?([a-z][a-z0-9:-]*)\b/i', $raw, $match ) ) {
				$signature[ $key ] = strtolower( $match[1] );
			}
		}
		return $signature;
	}

	/**
	 * The segment printed from a translation of its text.
	 *
	 * @param string             $translation  Translated text with the same placeholders.
	 * @param array<int, string> $translations All translations of the document, for attributes inside the segment.
	 */
	public function render( string $translation, array $translations ): string {
		$pieces = preg_split( self::PLACEHOLDER, $translation, -1, PREG_SPLIT_DELIM_CAPTURE );
		$pieces = false === $pieces ? array( $translation ) : $pieces;
		$out    = '';
		$count  = count( $pieces );
		for ( $i = 0; $i < $count; $i += 5 ) {
			$out .= $this->html ? self::encode( $pieces[ $i ] ) : $pieces[ $i ];
			if ( $i + 4 < $count ) {
				$key   = $pieces[ $i + 1 ] . $pieces[ $i + 2 ] . $pieces[ $i + 3 ] . $pieces[ $i + 4 ];
				$value = $this->map[ $key ] ?? '';
				$out  .= $value instanceof TagPart ? $value->render( $translations ) : $value;
			}
		}
		return $out;
	}

	/**
	 * Text made safe for HTML: the three characters that would start markup
	 * or an entity.
	 *
	 * @param string $text Text.
	 */
	public static function encode( string $text ): string {
		return strtr(
			$text,
			array(
				'&' => '&amp;',
				'<' => '&lt;',
				'>' => '&gt;',
			)
		);
	}
}
