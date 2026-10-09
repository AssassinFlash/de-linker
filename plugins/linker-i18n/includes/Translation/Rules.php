<?php
/**
 * The glossary and the banned words.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * The language rules of the German site, read from data/glossary-de.json
 * and data/banned-de.json.
 */
final class Rules {

	/**
	 * Sets up the rules.
	 *
	 * @param array<int, array{en: string, de: string, enforce: bool}> $terms  Glossary entries.
	 * @param array<int, string>                                       $keep   Names that stay as they are.
	 * @param array<int, string>                                       $banned Banned words; a trailing * matches compounds.
	 */
	public function __construct( public readonly array $terms, public readonly array $keep, public readonly array $banned ) {}

	/**
	 * Reads the rules from the plugin's data directory.
	 *
	 * @param string $directory Directory holding glossary-de.json and banned-de.json.
	 * @throws \RuntimeException When a file is missing or not the expected JSON.
	 */
	public static function load( string $directory ): self {
		$glossary = self::read( $directory . '/glossary-de.json' );
		$banned   = self::read( $directory . '/banned-de.json' );
		$terms    = array();
		foreach ( (array) ( $glossary['terms'] ?? array() ) as $term ) {
			if ( is_array( $term ) && isset( $term['en'], $term['de'] ) && is_string( $term['en'] ) && is_string( $term['de'] ) ) {
				$terms[] = array(
					'en'      => $term['en'],
					'de'      => $term['de'],
					'enforce' => true === ( $term['enforce'] ?? false ),
				);
			}
		}
		return new self(
			$terms,
			array_values( array_filter( (array) ( $glossary['keep'] ?? array() ), 'is_string' ) ),
			array_values( array_filter( (array) ( $banned['words'] ?? array() ), 'is_string' ) )
		);
	}

	/**
	 * Whether an English text uses a glossary term (whole words; a space and
	 * a hyphen count as the same, a plural s is allowed).
	 *
	 * @param string $term English term.
	 * @param string $text English text.
	 */
	public static function uses( string $term, string $text ): bool {
		// preg_quote() escapes a hyphen but not a space.
		$pattern = str_replace( array( ' ', '\\-' ), '[\\s-]', preg_quote( $term, '/' ) );
		return 1 === preg_match( '/(?<![\\p{L}\\p{N}])' . $pattern . 's?(?![\\p{L}\\p{N}])/iu', $text );
	}

	/**
	 * The banned words a German text contains.
	 *
	 * @param string $text German text.
	 * @return list<string>
	 */
	public function banned_in( string $text ): array {
		$found = array();
		foreach ( $this->banned as $word ) {
			$stem    = rtrim( $word, '*' );
			$pattern = '/(?<![\\p{L}\\p{N}])' . preg_quote( $stem, '/' ) . ( str_ends_with( $word, '*' ) ? '' : '(?![\\p{L}\\p{N}])' ) . '/iu';
			if ( 1 === preg_match( $pattern, $text ) ) {
				$found[] = $stem;
			}
		}
		return $found;
	}

	/**
	 * Reads one JSON data file.
	 *
	 * @param string $path File path.
	 * @return array<mixed>
	 * @throws \RuntimeException When the file is missing or not a JSON object.
	 */
	private static function read( string $path ): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a file of this plugin.
		$json = is_readable( $path ) ? file_get_contents( $path ) : false;
		$data = false === $json ? null : json_decode( $json, true );
		if ( ! is_array( $data ) ) {
			throw new \RuntimeException( esc_html( sprintf( 'Cannot read %s.', basename( $path ) ) ) );
		}
		return $data;
	}
}
