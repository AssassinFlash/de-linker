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
	 * The verbatim channel is the known German bytes (text holding
	 * placeholders the English does not, or German a person edited that is
	 * kept while its English changed). For an attribute value those bytes are
	 * German text just like a translation; dropping the channel here printed
	 * the English attribute over a German page's own label (measured
	 * 2026-10-16: two video aria-labels on the German services page).
	 *
	 * @param array<int, string> $translations Segment index => translation.
	 * @param array<int, string> $verbatim     Segment index => bytes to print as they are.
	 */
	public function render( array $translations, array $verbatim = array() ): string {
		$token = $this->tag;
		foreach ( $this->attributes as $attribute => $index ) {
			$value = $verbatim[ $index ] ?? $translations[ $index ] ?? null;
			if ( null !== $value ) {
				$token = new HtmlToken( HtmlToken::TAG, $token->with_attribute( $attribute, $value ), $token->name, $token->closing );
			}
		}
		return $token->raw;
	}
}
