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
	 * @param array<int, string> $verbatim Known German markup by English index.
	 * @param Document|null      $target Existing German markup; only changed sentence slots are replaced.
	 * @param bool               $mismatch Whether alignment failed and all German must stay.
	 */
	private function __construct(
		public readonly Document $english,
		public readonly ?string $kept,
		public readonly array $verbatim,
		public readonly ?Document $target = null,
		public readonly bool $mismatch = false
	) {}

	/**
	 * Keeps an unchanged field.
	 *
	 * @param Document $english English document.
	 * @param string   $german German field.
	 */
	public static function keep( Document $english, string $german ): self {
		return new self( $english, $german, array() );
	}

	/**
	 * Keeps German and exposes an alignment exception without model work.
	 *
	 * @param Document $english Current English.
	 * @param string   $german Existing German, byte for byte.
	 */
	public static function blocked( Document $english, string $german ): self {
		return new self( $english, $german, array(), null, true );
	}

	/**
	 * Builds from English markup with known and newly translated segments.
	 *
	 * @param Document           $english English document.
	 * @param array<int, string> $verbatim Known German markup.
	 * @param Document|null      $target Existing German markup, if aligned.
	 */
	public static function build( Document $english, array $verbatim = array(), ?Document $target = null ): self {
		return new self( $english, null, $verbatim, $target );
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
		return array_values( array_diff( array_keys( $this->english->segments ), array_keys( $this->verbatim ) ) );
	}

	/**
	 * Renders the German field.
	 *
	 * @param array<int, string> $translations New translations by English index.
	 * @param callable|null      $localize Localises new HTML only, leaving preserved German bytes alone.
	 * @phpstan-param (callable(string): string)|null $localize
	 */
	public function render( array $translations, ?callable $localize = null ): string {
		if ( null !== $this->kept ) {
			return $this->kept;
		}
		if ( null === $this->target ) {
			$html = $this->english->render( $translations, $this->verbatim );
			return null === $localize ? $html : $localize( $html );
		}
		$bytes = array();
		foreach ( $translations as $index => $text ) {
			$segment = $this->english->segments[ $index ];
			$map     = $segment->map;
			foreach ( $map as $key => $part ) {
				if ( $part instanceof TagPart ) {
					foreach ( $this->target->segments[ $index ]->map as $german ) {
						if ( $german instanceof TagPart && $german->attributes === $part->attributes ) {
							$map[ $key ] = new TagPart( $german->tag, $part->attributes );
							break;
						}
					}
				}
			}
			$changed         = new Segment( $segment->text, $segment->raw, $map, $segment->html );
			$html            = $changed->render( $text, $translations );
			$bytes[ $index ] = null === $localize ? $html : $localize( $html );
		}
		return $this->target->render( array(), $bytes );
	}
}
