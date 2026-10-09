<?php
/**
 * One piece of an HTML document.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * A tag, a run of text, a comment, or other markup, with its exact bytes.
 */
final class HtmlToken {

	public const TEXT = 'text';

	public const TAG = 'tag';

	public const COMMENT = 'comment';

	/**
	 * Doctype, CDATA, processing instructions, and the content of script,
	 * style and the other raw-text elements.
	 */
	public const OTHER = 'other';

	/**
	 * Sets up the token.
	 *
	 * @param string $type    One of the type constants.
	 * @param string $raw     The token's bytes in the document.
	 * @param string $name    Lower-case tag name, for tags.
	 * @param bool   $closing Whether the tag is a closing tag.
	 */
	public function __construct(
		public readonly string $type,
		public readonly string $raw,
		public readonly string $name = '',
		public readonly bool $closing = false
	) {}

	/**
	 * An attribute value of a tag, decoded; null when the tag has none.
	 *
	 * @param string $attribute Attribute name.
	 */
	public function attribute( string $attribute ): ?string {
		if ( self::TAG !== $this->type || $this->closing ) {
			return null;
		}
		$match = self::find_attribute( $this->raw, $attribute );
		return null === $match ? null : html_entity_decode( $match['value'], ENT_QUOTES | ENT_HTML5, 'UTF-8' );
	}

	/**
	 * The tag's bytes with an attribute's value replaced; unchanged when the
	 * tag has no such attribute.
	 *
	 * @param string $attribute Attribute name.
	 * @param string $value     New value, not encoded.
	 */
	public function with_attribute( string $attribute, string $value ): string {
		$match = self::find_attribute( $this->raw, $attribute );
		if ( null === $match ) {
			return $this->raw;
		}
		$encoded = '"' . htmlspecialchars( $value, ENT_QUOTES | ENT_HTML5, 'UTF-8', false ) . '"';
		return substr( $this->raw, 0, $match['offset'] ) . $encoded . substr( $this->raw, $match['offset'] + $match['length'] );
	}

	/**
	 * Where an attribute's value sits in a tag.
	 *
	 * @param string $tag       The tag's bytes.
	 * @param string $attribute Attribute name.
	 * @return array{value: string, offset: int, length: int}|null The value without quotes, and the offset and length of the value with its quotes.
	 */
	private static function find_attribute( string $tag, string $attribute ): ?array {
		$pattern = '/\s' . preg_quote( $attribute, '/' ) . '\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+))/i';
		if ( 1 !== preg_match( $pattern, $tag, $match, PREG_OFFSET_CAPTURE ) ) {
			return null;
		}
		$value = '';
		foreach ( array( 2, 3, 4 ) as $group ) {
			if ( isset( $match[ $group ] ) && -1 !== $match[ $group ][1] ) {
				$value = $match[ $group ][0];
				break;
			}
		}
		return array(
			'value'  => $value,
			'offset' => $match[1][1],
			'length' => strlen( $match[1][0] ),
		);
	}
}
