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
	use \Linker\Commerce\Tests\Support\PublishedDocumentView;
	use \Linker\Commerce\Tests\Support\BoundFaqFixture;

	/**
	 * Only the declared prepared answers receive fixture evidence bindings.
	 *
	 * @var array<int,array<string,array{document_id:string,blob_sha256:string,figure_revision:string}>>
	 */
	private array $current_faq_bindings = array();

	/**
	 * Explicitly maintained FAQ source records of this fixture.
	 *
	 * @var array<int,string>
	 */
	private array $managed_faqs = array();

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
				// The German table stores German type words with the row's
				// role beside them; the register reads the same type as the
				// English table does (2026-10-16).
				array(
					'download_file'     => 904,
					'download_title'    => 'ESA-Batterie-Datenblatt (DE)',
					'download_type'     => 'Datenblatt',
					'download_role'     => 'datasheet',
					'download_language' => 'DE',
				),
				array(
					'download_file'     => 905,
					'download_title'    => 'ESA-Batterie-Kompatibilitätsliste (DE)',
					'download_type'     => 'Kompatibilitätsliste',
					'download_role'     => 'compatibility_list',
					'download_language' => 'DE',
				),
				array(
					'download_file'     => 906,
					'download_title'    => 'ESA-Batterie-Broschüre (DE)',
					'download_type'     => 'Broschüre',
					'download_role'     => 'brochure',
					'download_language' => 'DE',
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
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' )->byDefault();
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' )->byDefault();
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) )->byDefault();
		$this->current_faq_bindings = array( 6521 => self::bound_faqs( self::PRODUCTS[6521]['faqs'], 'fixture-manual', hash( 'sha256', 'fixture manual bytes' ) ) );
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
				'return' => function ( int $id, string $key ) {
					$product = self::PRODUCTS[ $id ];
					return match ( $key ) {
						'_tv_legacy_acf_json' => (string) json_encode(
							array(
								'downloads' => $product['downloads'],
								'faqs'      => $product['legacy'],
							)
						),
						'_linker_faqs'        => (string) json_encode( $product['faqs'] ),
						'_linker_faqs_managed' => $this->managed_faqs[ $id ] ?? '',
						\Linker\Commerce\Products\Publication\EvidenceBindings::FAQ_META_KEY => $this->current_faq_bindings[ $id ] ?? array(),
						default               => '',
					};
				},
			)
		);
	}

	/**
	 * Current authoritative products and document relations of the fixture.
	 *
	 * @return array<string,mixed>
	 */
	private function manifest(): array {
		return array(
			'products'  => array_map(
				static fn ( int $id ): array => array(
					'product_id'           => $id,
					'published_locale_ids' => array( $id ),
				),
				array_keys( self::PRODUCTS )
			),
			'documents' => array(
				array(
					'product_ids' => array( 6521 ),
					'document_id' => 'fixture-manual',
					'blob_sha256' => hash( 'sha256', 'fixture manual bytes' ),
					'aliases'     => array( 'https://de-linker.test/media/901.pdf' ),
				),
			),
		);
	}

	/** Native published translations do not override canonical withdrawal. */
	public function test_library_omits_a_product_without_current_publication_permission(): void {
		$manifest = $this->manifest();
		$reads    = 0;
		$library  = new DocumentLibrary(
			$this->published_document_view(),
			static function () use ( &$manifest, &$reads ): array {
				++$reads;
				return $manifest;
			}
		);
		$this->assertNotEmpty( $library->entries()['answers'] );
		$manifest['products'] = array( $manifest['products'][1] );
		$withdrawn            = $library->entries();
		$this->assertSame( 2, $reads, 'A new assembly must re-read current permission.' );
		$this->assertSame( array(), $withdrawn['answers'] );
		foreach ( $withdrawn['documents'] as $document ) {
			$this->assertNotContains( 'GoodWe GW5.1-BAT-D-G21', $document['covers'] );
		}
	}

	/** Withdrawing cited evidence suppresses its answer without a legacy fallback. */
	public function test_library_omits_answers_whose_cited_document_is_withdrawn(): void {
		$manifest              = $this->manifest();
		$manifest['documents'] = array();
		$library               = new DocumentLibrary( $this->published_document_view(), static fn (): array => $manifest );
		$this->assertSame( array(), $library->answers() );
	}

	/** A current URL alone does not grant an unprepared answer its current evidence. */
	public function test_cited_answer_requires_an_explicit_current_binding(): void {
		$this->current_faq_bindings = array();
		$library                    = new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() );
		$this->assertSame( array(), $library->answers() );
	}

	/** Replacement bytes invalidate old answer text and the page URL together. */
	public function test_same_url_replacement_omits_old_answer_and_source_page(): void {
		$manifest                                = $this->manifest();
		$manifest['documents'][0]['blob_sha256'] = hash( 'sha256', 'replacement manual bytes' );
		$library                                 = new DocumentLibrary( $this->published_document_view(), static fn (): array => $manifest );
		$this->assertSame( array(), $library->answers() );
	}

	/** An intentionally emptied FAQ field cannot restore an older ACF answer. */
	public function test_maintained_empty_faq_list_cannot_fall_back_to_old_answers(): void {
		$this->managed_faqs[6522] = '1';
		$library                  = new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() );
		$this->assertSame( array( 'Is the module stackable?' ), array_column( $library->answers(), 'question' ) );
	}

	/**
	 * One row per file even when several products state it, and the row says
	 * which products it covers.
	 */
	public function test_documents_are_deduplicated_by_file_and_count_their_products(): void {
		$documents = array_column( ( new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() ) )->documents(), null, 'title' );

		$this->assertCount( 7, $documents, 'eight entries, one file stated by both products' );
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
		$documents = array_column( ( new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() ) )->documents(), null, 'title' );

		$this->assertSame( 'manual', $documents['ESA battery manual (DE)']['type'] );
		$this->assertSame( 'DE', $documents['ESA battery manual (DE)']['language'] );
		$this->assertSame( 'document', $documents['A brochure']['type'] );
		$this->assertSame( 'EN', $documents['A brochure']['language'] );
		$this->assertSame( 'MUL', $documents['Family certificate']['language'] );
	}

	/**
	 * A German row reads the same type as its English twin: the German table
	 * stores German type words (`Datenblatt`, `Broschüre`) with the row's
	 * role beside them, and the register resolves both through the mapping
	 * the product page's document cards use. Until 2026-10-16 the register
	 * knew only the English words, so every German row read `Document` and
	 * the type chips had nothing to tell apart.
	 */
	public function test_german_rows_read_the_same_type_as_their_english_twin(): void {
		$documents = array_column( ( new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() ) )->documents(), null, 'title' );

		$this->assertSame( 'datasheet', $documents['ESA-Batterie-Datenblatt (DE)']['type'] );
		$this->assertSame( 'compatibility', $documents['ESA-Batterie-Kompatibilitätsliste (DE)']['type'] );
		$this->assertSame( 'brochure', $documents['ESA-Batterie-Broschüre (DE)']['type'] );
		// The vocabulary stays finite: a German word the mapping does not
		// know (and the register's own list lacks) still reads `Document`.
		$this->assertSame( 'document', DocumentLibrary::type( 'Installationshandbuch' ) );
		$this->assertSame( 'manual', DocumentLibrary::type( 'Handbuch' ) );
	}

	/**
	 * The register is ordered by type first, then by title — the order the
	 * live register used.
	 */
	public function test_the_register_is_ordered_by_type(): void {
		$documents = ( new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() ) )->documents();

		$this->assertSame(
			array( 'datasheet', 'datasheet', 'manual', 'certificate', 'compatibility', 'brochure', 'document' ),
			array_map(
				static function ( array $document ): string {
					return $document['type'];
				},
				$documents
			)
		);
		$this->assertSame( 'A brochure', $documents[6]['title'] );
	}

	/**
	 * Cited current answers use their requested language. Unbound old metadata
	 * never provides a fallback when a maintained answer is absent.
	 */
	public function test_answers_require_current_citations_without_unbound_fallbacks(): void {
		$library = new DocumentLibrary( $this->published_document_view(), fn (): array => $this->manifest() );
		$english = $library->answers( 'en' );
		$german  = $library->answers( 'de' );

		$this->assertSame( 'Is the module stackable?', $english[0]['question'] );
		$this->assertSame( 'GoodWe GW5.1-BAT-D-G21', $english[0]['product'] );
		$this->assertSame( 'GoodWe', $english[0]['brand'], 'the row names its product brand, so the register files it' );
		$this->assertSame( 'Ist das Modul stapelbar?', $german[0]['question'] );
		$this->assertSame( 'ESA battery manual, p. 12', $english[0]['source'], 'the answer cites the document it came from' );
		$this->assertCount( 1, $english );
		$this->assertCount( 1, $german );
	}
}
