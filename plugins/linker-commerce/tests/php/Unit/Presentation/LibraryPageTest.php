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
use Linker\Commerce\Products\TradeRules;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Mock\Functions\Handler;

/**
 * Tests for LibraryPage: the register's rail and chips, the FAQ tab's cards,
 * the documents tab's cards and its type chips, the counts the template
 * prints, and the interaction layer's config — all as the LiveCanvas template
 * prints them, without JavaScript.
 *
 * @covers \Linker\Commerce\Presentation\LibraryPage
 */
final class LibraryPageTest extends TestCase {
	use \Linker\Commerce\Tests\Support\PublishedDocumentView;
	use \Linker\Commerce\Tests\Support\BoundFaqFixture;

	/** One deliberately prepared answer and its cited source. */
	private const FAQ = array(
		array(
			'question' => 'Is the module stackable?',
			'answer'   => 'Yes, up to four modules.',
			'citation' => array(
				'url'   => 'https://de-linker.test/media/901.pdf',
				'page'  => 12,
				'title' => 'ESA battery manual',
			),
		),
	);

	/**
	 * Post queries the fragments ran: the register's readings and the brand
	 * lookups.
	 *
	 * @var int
	 */
	private int $post_queries = 0;

	/**
	 * Whether this product has a published answer.
	 *
	 * @var bool
	 */
	private bool $has_answer = true;

	/**
	 * Fresh publication assemblies used by the page's shared model.
	 *
	 * @var int
	 */
	private int $authority_reads = 0;

	/**
	 * A product of one brand with two files and one answer, the shape the
	 * register reads.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://de-linker.test' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnUsing( static fn( string $url ): string => rtrim( $url, '/' ) . '/' );
		WP_Mock::userFunction( 'rest_url' )->andReturn( 'https://de-linker.test/wp-json/linker/v1/library-index' );
		WP_Mock::userFunction( 'add_query_arg' )->andReturnUsing( static fn( string $key, string $value, string $url ): string => $url . '?' . $key . '=' . $value );
		$this->plain_text();
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' )->byDefault();
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' )->byDefault();
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
		WP_Mock::userFunction( 'pll_get_post' )->andReturn( 0 )->byDefault();
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
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'genie' ),
				'return' => new \WP_Post( (object) array( 'ID' => 60 ) ),
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 60 ),
				'return' => 'https://de-linker.test/genie/',
			)
		);
		WP_Mock::userFunction( 'plugins_url', array( 'return' => static fn ( string $path ): string => 'https://de-linker.test/wp-content/plugins/linker-commerce/' . $path ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => '0+' ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( array $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( string $value ): string => strip_tags( $value ) ) );
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
				'return' => function ( int $id, string $key ): mixed {
					return match ( $key ) {
						'_sku'                => 'DLK-EXAMPLE',
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
						'_linker_faqs' => (string) json_encode( $this->has_answer ? self::FAQ : array() ),
						\Linker\Commerce\Products\Publication\EvidenceBindings::FAQ_META_KEY => self::bound_faqs( self::FAQ, 'fixture-manual', hash( 'sha256', 'fixture manual bytes' ) ),
						default               => '',
					};
				},
			)
		);
		WP_Mock::userFunction( 'wp_get_attachment_image_srcset', array( 'return' => '' ) );
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
		$this->assertStringContainsString( 'Inquiries & delivery', $html );
		$this->assertStringContainsString( 'Can I request a single unit, and where do you deliver?', $html );
		$this->assertStringContainsString( 'You can request a single unit.', $html );
		$this->assertStringContainsString( 'id="linker-library-zone-answers"', $html );
		$this->assertStringNotContainsString( 'our-brand-goodwe-mono-light', $html );
		$this->assertStringContainsString( 'class="linker-library-mark"', $html );
		$this->assertStringContainsString( 'Is the module stackable?', $html );
		$this->assertStringContainsString( 'Yes, up to four modules.', $html );
		$this->assertStringContainsString( '<a href="/produkt/goodwe-gw5-1/">GoodWe GW5.1-BAT-D-G21</a>', $html );
		$this->assertStringContainsString( 'ESA battery manual, p. 12', $html );
		$this->assertStringContainsString( 'href="/media/901.pdf#page=12"', $html );
		$this->assertStringContainsString( 'data-library-card-count', $html );
		$this->assertStringNotContainsString( 'data-library-group=', $html );
		$this->assertStringNotContainsString( 'linker-library-qa-where', $html );
		$this->assertStringNotContainsString( '<script', $html );
		$this->assertStringNotContainsString( ' style="', $html );
	}

	/** Brands remain browsable on each tab that actually has entries. */
	public function test_files_without_answers_have_no_empty_faq_card_or_anchor(): void {
		$this->has_answer = false;
		$page             = new LibraryPage( $this->library() );
		self::assertStringNotContainsString( 'linker-library-answers-goodwe', $page->faq() . $page->rail() . $page->chips() );
		self::assertStringContainsString( 'linker-library-docs-goodwe', $page->documents() );
	}

