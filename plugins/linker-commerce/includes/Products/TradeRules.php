<?php
/**
 * The trade rules of /faq-download/ ("Before you order").
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use Linker\Commerce\Abilities\ProductText;

/**
 * The page's own 16 B2B questions in 5 categories (data/faq-trade.json). The
 * answers are frozen approved content and read verbatim; the file is the one
 * source for the register's rail, its mobile chip row, the card headings and
 * the answers, so a card's count cannot disagree with the entries under it.
 *
 * Until #176 these questions lived in the two LiveCanvas templates, one
 * language per file, and the counts around them were hand-written. The
 * templates now carry the page's structure and headline copy; this data file
 * carries the rules themselves, and tools/faq/extract-trade.py is where the
 * file came from (it re-reads the templates at the revision that still had
 * them, so the move is reproducible).
 *
 * The file is read once per instance, and its path is the constructor's: the
 * plugin's own shipped file by default, a fixture in tests.
 */
final class TradeRules {

	/**
	 * The shipped data file.
	 */
	public const FILE = 'faq-trade.json';

	/**
	 * Absolute path of the data file.
	 *
	 * @var string
	 */
	private readonly string $path;

	/**
	 * The well-formed categories, read on first use.
	 *
	 * @var list<array{name: array{en: string, de: string}, qas: list<array{question: array{en: string, de: string}, answer: array{en: string, de: string}}>}>|null
	 */
	private ?array $categories = null;

	/**
	 * Sets up the reader.
	 *
	 * @param string|null $path Data-file override (tests); the shipped file
	 *                          when null.
	 */
	public function __construct( ?string $path = null ) {
		$this->path = $path ?? dirname( __DIR__, 2 ) . '/data/' . self::FILE;
	}

	/**
	 * The categories in stored order, each with its questions in `$lang`.
	 *
	 * @param string $lang Language of the words ('de' or 'en').
	 * @return list<array{name: string, questions: list<array{question: string, answer: string}>}>
	 */
	public function categories( string $lang = 'en' ): array {
		$language = ProductText::lang( $lang );
		$out      = array();
		foreach ( $this->raw() as $category ) {
			$questions = array();
			foreach ( $category['qas'] as $qa ) {
				$questions[] = array(
					'question' => self::word( $qa['question'], $language ),
					'answer'   => self::word( $qa['answer'], $language ),
				);
			}
			$out[] = array(
				'name'      => self::word( $category['name'], $language ),
				'questions' => $questions,
			);
		}

		return $out;
	}

	/**
	 * The question count over every category.
	 */
	public function count(): int {
		$count = 0;
		foreach ( $this->raw() as $category ) {
			$count += count( $category['qas'] );
		}

		return $count;
	}

	/**
	 * A stored pair of words in the page's language, the English one when the
	 * German side is empty (the data is written in pairs, and a half-written
	 * row must not blank the page).
	 *
	 * @param array{en: string, de: string} $pair Stored pair.
	 * @param 'en'|'de'                     $language Page language.
	 */
	private static function word( array $pair, string $language ): string {
		return 'de' === $language && '' !== trim( $pair['de'] ) ? $pair['de'] : $pair['en'];
	}

	/**
	 * The well-formed categories of the data file; rows the file states
	 * wrongly are dropped rather than printed. An unreadable file is no
	 * categories, not an error.
	 *
	 * @return list<array{name: array{en: string, de: string}, qas: list<array{question: array{en: string, de: string}, answer: array{en: string, de: string}}>}>
	 */
	private function raw(): array {
		if ( null !== $this->categories ) {
			return $this->categories;
		}
		$out = array();
		if ( is_readable( $this->path ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local plugin data file on disk, not a remote URL.
			$payload = json_decode( (string) file_get_contents( $this->path ), true );
			foreach ( is_array( $payload ) ? (array) ( $payload['categories'] ?? array() ) : array() as $category ) {
				$row = self::category( $category );
				if ( null !== $row ) {
					$out[] = $row;
				}
			}
		}
		$this->categories = $out;

		return $out;
	}

	/**
	 * One well-formed category, or null: a category needs a named pair of
	 * words and at least one question whose own pair is complete.
	 *
	 * @param mixed $category Decoded row.
	 * @return array{name: array{en: string, de: string}, qas: list<array{question: array{en: string, de: string}, answer: array{en: string, de: string}}>}|null
	 */
	private static function category( mixed $category ): ?array {
		if ( ! is_array( $category ) ) {
			return null;
		}
		$name = self::pair( $category['name'] ?? null );
		if ( null === $name ) {
			return null;
		}
		$qas = array();
		foreach ( (array) ( $category['qas'] ?? array() ) as $qa ) {
			if ( ! is_array( $qa ) ) {
				continue;
			}
			$question = self::pair( $qa['question'] ?? null );
			$answer   = self::pair( $qa['answer'] ?? null );
			if ( null === $question || null === $answer ) {
				continue;
			}
			$qas[] = array(
				'question' => $question,
				'answer'   => $answer,
			);
		}
		if ( array() === $qas ) {
			return null;
		}

		return array(
			'name' => $name,
			'qas'  => $qas,
		);
	}

	/**
	 * A decoded {en, de} pair, or null when the row is not one: an empty
	 * English side is a missing word, not a translation gap.
	 *
	 * @param mixed $pair Decoded row.
	 * @return array{en: string, de: string}|null
	 */
	private static function pair( mixed $pair ): ?array {
		if ( ! is_array( $pair ) || ! is_string( $pair['en'] ?? null ) || '' === trim( $pair['en'] ) ) {
			return null;
		}

		return array(
			'en' => $pair['en'],
			'de' => is_string( $pair['de'] ?? null ) ? $pair['de'] : '',
		);
	}
}
