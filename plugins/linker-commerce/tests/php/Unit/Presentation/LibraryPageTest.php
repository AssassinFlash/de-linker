<?php
/**
 * Tests for the library page's fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\LibraryPage;
use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for LibraryPage: the register's rail and chips, the FAQ tab's cards,
 * the documents tab's cards and its type chips, the counts the template
 * prints, and the interaction layer's config — all as the LiveCanvas template
 * prints them, without JavaScript.
 *
 * @covers \Linker\Commerce\Presentation\LibraryPage
 */
final class LibraryPageTest extends TestCase {

	/**
	 * Post queries the fragments ran: the register's readings and the brand
	 * lookups.
	 *
	 * @var int
	 */
	private int $post_queries = 0;

	/**
	 * A product of one brand with two files and one answer, the shape the
	 * register reads.
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
			'pll_current_language',
			array(
				'return' => 'en',
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
		WP_Mock::userFunction( 'sanitize_title', array( 'return' => static fn ( string $value ): string => strtolower( str_replace( ' ', '-', $value ) ) ) );
		WP_Mock::userFunction( 'wpautop', array( 'return' => static fn ( string $value ): string => '<p>' . $value . '</p>' ) );
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static function ( string $url, int $component = -1 ) {
					$parsed = -1 === $component ? parse_url( $url ) : parse_url( $url, $component );
					return false === $parsed ? null : $parsed;
				},
			)
		);
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://de-linker.test/genie/' ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => null ) );
		WP_Mock::userFunction( 'plugins_url', array( 'return' => static fn ( string $path ): string => 'https://de-linker.test/wp-content/plugins/linker-commerce/' . $path ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => '0+' ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( array $value ): string => (string) json_encode( $value ) ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => function (): array {
					++$this->post_queries;
					return array( 6521 );
				},
			)
		);
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
		WP_Mock::userFunction(
			'wp_get_attachment_url',
			array( 'return' => static fn ( int $id ): string => 'https://de-linker.test/media/' . $id . '.pdf' )
		);
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
									array(
										'download_file'  => 902,
										'download_title' => 'Family certificate',
										'download_type'  => 'certificate',
										'download_language' => 'MULTI',
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
		// The brand logo's media lookup: the library holds the GoodWe light
		// lockup, and no other brand's.
		WP_Mock::userFunction(
			'wp_get_attachment_image_src',
			array(
				'return' => static fn (): array => array( 'https://de-linker.test/uploads/our-brand-goodwe-mono-light.png', 1480, 288 ),
			)
		);
	}

	/**
	 * The FAQ tab: the trade rules from the page's own data file, then the
	 * products' answers — each as a card with its own count, all open to
	 * search-engine and no-JS readers.
	 */
	public function test_the_faq_tab_prints_the_trade_rules_and_the_answers_without_script(): void {
		$html = ( new LibraryPage( $this->library() ) )->faq();

		$this->assertStringContainsString( 'id="linker-library-zone-trade"', $html );
		$this->assertStringContainsString( 'id="linker-library-trade-0"', $html );
		$this->assertStringContainsString( 'data-library-kind="trade"', $html );
		$this->assertStringContainsString( 'Ordering & delivery', $html );
		$this->assertStringContainsString( 'What is the minimum order quantity, and where does Linker deliver?', $html );
		$this->assertStringContainsString( 'There is no pallet minimum.', $html );
		$this->assertStringContainsString( 'id="linker-library-zone-answers"', $html );
		$this->assertStringContainsString( 'Is the module stackable?', $html );
		$this->assertStringContainsString( 'Yes, up to four modules.', $html );
		$this->assertStringContainsString( '<a href="https://de-linker.test/produkt/goodwe-gw5-1/">GoodWe GW5.1-BAT-D-G21</a>', $html );
		$this->assertStringContainsString( 'ESA battery manual, p. 12', $html );
		$this->assertStringContainsString( 'href="https://de-linker.test/media/901.pdf#page=12"', $html );
		$this->assertStringContainsString( 'data-library-card-count', $html );
		$this->assertStringContainsString( 'data-library-group="GoodWe"', $html );
		$this->assertStringContainsString( 'linker-library-qa-where', $html );
		$this->assertStringNotContainsString( '<script', $html );
		$this->assertStringNotContainsString( ' style="', $html );
	}

