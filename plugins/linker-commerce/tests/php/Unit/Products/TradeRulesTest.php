<?php
/**
 * Tests for the page's own trade rules.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\TradeRules;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests for TradeRules: the shipped data file's categories and their counts,
 * the language pairs, and which malformed rows are dropped rather than
 * printed.
 *
 * @covers \Linker\Commerce\Products\TradeRules
 */
final class TradeRulesTest extends TestCase {

	/**
	 * Paths this test writes and removes.
	 *
	 * @var list<string>
	 */
	private array $paths = array();

	/**
	 * Removes the fixtures.
	 */
	public function tearDown(): void {
		foreach ( $this->paths as $path ) {
			unlink( $path );
		}
		$this->paths = array();
		parent::tearDown();
	}

	/**
	 * A data file with the given categories.
	 *
	 * @param mixed $categories The `categories` array to write.
	 */
	private function data_file( mixed $categories ): string {
		$path = sys_get_temp_dir() . '/linker-commerce-trade-' . bin2hex( random_bytes( 6 ) ) . '.json';
		file_put_contents( $path, (string) json_encode( array( 'categories' => $categories ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a temp fixture on this machine.
		$this->paths[] = $path;

		return $path;
	}

	/**
	 * A complete row.
	 *
	 * @param string $en English words; the German side is `<en> (de)`.
	 * @return array{en: string, de: string}
	 */
	private function row( string $en ): array {
		return array(
			'en' => $en,
			'de' => $en . ' (de)',
		);
	}

	/**
	 * The shipped file: 5 categories, 16 questions, and every entry bilingual.
	 */
	public function test_the_shipped_file_states_five_categories_of_sixteen_questions(): void {
		$rules      = new TradeRules();
		$categories = $rules->categories();

		$this->assertCount( 5, $categories );
		$this->assertSame( 16, $rules->count() );
		foreach ( $categories as $category ) {
			$this->assertNotSame( '', trim( $category['name'] ) );
			$this->assertNotSame( array(), $category['questions'] );
			foreach ( $category['questions'] as $question ) {
				$this->assertNotSame( '', trim( $question['question'] ) );
				$this->assertNotSame( '', trim( $question['answer'] ) );
			}
		}
		$this->assertSame( 'Ordering & delivery', $categories[0]['name'] );
		$this->assertSame( 'Was ist die Mindestbestellmenge, und wohin liefert Linker?', $rules->categories( 'de' )[0]['questions'][0]['question'] );
		$this->assertSame( 'Bestellung & Lieferung', $rules->categories( 'de-DE' )[0]['name'], 'a locale answers with its language' );
	}

	/**
	 * A German side that is empty falls back to English instead of blanking the
	 * page; an English side that is empty is a missing word, and its row is
	 * dropped with the category if nothing else holds it up.
	 */
	public function test_a_half_written_row_falls_back_to_english_and_an_empty_english_side_is_dropped(): void {
		$rules = new TradeRules(
			$this->data_file(
				array(
					array(
						'name' => array(
							'en' => 'Ordering',
							'de' => '',
						),
						'qas'  => array(
							array(
								'question' => array(
									'en' => 'How does delivery work?',
									'de' => '',
								),
								'answer'   => array(
									'en' => 'By freight.',
									'de' => '',
								),
							),
						),
					),
				)
			)
		);

		$this->assertSame( 'Ordering', $rules->categories( 'de' )[0]['name'], 'the German side is empty, so the English word stands' );
		$this->assertSame( 'How does delivery work?', $rules->categories( 'de' )[0]['questions'][0]['question'] );
		$this->assertSame( 1, $rules->count() );

		$empty = new TradeRules(
			$this->data_file(
				array(
					array(
						'name' => array(
							'en' => 'Ordering',
							'de' => 'Bestellung',
						),
						'qas'  => array(
							array(
								'question' => array(
									'en' => '',
									'de' => 'Wie?',
								),
								'answer'   => $this->row( 'By freight.' ),
							),
						),
					),
				)
			)
		);
		$this->assertSame( array(), $empty->categories(), 'a question whose English side is empty is not a question' );
		$this->assertSame( 0, $empty->count() );
	}

	/**
	 * Malformed rows are dropped, and a category left without a question goes
	 * with them: the page prints what the file states, never a row the file
	 * states wrongly.
	 */
	public function test_malformed_rows_are_dropped(): void {
		$rules = new TradeRules(
			$this->data_file(
				array(
					'not a category',
					array(
						'qas' => array(
							array(
								'question' => $this->row( 'No name' ),
								'answer'   => $this->row( 'x' ),
							),
						),
					),
					array(
						'name' => 'not a pair',
						'qas'  => array(
							array(
								'question' => $this->row( 'x' ),
								'answer'   => $this->row( 'y' ),
							),
						),
					),
					array(
						'name' => $this->row( 'Empty questions' ),
						'qas'  => array( 'not a row', array( 'question' => $this->row( 'x' ) ) ),
					),
					array(
						'name' => $this->row( 'Kept' ),
						'qas'  => array(
							array(
								'question' => $this->row( 'A kept question' ),
								'answer'   => $this->row( 'A kept answer' ),
							),
							array(
								'question' => $this->row( 'A dropped one' ),
								'answer'   => 'not a pair',
							),
							array( 'question' => $this->row( 'Also dropped' ) ),
						),
					),
				)
			)
		);

		$categories = $rules->categories();
		$this->assertCount( 1, $categories, 'only the well-formed category survives' );
		$this->assertSame( 'Kept', $categories[0]['name'] );
		$this->assertCount( 1, $categories[0]['questions'] );
		$this->assertSame( 'A kept question', $categories[0]['questions'][0]['question'] );
		$this->assertSame( 1, $rules->count() );
	}

	/**
	 * A file that is absent, unreadable or not JSON is no categories, not an
	 * error: the fragments then print the zones with nothing in them.
	 */
	public function test_an_unreadable_data_file_is_no_categories(): void {
		$absent = new TradeRules( sys_get_temp_dir() . '/linker-commerce-trade-absent-' . bin2hex( random_bytes( 6 ) ) . '.json' );
		$this->assertSame( array(), $absent->categories() );
		$this->assertSame( 0, $absent->count() );

		$broken = sys_get_temp_dir() . '/linker-commerce-trade-broken-' . bin2hex( random_bytes( 6 ) ) . '.json';
		file_put_contents( $broken, '[' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a temp fixture on this machine.
		$this->paths[] = $broken;
		$this->assertSame( array(), ( new TradeRules( $broken ) )->categories() );

		$list = $this->data_file( 'not a list' );
		$this->assertSame( array(), ( new TradeRules( $list ) )->categories() );
	}
}
