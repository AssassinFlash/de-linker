<?php
/**
 * A tag whose attributes hold translatable text.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * A tag kept as it is except for attributes such as alt and title, whose
 * values are segments of the document.
 */
final class TagPart {

	/**
	 * Sets up the part.
	 *
	 * @param HtmlToken          $tag        The tag.
	 * @param array<string, int> $attributes Attribute name => segment index.
	 */
	public function __construct( public readonly HtmlToken $tag, public readonly array $attributes ) {}

	/**
	 * The tag with the translated attribute values.
	 *
	 * @param array<int, string> $translations Segment index => translation.
	 */
	public function render( array $translations ): string {
		$token = $this->tag;
		foreach ( $this->attributes as $attribute => $index ) {
			if ( isset( $translations[ $index ] ) ) {
				$token = new HtmlToken( HtmlToken::TAG, $token->with_attribute( $attribute, $translations[ $index ] ), $token->name, $token->closing );
			}
		}
		return $token->raw;
	}
}