	/**
	 * The documents tab: the type chips with their counts, one card per brand,
	 * and one row per file carrying its type, title, coverage, language and
	 * download.
	 */
	public function test_the_documents_tab_prints_the_register_with_its_chips(): void {
		$html = ( new LibraryPage( $this->library() ) )->documents();

		$this->assertStringContainsString( 'data-library-filters', $html );
		$this->assertStringContainsString( 'aria-label="Document type"', $html );
		$this->assertStringContainsString( 'data-library-type="datasheet" aria-pressed="false"', $html );
		$this->assertStringContainsString( 'Datasheet', $html );
		$this->assertStringContainsString( 'Certificate', $html );
		$this->assertStringContainsString( 'id="linker-library-zone-documents"', $html );
		$this->assertStringContainsString( 'id="linker-library-docs-goodwe"', $html );
		$this->assertStringContainsString( 'linker-library-doc-list', $html );
		$this->assertStringContainsString( 'data-library-item data-library-type="datasheet"', $html );
		$this->assertStringContainsString( 'ESA battery datasheet (EN)', $html );
		$this->assertStringContainsString( 'covers GoodWe GW5.1-BAT-D-G21', $html );
		$this->assertStringContainsString( 'href="https://de-linker.test/media/900.pdf"', $html );
		$this->assertStringContainsString( 'Download', $html );
		$this->assertStringContainsString( 'linker-library-lang', $html );
		$this->assertStringNotContainsString( '<script', $html );
	}

	/**
	 * A row with no shipped thumbnail keeps the type tile the design shows in
	 * its place — the build's own gap, printed rather than left blank.
	 */
	public function test_a_document_without_a_thumbnail_keeps_its_type_tile(): void {
		$html = ( new LibraryPage( $this->library() ) )->documents();

		$this->assertStringContainsString( 'linker-library-thumb is-type is-datasheet', $html );
		$this->assertStringNotContainsString( 'has-src', $html );
		$this->assertStringNotContainsString( '<img src="https://de-linker.test/wp-content/plugins/linker-commerce/assets/faq-thumbs/', $html );
	}

	/**
	 * The rail and the chip row: both tabs' groups, each link naming the card
	 * it jumps to with the count that card starts on.
	 */
	public function test_the_rail_and_the_chips_link_both_tabs_cards(): void {
		$page  = new LibraryPage( $this->library() );
		$rail  = $page->rail();
		$chips = $page->chips();

		$this->assertStringContainsString( 'data-library-nav="faq"', $rail );
		$this->assertStringContainsString( 'data-library-nav="documents"', $rail );
		$this->assertStringContainsString( 'href="#linker-library-trade-0"', $rail );
		$this->assertStringContainsString( 'href="#linker-library-answers-goodwe"', $rail );
		$this->assertStringContainsString( 'href="#linker-library-docs-goodwe"', $rail );
		$this->assertStringContainsString( 'data-library-zone="linker-library-zone-trade"', $rail );
		$this->assertStringContainsString( 'data-library-nav="faq"', $chips );
		$this->assertStringContainsString( 'data-library-nav="documents"', $chips );
		$this->assertStringContainsString( 'linker-library-chip-gap', $chips );
		$this->assertStringContainsString( '<span class="linker-library-n">2</span>', $rail, 'the card link carries its row count' );
	}

	/**
	 * The counts the template and the search field print: FAQ and documents
	 * apart for the tabs, their sum for the field.
	 */
	public function test_the_counts_state_each_tab_and_the_whole_file(): void {
		$page = new LibraryPage( $this->library() );

		$this->assertSame( '17', $page->count( array( 'of' => 'faq' ) ), 'the trade rules and the product answers' );
		$this->assertSame( '17', $page->count(), 'the tab that opens first' );
		$this->assertSame( '2', $page->count( array( 'of' => 'documents' ) ) );
		$this->assertSame( '19 on file', $page->total() );
	}

	/**
	 * The interaction layer's config: the page size, the Genie URL in the
	 * page's language, and every word the script prints — translated
	 * server-side, so the script carries none of them itself.
	 */
	public function test_the_config_carries_the_labels_the_script_prints(): void {
		$html = ( new LibraryPage( $this->library() ) )->config();

		$this->assertStringContainsString( 'id="linker-library-config"', $html );
		$this->assertStringContainsString( '"pageSize":20', $html );
		$this->assertStringContainsString( '"genieUrl":"https:\/\/de-linker.test\/genie\/"', $html );
		$this->assertStringContainsString( '"empty":"Nothing on file matches that search."', $html );
		$this->assertStringContainsString( '"pages":"Pages"', $html );
	}

	/**
	 * The fragments share one reading of the register: a second shortcode call
	 * on the same request does not re-read the products.
	 */
	public function test_the_page_reads_the_register_once(): void {
		$page = new LibraryPage( $this->library() );
		$page->faq();
		$page->documents();
		$page->rail();
		$page->chips();
		$page->count();
		$page->count( array( 'of' => 'documents' ) );
		$page->total();

		// The model's own readings: the register's documents, the products'
		// answers, and one brand-logo lookup. Every fragment after them reads
		// the same model, so the counts and the rows cannot disagree and a
		// template is free to call the fragments in any order.
		$this->assertSame( 3, $this->post_queries );
	}

	/**
	 * The register the fragments describe: one product of one brand.
	 */
	private function library(): DocumentLibrary {
		return new DocumentLibrary();
	}
}
