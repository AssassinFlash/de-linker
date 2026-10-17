<?php
/**
 * One field retained in German or rebuilt from the English document.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Known German segments and the remaining English segments to translate.
 */
final class FieldPlan {

	/**
	 * Sets up the plan.
	 *
	 * @param Document           $english English document.
	 * @param string|null        $kept Complete German field, or null to rebuild it.
	 * @param array<int, string> $texts Known German text by English index.
	 * @param array<int, string> $verbatim Known German markup by English index.
	 */
	private function __construct(
		public readonly Document $english,
		public readonly ?string $kept,
		public readonly array $texts,
		public readonly array $verbatim
	) {}

	/**
	 * Keeps an unchanged field.
	 *
	 * @param Document $english English document.
	 * @param string   $german German field.
	 */
	public static function keep( Document $english, string $german ): self {
		return new self( $english, $german, array(), array() );
	}

	/**
	 * Builds from English markup with known and newly translated segments.
	 *
	 * @param Document           $english English document.
	 * @param array<int, string> $texts Known German texts.
	 * @param array<int, string> $verbatim Known German markup.
	 */
	public static function build( Document $english, array $texts = array(), array $verbatim = array() ): self {
		return new self( $english, null, $texts, $verbatim );
	}

	/**
	 * English indexes still requiring a translation.
	 *
	 * @return list<int>
	 */
	public function missing(): array {
		if ( null !== $this->kept ) {
			return array();
		}
		return array_values( array_diff( array_keys( $this->english->segments ), array_keys( $this->texts ), array_keys( $this->verbatim ) ) );
	}

	/**
	 * Renders the German field.
	 *
	 * @param array<int, string> $translations New translations by English index.
	 */
	public function render( array $translations ): string {
		return $this->kept ?? $this->english->render( $translations + $this->texts, $this->verbatim );
	}
}
