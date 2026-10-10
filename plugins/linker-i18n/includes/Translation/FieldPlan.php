<?php
/**
 * What happens to one German field in a translation run.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * The plan for one field: keep the German as it is, or build it from the
 * English document with known German segments and new translations; a
 * built field can hold segments a person edited whose English changed.
 */
final class FieldPlan {

	/**
	 * Sets up the plan.
	 *
	 * @param Document                                                         $english  The English field.
	 * @param string|null                                                      $kept     The German value kept as it is; null when the field is built.
	 * @param bool                                                             $conflict Whether German a person edited stays under changed English.
	 * @param array<int, string>                                               $texts    English segment index => known German text (with placeholders).
	 * @param array<int, string>                                               $verbatim English segment index => known German bytes to print as they are.
	 * @param array<int, int>|string                                           $reviewed Segments a person edited, as English indexes after this run, or '*'.
	 * @param array{src: list<string>, out: list<string>, conflict: bool}|null $unit     The field's state when it is kept.
	 * @param array<int, string>                                               $held     English segment index => fingerprint of the English its German was made from, for German a person edited that stays while its English changed.
	 */
	private function __construct(
		public readonly Document $english,
		public readonly ?string $kept,
		public readonly bool $conflict,
		public readonly array $texts,
		public readonly array $verbatim,
		public readonly array|string $reviewed,
		public readonly ?array $unit,
		public readonly array $held
	) {}

	/**
	 * Keep the German value as it is.
	 *
	 * @param Document                                                    $english  The English field.
	 * @param string                                                      $german   The German value.
	 * @param bool                                                        $conflict Whether the English changed under a person's edit.
	 * @param array<int, int>|string                                      $reviewed Edited segments.
	 * @param array{src: list<string>, out: list<string>, conflict: bool} $unit     The field's state to store.
	 */
	public static function keep( Document $english, string $german, bool $conflict, array|string $reviewed, array $unit ): self {
		return new self( $english, $german, $conflict, array(), array(), $reviewed, $unit, array() );
	}

	/**
	 * Build the German value from the English document.
	 *
	 * @param Document           $english  The English field.
	 * @param array<int, string> $texts    Known German texts by English segment index.
	 * @param array<int, string> $verbatim Known German bytes by English segment index.
	 * @param array<int, int>    $reviewed Edited segments, as English indexes.
	 * @param array<int, string> $held     Edited German kept under changed English: English index => fingerprint of the English it was made from.
	 */
	public static function build( Document $english, array $texts = array(), array $verbatim = array(), array $reviewed = array(), array $held = array() ): self {
		return new self( $english, null, array() !== $held, $texts, $verbatim, $reviewed, null, $held );
	}

	/**
	 * The English segments that need a translation.
	 *
	 * @return list<int>
	 */
	public function missing(): array {
		if ( null !== $this->kept ) {
			return array();
		}
		$missing = array();
		foreach ( array_keys( $this->english->segments ) as $index ) {
			if ( ! isset( $this->texts[ $index ] ) && ! isset( $this->verbatim[ $index ] ) ) {
				$missing[] = $index;
			}
		}
		return $missing;
	}

	/**
	 * The German value.
	 *
	 * @param array<int, string> $translations New translations by English segment index.
	 */
	public function render( array $translations ): string {
		if ( null !== $this->kept ) {
			return $this->kept;
		}
		return $this->english->render( $translations + $this->texts, $this->verbatim );
	}
}
