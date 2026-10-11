<?php
/**
 * Tests for the library page's two fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\LibraryPage;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for LibraryPage: the document register and the product answers as the
 * LiveCanvas template prints them.
 *
 * @covers \Linker\Commerce\Presentation\LibraryPage
 */
final class LibraryPageTest extends TestCase {

	/**
	 * One product, one file, one answer.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'wp_specialchars_decode', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'has_filter',
			array(
				'return' => false,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => 0,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'pll_current_language',
			array(
				'return' => 'en',
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction( 'sanitize_title', array( 'return' => static fn ( string $value ): string => strtolower( str_replace( ' ', '-', $value ) ) ) );
		WP_Mock::userFunction( 'wpautop', array( 'return' => static fn ( string $value ): string => '<p>' . $value . '</p>' ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 6521 ) ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'GoodWe GW5.1-BAT-D-G21' ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://de-linker.test/produkt/goodwe-gw5-1/' ) );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static fn ( int $id, string $taxonomy ) => 'pa_brand' === $taxonomy
					? array(
						(object) array(
							'term_id' => 30,
							'slug'    => 'goodwe',
							'name'    => 'GoodWe',
						),
					)
					: false,
			)
		);
		WP_Mock::userFunction( 'wp_get_attachment_url', array( 'return' => 'https://de-linker.test/media/900.pdf' ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ): string {
					return match ( $key ) {
						'_tv_legacy_acf_json' => (string) json_encode(
							array(
								'downloads' => array(
									array(
										'download_file'  => 900,
										'download_title' => 'ESA battery datasheet (EN)',
										'download_type'  => 'datasheet',
										'download_language' => 'EN',
									),
								),
								'faqs'      => array(),
							)
						),
						'_linker_faqs'        => (string) json_encode(
							array(
								array(
									'question' => 'Is the module stackable?',
									'answer'   => 'Yes, up to four modules.',
									'citation' => array(
										'url'   => 'https://de-linker.test/media/901.pdf',
										'page'  => 12,
										'title' => 'ESA battery manual',
									),
								),
							)
						),
						default               => '',
					};
				},
			)
		);
	}

	/**
	 * The register: one row per file with its type, what it covers, its
	 * language and a download link — no script, so the page is complete
	 * without JavaScript.
	 */
	public function test_the_register_lists_each_document_with_its_metadata(): void {
		$html = ( new LibraryPage() )->register_documents();

		$this->assertStringContainsString( 'id="linker-documents"', $html );
		$this->assertStringContainsString( 'GoodWe', $html );
		$this->assertStringContainsString( '1 document', $html );
		$this->assertStringContainsString( 'Datasheet', $html );
		$this->assertStringContainsString( 'ESA battery datasheet (EN)', $html );
		$this->assertStringContainsString( 'covers GoodWe GW5.1-BAT-D-G21', $html );
		$this->assertStringContainsString( 'English', $html );
		$this->assertStringContainsString( 'href="https://de-linker.test/media/900.pdf"', $html );
		$this->assertStringContainsString( 'Download', $html );
		$this->assertStringNotContainsString( '<script', $html );
	}

	/**
	 * The answers: each question with its answer, the product it belongs to
	 * and the page it came from.
	 */
	public function test_the_answers_list_the_questions_of_the_products(): void {
		$html = ( new LibraryPage() )->product_answers();

		$this->assertStringContainsString( 'id="linker-answers"', $html );
		$this->assertStringContainsString( 'Is the module stackable?', $html );
		$this->assertStringContainsString( 'Yes, up to four modules.', $html );
		$this->assertStringContainsString( '<a href="https://de-linker.test/produkt/goodwe-gw5-1/">GoodWe GW5.1-BAT-D-G21</a>', $html );
		$this->assertStringContainsString( 'ESA battery manual, p. 12', $html );
		$this->assertStringContainsString( 'href="https://de-linker.test/media/901.pdf#page=12"', $html );
	}
}
