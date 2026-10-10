<?php
/**
 * Tests for the FAQ list reader.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\Faqs;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Faqs: only a row with an English question and a citation (url and
 * page ≥ 1) is kept.
 *
 * @covers \Linker\Commerce\Catalog\Faqs
 */
final class FaqsTest extends TestCase {

	private const PRODUCT = 1959;

	/**
	 * The mirror writes the English product's list onto its German twin.
	 */
	public function test_mirror_writes_the_twin_of_an_english_product(): void {
		WP_Mock::passthruFunction( 'wp_slash' );
		$this->mock_twin( self::PRODUCT, 'en', 889 );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'args'  => array( 889, '_linker_faqs', '[]' ),
				'times' => 1,
			)
		);

		Faqs::mirror_to_twin( self::PRODUCT, '[]' );

		$this->assertConditionsMet();
	}

	/**
	 * The mirror writes the German product's list onto its English twin.
	 */
	public function test_mirror_writes_the_twin_of_a_german_product(): void {
		WP_Mock::passthruFunction( 'wp_slash' );
		$this->mock_twin( 889, 'de', self::PRODUCT );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'args'  => array( self::PRODUCT, '_linker_faqs', '[]' ),
				'times' => 1,
			)
		);

		Faqs::mirror_to_twin( 889, '[]' );

		$this->assertConditionsMet();
	}

	/**
	 * A language the FAQ twin rule does not pair (not en, not de) writes
	 * nothing.
	 */
	public function test_mirror_is_silent_for_an_unpaired_language(): void {
		$this->mock_twin( self::PRODUCT, 'fr', 889 );
		WP_Mock::userFunction( 'update_post_meta' )->never();

		Faqs::mirror_to_twin( self::PRODUCT, '[]' );

		$this->assertConditionsMet();
	}

	/**
	 * Without a twin nothing is written.
	 */
	public function test_mirror_is_silent_without_a_twin(): void {
		$this->mock_twin( self::PRODUCT, 'en', 0 );
		WP_Mock::userFunction( 'update_post_meta' )->never();

		Faqs::mirror_to_twin( self::PRODUCT, '[]' );

		$this->assertConditionsMet();
	}

	/**
	 * A post that is its own twin is not written (the self-write would
	 * duplicate the list onto itself).
	 */
	public function test_mirror_is_silent_when_the_post_is_its_own_twin(): void {
		$this->mock_twin( self::PRODUCT, 'en', self::PRODUCT );
		WP_Mock::userFunction( 'update_post_meta' )->never();

		Faqs::mirror_to_twin( self::PRODUCT, '[]' );

		$this->assertConditionsMet();
	}

	/**
	 * Mocks the Polylang pair: the post's language and its twin.
	 *
	 * @param int    $post_id  The product the mirror runs on.
	 * @param string $language The post's language.
	 * @param int    $twin     The twin ID, 0 for none.
	 */
	private function mock_twin( int $post_id, string $language, int $twin ): void {
		WP_Mock::userFunction(
			'pll_get_post_language',
			array(
				'args'   => array( $post_id ),
				'return' => $language,
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( $post_id, 'en' === $language ? 'de' : 'en' ),
				'return' => $twin,
			)
		);
	}

	/**
	 * A stored list keeps the well-formed rows and drops the rest.
	 */
	public function test_of_keeps_cited_questions_and_drops_the_rest(): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( self::PRODUCT, '_linker_faqs', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode(
					array(
						array(
							'question'    => 'What does X stand for?',
							'answer'      => 'The battery option.',
							'question_de' => 'Wofür steht X?',
							'answer_de'   => 'Die Batterieoption.',
							'citation'    => array(
								'url'   => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
								'page'  => 2,
								'title' => 'CHS2 datasheet',
							),
						),
						array(
							'question' => 'No citation',
							'answer'   => 'Dropped.',
						),
						array(
							'question' => '',
							'answer'   => 'Empty question.',
							'citation' => array(
								'url'  => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
								'page' => 1,
							),
						),
					)
				),
			)
		);

		$items = Faqs::of( self::PRODUCT );

		$this->assertCount( 1, $items );
		$this->assertSame( 'What does X stand for?', $items[0]['question'] );
			$this->assertSame( 2, $items[0]['citation']['page'] );
			$this->assertSame( 'CHS2 datasheet', $items[0]['citation']['title'] ?? '' );
	}

	/**
	 * Encode round-trips a well-formed item and drops a page of zero.
	 */
	public function test_encode_drops_a_page_below_one(): void {
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => static fn( $data ): string => (string) json_encode( $data ),
			)
		);
		$json  = Faqs::encode(
			array(
				array(
					'question' => 'Kept',
					'answer'   => 'Yes.',
					'citation' => array(
						'url'  => 'https://de-linker.com/a.pdf',
						'page' => 1,
					),
				),
				array(
					'question' => 'Zero page',
					'answer'   => 'No.',
					'citation' => array(
						'url'  => 'https://de-linker.com/a.pdf',
						'page' => 0,
					),
				),
			)
		);
		$items = json_decode( $json, true );

		$this->assertCount( 1, $items );
		$this->assertSame( 'Kept', $items[0]['question'] );
	}
}
