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