	/**
	 * The documents tab: the type chips with their counts, one card per brand,
	 * and one row per file carrying its type, title, coverage, language and
	 * download.
	 */
	public function test_the_documents_tab_prints_the_register_with_its_chips(): void {
		$html = ( new LibraryPage( $this->library() ) )->documents();

		$this->assertStringContainsString( 'data-library-filters', $html );
		self::assertStringNotContainsString( '<svg', $html );
		$this->assertStringNotContainsString( 'data-library-skus=', $html );
		$this->assertStringNotContainsString( 'faq-thumbs', $html );
		$this->assertStringContainsString( 'our-brand-goodwe-mono-light', $html );
		$this->assertStringContainsString( 'data-library-brand="goodwe"', $html );
		$this->assertStringContainsString( 'data-library-type="datasheet" aria-pressed="false"', $html );
		$this->assertStringContainsString( 'Grid Certificate (VDE · ZEREZ)', $html );
		$this->assertStringContainsString( '<a href="/media/900.pdf"', $html );
		$this->assertStringContainsString( '<a href="/produkt/goodwe-gw5-1/">GoodWe GW5.1-BAT-D-G21</a>', $html );
	}

	/** Each primary planning file and its counterpart are linked in the static page. */
	public function test_toolkit_links_both_editions_of_every_resource(): void {
		$html = ( new LibraryPage() )->toolkit();
		$this->assertSame( 4, substr_count( $html, 'class="lk-toolkit-card"' ) );
		$this->assertSame( 8, substr_count( $html, 'href="https://de-linker.test/downloads/engineering-toolkit/' ) );
		$this->assertSame( 2, substr_count( $html, ' download>' ) );
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
		$this->assertStringNotContainsString( '"clear"', $html, 'the template owns the clear button\'s label' );
		$this->assertStringContainsString( 'In the answer', $html );
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
		$this->assertSame( 1, $this->authority_reads );
		$this->assertSame( 2, $this->post_queries );
	}

