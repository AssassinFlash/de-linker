<?php
/**
 * Checks a translation before it is stored.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Accepts a translated segment only when it keeps everything that must not
 * change: each placeholder once and properly nested, every figure, every
 * name to keep; and when it follows the glossary and uses no banned word.
 */
final class Validator {

	/**
	 * A figure: digits with decimal separators, or thousands separated by a
	 * point, comma or (no-break) space before exactly three digits.
	 */
	private const FIGURE = '/\d+(?:[.,]\d+|[ \x{00A0}\x{202F}]\d{3}(?!\d))*/u';

	/**
	 * Sets up the validator.
	 *
	 * @param Rules $rules Glossary and banned words.
	 */
	public function __construct( private readonly Rules $rules ) {}

	/**
	 * What is wrong with a translation; empty when it can be stored.
	 *
	 * @param Segment $source      The English segment.
	 * @param string  $translation The German text.
	 * @return list<string>
	 */
	public function problems( Segment $source, string $translation ): array {
		if ( '' === trim( $translation ) ) {
			return array( 'empty translation' );
		}
		$problems = array();
		if ( ! $this->same_placeholders( $source->text, $translation ) ) {
			$problems[] = 'placeholders changed';
		}
		if ( self::figures( $source->text ) !== self::figures( $translation ) ) {
			$problems[] = 'figures changed';
		}
		$english = self::plain( $source->text );
		$german  = self::plain( $translation );
		foreach ( $this->rules->terms as $term ) {
			if ( $term['enforce'] && Rules::uses( $term['en'], $english ) && false === mb_stripos( $german, $term['de'] ) ) {
				$problems[] = sprintf( 'glossary: "%s" must be "%s"', $term['en'], $term['de'] );
			}
		}
		foreach ( $this->rules->keep as $name ) {
			if ( str_contains( $english, $name ) && ! str_contains( $german, $name ) ) {
				$problems[] = sprintf( 'name changed: "%s"', $name );
			}
		}
		foreach ( $this->rules->banned_in( $german ) as $word ) {
			$problems[] = sprintf( 'banned word: "%s"', $word );
		}
		return $problems;
	}

	/**
	 * Whether the translation has each placeholder of the source exactly once,
	 * with every pair opened before it is closed and pairs nested.
	 *
	 * @param string $source      Source text.
	 * @param string $translation Translated text.
	 */
	private function same_placeholders( string $source, string $translation ): bool {
		$expected = Segment::placeholders( $source );
		$actual   = Segment::placeholders( $translation );
		$sorted   = $actual;
		sort( $expected );
		sort( $sorted );
		if ( $expected !== $sorted ) {
			return false;
		}
		$open = array();
		foreach ( $actual as $placeholder ) {
			if ( str_starts_with( $placeholder, '/' ) ) {
				if ( array_pop( $open ) !== substr( $placeholder, 1 ) ) {
					return false;
				}
			} elseif ( ! str_ends_with( $placeholder, '/' ) ) {
				$open[] = $placeholder;
			}
		}
		return array() === $open;
	}

	/**
	 * The figures of a text as digit strings, sorted: 29,999 W and
	 * 29.999 W are both 29999, 20.0 and 20,0 both 200.
	 *
	 * @param string $text Text.
	 * @return list<string>
	 */
	private static function figures( string $text ): array {
		preg_match_all( self::FIGURE, self::plain( $text ), $matches );
		$figures = array_map( static fn( string $figure ): string => (string) preg_replace( '/\D/u', '', $figure ), $matches[0] );
		sort( $figures );
		return $figures;
	}

	/**
	 * Text without placeholders.
	 *
	 * @param string $text Text.
	 */
	private static function plain( string $text ): string {
		return (string) preg_replace( Segment::PLACEHOLDER, ' ', $text );
	}
}
