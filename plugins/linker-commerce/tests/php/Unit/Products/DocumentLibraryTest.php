<?php
/**
 * Tests for the document register and the product answers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for DocumentLibrary: the register /faq-download/ lists, built from the
 * readings the product pages use.
 *
 * @covers \Linker\Commerce\Products\DocumentLibrary
 */
final class DocumentLibraryTest extends TestCase {

	/**
	 * Two products of one brand: their download entries and their FAQ field.
	 *
	 * @var array<int, array<string, mixed>>
	 */
	private const PRODUCTS = array(
		6521 => array(
			'name'      => 'GoodWe GW5.1-BAT-D-G21',
			'brand'     => 'GoodWe',
			'downloads' => array(
				array(
					'download_file'     => 900,
					'download_title'    => 'ESA battery datasheet (EN)',
					'download_type'     => 'datasheet',
					'download_language' => 'EN',
				),
				array(
					'download_file'     => 901,
					'download_title'    => 'ESA battery manual (DE)',
					'download_type'     => 'Manual',
					'download_language' => 'DE',
				),
				array(
					'download_file'     => 902,
					'download_title'    => 'Family certificate',
					'download_type'     => 'certificate',
					'download_language' => 'MULTI',
				),
			),
			'faqs'      => array(
				array(
					'question'    => 'Is the module stackable?',
					'answer'      => 'Yes, up to four modules.',
					'question_de' => 'Ist das Modul stapelbar?',
					'answer_de'   => 'Ja, bis zu vier Module.',
					'citation'    => array(
						'url'   => 'https://de-linker.test/media/901.pdf',
						'page'  => 12,
						'title' => 'ESA battery manual',
					),
				),
			),
			'legacy'    => array(),
		),
		6522 => array(
			'name'      => 'GoodWe GW8.3-BAT-D-G21',
			'brand'     => 'GoodWe',
			'downloads' => array(
				array(
					'download_file'     => 900,
					'download_title'    => 'ESA battery datasheet (EN)',
					'download_type'     => 'datasheet',
					'download_language' => 'EN',
				),
				array(
					'download_file'     => 903,
					'download_title'    => 'A brochure',
					'download_type'     => 'leaflet',
					'download_language' => '',
				),
			),
			'faqs'      => array(),
			'legacy'    => array(
				array(
					'faq_question' => 'Legacy question?',
					'faq_answer'   => 'Legacy answer.',
				),
			),
		),
	);

	/**
	 * The WordPress reads of the fixture.
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
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 6521, 6522 ) ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn ( int $id ): string => self::PRODUCTS[ $id ]['name'] ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => static fn ( int $id ): string => 'https://de-linker.test/produkt/' . $id . '/' ) );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) {
					if ( 'pa_brand' !== $taxonomy ) {
						return false;
					}
					return array(
						(object) array(
							'term_id' => 30,
							'slug'    => strtolower( self::PRODUCTS[ $id ]['brand'] ),
							'name'    => self::PRODUCTS[ $id ]['brand'],
						),
					);
				},
			)
		);
		WP_Mock::userFunction(
			'wp_get_attachment_url',
			array(
				'return' => static fn ( int $id ): string => 'https://de-linker.test/media/' . $id . '.pdf',
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) {
					$product = self::PRODUCTS[ $id ];
					return match ( $key ) {
						'_tv_legacy_acf_json' => (string) json_encode(
							array(
								'downloads' => $product['downloads'],
								'faqs'      => $product['legacy'],
							)
						),
						'_linker_faqs'        => (string) json_encode( $product['faqs'] ),
						default               => '',
					};
				},
			)
		);
	}

	/**
	 * One row per file even when several products state it, and the row says
	 * which products it covers.
	 */
	public function test_documents_are_deduplicated_by_file_and_count_their_products(): void {
		$documents = array_column( ( new DocumentLibrary() )->documents(), null, 'title' );

		$this->assertCount( 4, $documents, 'five entries, one file stated by both products' );
		$this->assertSame(
			array( 'GoodWe GW5.1-BAT-D-G21', 'GoodWe GW8.3-BAT-D-G21' ),
			$documents['ESA battery datasheet (EN)']['covers']
		);
		$this->assertSame( array( 'GoodWe GW5.1-BAT-D-G21' ), $documents['ESA battery manual (DE)']['covers'] );
		$this->assertSame( 'GoodWe', $documents['ESA battery manual (DE)']['brand'] );
	}

	/**
	 * The stored type and language words become the register's own: a known
	 * type lowercased, an unknown one `Document`; a language word normalised,
	 * an absent one `EN`.
	 */
	public function test_type_and_language_are_normalised(): void {
		$documents = array_column( ( new DocumentLibrary() )->documents(), null, 'title' );

		$this->assertSame( 'manual', $documents['ESA battery manual (DE)']['type'] );
		$this->assertSame( 'DE', $documents['ESA battery manual (DE)']['language'] );
		$this->assertSame( 'document', $documents['A brochure']['type'] );
		$this->assertSame( 'EN', $documents['A brochure']['language'] );
		$this->assertSame( 'MUL', $documents['Family certificate']['language'] );
	}

	/**
	 * The register is ordered by type first, then by title — the order the
	 * live register used.
	 */
	public function test_the_register_is_ordered_by_type(): void {
		$documents = ( new DocumentLibrary() )->documents();

		$this->assertSame(
			array( 'datasheet', 'manual', 'certificate', 'document' ),
			array_map(
				static function ( array $document ): string {
					return $document['type'];
				},
				$documents
			)
		);
		$this->assertSame( 'A brochure', $documents[3]['title'] );
	}

	/**
	 * The #15 FAQ field answers where it is filled, the legacy product FAQ
	 * until then; German reads the German words of the field.
	 */
	public function test_answers_prefer_the_faq_field_and_fall_back_to_the_legacy_list(): void {
		$library = new DocumentLibrary();
		$english = $library->answers( 'en' );
		$german  = $library->answers( 'de' );

		$this->assertSame( 'Is the module stackable?', $english[0]['question'] );
		$this->assertSame( 'GoodWe GW5.1-BAT-D-G21', $english[0]['product'] );
		$this->assertSame( 'Ist das Modul stapelbar?', $german[0]['question'] );
		$this->assertSame( 'ESA battery manual, p. 12', $english[0]['source'], 'the answer cites the document it came from' );
		$this->assertSame( 'Legacy question?', $english[1]['question'], 'the field is empty, so the product FAQ answers' );
		$this->assertSame( '', $english[1]['source'], 'a legacy answer cites no page' );
	}
}