	/** The native switcher retains only this library's supported display state. */
	public function test_language_query_keeps_library_tab_and_type_without_loading_products(): void {
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'post_type'    => 'page',
						'post_name'    => 'faq-download',
						'post_content' => '',
					)
				),
			)
		);

		$this->assertSame(
			array(
				'tab'   => 'documents',
				'brand' => 'goodwe',
				'type'  => 'certificate',
			),
			LibraryPage::language_query(
				array(
					'q'       => 'GW10K-EHA-G20',
					'tab'     => 'documents',
					'type'    => 'certificate',
					'brand'   => 'goodwe',
					'private' => 'discard',
				)
			)
		);
		$this->assertSame( 0, $this->authority_reads );
	}

	/** A translated page can have an empty, template-driven body. */
	public function test_language_query_uses_the_native_page_twin(): void {
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'           => 6863,
						'post_type'    => 'page',
						'post_name'    => 'faq-dokumente',
						'post_content' => '',
					)
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 6863, 'en' ),
				'return' => 932,
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'args'   => array( 932 ),
				'return' => new \WP_Post(
					(object) array(
						'ID'        => 932,
						'post_type' => 'page',
						'post_name' => 'faq-download',
					)
				),
			)
		);

		$this->assertSame(
			array(
				'tab'  => 'documents',
				'type' => 'manual',
			),
			LibraryPage::language_query(
				array(
					'tab'  => 'documents',
					'type' => 'manual',
				)
			)
		);
	}

	/** Defaults, invalid values and array inputs cannot create query state. */
	public function test_language_query_omits_default_and_invalid_display_state(): void {
		$this->assertSame(
			array(),
			LibraryPage::language_query(
				array(
					'tab'  => 'other',
					'type' => 'all',
				)
			)
		);
		$this->assertSame(
			array(),
			LibraryPage::language_query(
				array(
					'tab'  => array( 'documents' ),
					'type' => 'unsupported',
				)
			)
		);
	}

	/** Other pages cannot inherit a library-only tab or filter. */
	public function test_language_query_does_not_add_library_state_to_other_pages(): void {
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'post_type' => 'page',
						'ID'        => 28,
						'post_name' => 'contact',
					)
				),
			)
		);

		$this->assertSame(
			array(),
			LibraryPage::language_query(
				array(
					'tab'  => 'documents',
					'type' => 'manual',
				)
			)
		);
	}

	/**
	 * The English library emits a FAQPage whose questions and answers come
	 * from the same model that renders the visible FAQ rows.
	 */
	public function test_the_library_schema_matches_the_visible_faq(): void {
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'        => 932,
						'post_type' => 'page',
						'post_name' => 'faq-download',
					)
				),
			)
		);

		ob_start();
		( new LibraryPage( $this->library() ) )->print_schema();
		$html = (string) ob_get_clean();

		$this->assertSame( 1, substr_count( $html, 'type="application/ld+json"' ) );
		$this->assertStringContainsString( '"@type":"FAQPage"', $html );
		$this->assertStringContainsString( '"name":"Is the module stackable?"', $html );
		$this->assertStringContainsString( '"text":"Yes, up to four modules. GoodWe GW5.1-BAT-D-G21 — ESA battery manual, p. 12"', $html );
		$this->assertStringContainsString( '"name":"Can I request a single unit, and where do you deliver?"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The German twin follows the English page's Polylang pair and emits the
	 * German FAQPage from the same code path.
	 */
	public function test_the_german_library_twin_also_gets_the_faq_schema(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'        => 6863,
						'post_type' => 'page',
						'post_name' => 'faq-dokumente',
					)
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 6863, 'en' ),
				'return' => 932,
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'args'   => array( 932 ),
				'return' => new \WP_Post(
					(object) array(
						'ID'        => 932,
						'post_type' => 'page',
						'post_name' => 'faq-download',
					)
				),
			)
		);

		ob_start();
		( new LibraryPage( $this->library() ) )->print_schema();
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( '"@type":"FAQPage"', $html );
		$this->assertStringContainsString( '"name":"Is the module stackable?"', $html );
		$this->assertConditionsMet();
	}

	/** An ordinary page cannot inherit the library's FAQPage block. */
	public function test_a_non_library_page_gets_no_faq_schema(): void {
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'        => 28,
						'post_type' => 'page',
						'post_name' => 'contact',
					)
				),
			)
		);

		ob_start();
		( new LibraryPage( $this->library() ) )->print_schema();
		$this->assertSame( '', (string) ob_get_clean() );
		$this->assertSame( 0, $this->authority_reads );
		$this->assertConditionsMet();
	}

	/**
	 * FAQPage follows what the interaction layer leaves visible: the first
	 * 20 rows of each card, in the request's language, and plain answer text.
	 *
	 * @dataProvider visibleLanguages
	 * @param string $language Requested language.
	 * @param string $prefix   Visible question prefix.
	 * @param string $answer   Expected first answer.
	 */
	public function test_faq_schema_uses_each_visible_card_page_and_plain_answer_text( string $language, string $prefix, string $answer ): void {
		$path = (string) tempnam( sys_get_temp_dir(), 'linker-trade-' );
		$qas  = array();
		for ( $number = 1; $number <= 21; ++$number ) {
			$qas[] = array(
				'question' => array(
					'en' => 'Question ' . $number,
					'de' => 'Frage ' . $number,
				),
				'answer'   => array(
					'en' => 'Read <a href="/manual/">the manual</a> for item ' . $number . '.',
					'de' => 'Lesen Sie <a href="/de/handbuch/">das Handbuch</a> für Position ' . $number . '.',
				),
			);
		}
		file_put_contents(
			$path,
			(string) json_encode(
				array(
					'categories' => array(
						array(
							'name' => array(
								'en' => 'Visible card',
								'de' => 'Sichtbare Karte',
							),
							'qas'  => $qas,
						),
					),
				)
			)
		);

		try {
			// The test fixture registers English by default; this function
			// handler is the override point WP_Mock uses for each generated
			// WordPress function.
			Handler::registerHandler( 'pll_current_language', static fn (): string => $language );
			$this->assertSame( $language, pll_current_language() );
			WP_Mock::userFunction(
				'get_queried_object',
				array(
					'return' => new \WP_Post(
						(object) array(
							'ID'        => 932,
							'post_type' => 'page',
							'post_name' => 'faq-download',
						)
					),
				)
			);
			WP_Mock::userFunction( 'get_option' )->andReturn( array() )->byDefault();

			ob_start();
			( new LibraryPage( $this->library(), new TradeRules( $path ) ) )->print_schema();
			$html = (string) ob_get_clean();
			$this->assertSame( 1, preg_match( '#<script type="application/ld\+json">(.*?)</script>#s', $html, $match ) );
			$encoded = $match[1] ?? '';
			$this->assertNotSame( '', $encoded );
			$schema = json_decode( $encoded, true, 512, JSON_THROW_ON_ERROR );
			$this->assertIsArray( $schema );
			$nodes = array_column( $schema['@graph'], null, '@type' );
			$this->assertArrayHasKey( 'DataCatalog', $nodes );
			$this->assertArrayHasKey( 'Dataset', $nodes );
			$this->assertSame( 4, count( $nodes['DataCatalog']['hasPart'] ) );
			$schema    = $nodes['FAQPage'];
			$questions = array_column( $schema['mainEntity'], 'name' );
			$this->assertContains( $prefix . '1', $questions );
			$this->assertContains( $prefix . '20', $questions );
			$this->assertContains( $prefix . '21', $questions );
			$this->assertSame( $answer, $schema['mainEntity'][0]['acceptedAnswer']['text'] );
			$this->assertStringNotContainsString( '<a ', $schema['mainEntity'][0]['acceptedAnswer']['text'] );
			$this->assertSame(
				21,
				count(
					array_filter(
						$questions,
						static fn ( string $question ): bool => str_starts_with( $question, 'Question ' ) || str_starts_with( $question, 'Frage ' )
					)
				)
			);
		} finally {
			unlink( $path );
		}
		$this->assertConditionsMet();
	}

	/**
	 * Both language faces use the same visible-card projection.
	 *
	 * @return array<string, array{string, string, string}>
	 */
	public function visibleLanguages(): array {
		return array(
			'English' => array( 'en', 'Question ', 'Read the manual for item 1.' ),
			'German'  => array( 'de', 'Frage ', 'Lesen Sie das Handbuch für Position 1.' ),
		);
	}

	/**
	 * The register the fragments describe: one product of one brand.
	 */
	private function library(): DocumentLibrary {
		return new DocumentLibrary(
			$this->published_document_view(),
			function (): array {
				++$this->authority_reads;
				return array(
					'products'  => array(
						array(
							'product_id'           => 6521,
							'published_locale_ids' => array( 6521 ),
						),
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
		);
	}
}
