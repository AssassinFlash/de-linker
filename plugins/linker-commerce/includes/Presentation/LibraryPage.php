<?php
/**
 * The FAQ + document library page (/faq-download/).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Products\ToolkitRegistry;
use Linker\Commerce\Products\TradeRules;

/**
 * Render the bilingual toolkit, published document register and first page
 * of product answers. The library index supplies additional answers and model
 * aliases when a visitor searches or continues to another page.
 */
final class LibraryPage {

	/** English page key; Polylang resolves its translated slug. */
	private const PAGE_SLUG = 'faq-download';

	/**
	 * Rows one page of a card or of the search results shows: the accepted
	 * prototype's page size.
	 */
	public const PAGE_SIZE = 20;

	/** Number of product answers per brand visible in the initial register. */
	public const FAQ_SSR_PAGE_SIZE = 3;

	/**
	 * Every anchor the page prints starts with this.
	 */
	private const ID_PREFIX = 'linker-library-';

	/**
	 * The zone anchors the rail, the chips and the panels share.
	 */
	private const ZONE_TRADE     = 'linker-library-zone-trade';
	private const ZONE_ANSWERS   = 'linker-library-zone-answers';
	private const ZONE_DOCUMENTS = 'linker-library-zone-documents';

	/**
	 * The filter chips' type order: the design's own order (the accepted
	 * prototype's chip row). The rows inside a card follow
	 * DocumentLibrary::TYPE_ORDER.
	 */
	private const CHIP_ORDER = array( 'datasheet', 'manual', 'warranty', 'certificate', 'compatibility', 'brochure', 'document' );

	/**
	 * The brand logo's height: the design's lockup.
	 */
	private const LOGO_HEIGHT = 34;

	/**
	 * Characters the initials fallback shows.
	 */
	private const MARK_LENGTH = 2;

	/**
	 * The register the fragments list.
	 *
	 * @var DocumentLibrary
	 */
	private readonly DocumentLibrary $library;

	/**
	 * The page's own trade rules.
	 *
	 * @var TradeRules
	 */
	private readonly TradeRules $rules;

	/**
	 * The page's model, assembled once per request.
	 *
	 * @var array{
	 *   trade: list<array{id: string, name: string, count: int, questions: list<array{question: string, answer: string}>}>,
	 *   brands: list<array{name: string, logo: array{src:string,srcset:string,sizes:string,width:int,height:int}|null, mark: string, answers_id: string, documents_id: string, answers: list<array{question: string, answer: string, product: string, url: string, source: string, source_url: string}>|null, documents: list<array{title: string, url: string, type: string, type_label: string, language: string, product_links:list<array{title:string,url:string}>}>|null}>,
	 *   types: list<array{type: string, label: string, count: int}>,
	 *   faq_total: int,
	 *   document_total: int
	 * }|null
	 */
	private ?array $model = null;

	/**
	 * Sets up the page.
	 *
	 * @param DocumentLibrary|null $library Register override (tests).
	 * @param TradeRules|null      $rules   Trade-rule data override (tests).
	 */
	public function __construct(
		?DocumentLibrary $library = null,
		?TradeRules $rules = null
	) {
		$this->library = $library ?? new DocumentLibrary();
		$this->rules   = $rules ?? new TradeRules();
	}

	/**
	 * Adds the fragments' shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_library_toolkit', array( $this, 'toolkit' ) );
		add_action( 'rest_api_init', array( LibraryIndexEndpoint::class, 'register' ) );
		add_shortcode( 'linker_library_count', array( $this, 'count' ) );
		add_shortcode( 'linker_library_total', array( $this, 'total' ) );
		add_shortcode( 'linker_library_rail', array( $this, 'rail' ) );
		add_shortcode( 'linker_library_chips', array( $this, 'chips' ) );
		add_shortcode( 'linker_library_faq', array( $this, 'faq' ) );
		add_shortcode( 'linker_library_documents', array( $this, 'documents' ) );
		add_shortcode( 'linker_library_config', array( $this, 'config' ) );
		add_action( 'wp_head', array( $this, 'print_schema' ) );
	}

	/**
	 * Keep this library's finite display state in native language links.
	 *
	 * Search text already belongs to LanguageLinks' shared query contract.
	 * Native page twins identify the library even when LiveCanvas renders
	 * its shortcodes from an assigned template instead of the page body.
	 *
	 * @param array<string,mixed> $query Public, unslashed request query.
	 * @return array<string,string>
	 */
	public static function language_query( array $query ): array {
		$kept = array();
		if ( 'documents' === ( $query['tab'] ?? null ) ) {
			$kept['tab'] = 'documents';
		}
		if ( 'faq' === ( $query['tab'] ?? null ) ) {
			$kept['tab'] = 'faq';
		}
		if ( isset( $query['brand'] ) && is_string( $query['brand'] ) && preg_match( '/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $query['brand'] ) && 'all' !== $query['brand'] ) {
			$kept['brand'] = $query['brand'];
		}
		$type = $query['type'] ?? null;
		if ( is_string( $type ) && in_array( $type, self::CHIP_ORDER, true ) ) {
			$kept['type'] = $type;
		}
		if ( array() === $kept ) {
			return array();
		}
		$page = get_queried_object();
		if ( ! $page instanceof \WP_Post || 'page' !== $page->post_type ) {
			return array();
		}
		if ( self::is_library_page( $page ) ) {
			return $kept;
		}
		return array();
	}

	/**
	 * Whether a page belongs to this library: the English page itself or a
	 * page whose English translation is it (the German twin keeps the slug of
	 * whatever it was given, so the source is the certain answer).
	 *
	 * @param \WP_Post $page A page.
	 */
	private static function is_library_page( \WP_Post $page ): bool {
		if ( self::PAGE_SLUG === $page->post_name ) {
			return true;
		}
		$source_id = function_exists( 'pll_get_post' ) ? (int) pll_get_post( (int) $page->ID, 'en' ) : 0;
		$source    = $source_id > 0 ? get_post( $source_id ) : null;
		return $source instanceof \WP_Post && self::PAGE_SLUG === $source->post_name;
	}

	/**
	 * A tab's entry count, as the tab bar prints it. `of` is `faq` or
	 * `documents`; anything else is the FAQ tab, the one that opens.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes: `of`.
	 */
	public function count( $atts = array() ): string {
		$atts  = is_array( $atts ) ? $atts : array();
		$of    = is_string( $atts['of'] ?? null ) ? $atts['of'] : 'faq';
		$model = $this->model();

		return (string) ( 'documents' === $of ? $model['document_total'] : $model['faq_total'] );
	}

	/**
	 * The search field's initial text: how much is on file. The script keeps
	 * the same field updated while a search runs.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function total( $atts = array() ): string {
		unset( $atts );
		$model = $this->model();

		return esc_html(
			sprintf(
				/* translators: %d: number of questions and documents on file. */
				__( '%d on file', 'linker-commerce' ),
				$model['faq_total'] + $model['document_total']
			)
		);
	}

	/**
	 * The rail: one group per tab, each ending in the brands of its own panel.
	 * Both groups are printed; the script hides the one the active tab does
	 * not show, and without the script the rail is the page's full table of
	 * contents.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function rail( $atts = array() ): string {
		unset( $atts );
		$model = $this->model();
		$trade = (string) __( 'Before your inquiry', 'linker-commerce' );
		$faq   = (string) __( 'Product answers', 'linker-commerce' );
		$docs  = (string) __( 'Brands', 'linker-commerce' );

		$links = '';
		foreach ( $model['trade'] as $category ) {
			$links .= '<a href="#' . esc_attr( $category['id'] ) . '" data-library-spy-link>' . esc_html( $category['name'] ) . ' <span class="linker-library-n">' . esc_html( (string) $category['count'] ) . '</span></a>';
		}
		$brand_links = '';
		foreach ( $model['brands'] as $brand ) {
			if ( empty( $brand['answers'] ) ) {
				continue;
			}
			$brand_links .= '<a href="#' . esc_attr( $brand['answers_id'] ) . '" data-library-spy-link>' . esc_html( $brand['name'] ) . ' <span class="linker-library-n">' . esc_html( (string) count( $brand['answers'] ) ) . '</span></a>';
		}
		$document_links = '';
		foreach ( $model['brands'] as $brand ) {
			if ( empty( $brand['documents'] ) ) {
				continue;
			}
			$document_links .= '<a href="#' . esc_attr( $brand['documents_id'] ) . '" data-library-spy-link>' . esc_html( $brand['name'] ) . ' <span class="linker-library-n">' . esc_html( (string) count( $brand['documents'] ) ) . '</span></a>';
		}

		$out  = '<div class="linker-library-rail-group" data-library-nav="faq">';
		$out .= '<p class="linker-library-rail-label"><a href="#' . esc_attr( self::ZONE_TRADE ) . '" data-library-spy-link data-library-zone="' . esc_attr( self::ZONE_TRADE ) . '">' . esc_html( $trade ) . '</a></p>';
		$out .= '<nav class="linker-library-toc" aria-label="' . esc_attr( $trade ) . '">' . $links . '</nav>';
		$out .= '<p class="linker-library-rail-label"><a href="#' . esc_attr( self::ZONE_ANSWERS ) . '" data-library-spy-link data-library-zone="' . esc_attr( self::ZONE_ANSWERS ) . '">' . esc_html( $faq ) . '</a></p>';
		$out .= '<nav class="linker-library-toc" aria-label="' . esc_attr( $faq ) . '">' . $brand_links . '</nav>';
		$out .= '</div>';
		$out .= '<div class="linker-library-rail-group" data-library-nav="documents">';
		$out .= '<p class="linker-library-rail-label"><a href="#' . esc_attr( self::ZONE_DOCUMENTS ) . '" data-library-spy-link data-library-zone="' . esc_attr( self::ZONE_DOCUMENTS ) . '">' . esc_html( $docs ) . '</a></p>';
		$out .= '<nav class="linker-library-toc" aria-label="' . esc_attr( $docs ) . '">' . $document_links . '</nav>';
		$out .= '</div>';

		return $out;
	}

	/**
	 * The narrow viewports' chip row: the rail's own links, one group per tab.
	 * The chips scroll sideways and stay pinned under the tab bar.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function chips( $atts = array() ): string {
		unset( $atts );
		$model       = $this->model();
		$trade       = (string) __( 'Before your inquiry', 'linker-commerce' );
		$faq         = (string) __( 'Product answers', 'linker-commerce' );
		$trade_chips = '';
		foreach ( $model['trade'] as $category ) {
			$trade_chips .= $this->chip( $category['id'], $category['name'], $category['count'] );
		}
		$answer_chips = '';
		foreach ( $model['brands'] as $brand ) {
			if ( empty( $brand['answers'] ) ) {
				continue;
			}
			$answer_chips .= $this->chip( $brand['answers_id'], $brand['name'], count( $brand['answers'] ) );
		}
		$document_chips = '';
		foreach ( $model['brands'] as $brand ) {
			if ( empty( $brand['documents'] ) ) {
				continue;
			}
			$document_chips .= $this->chip( $brand['documents_id'], $brand['name'], count( $brand['documents'] ) );
		}

		$out  = '<div class="linker-library-chips-scroll" data-library-nav="faq">';
		$out .= $this->chip( self::ZONE_TRADE, $trade, null, self::ZONE_TRADE ) . $trade_chips;
		$out .= '<span class="linker-library-chip-gap" aria-hidden="true"></span>';
		$out .= $this->chip( self::ZONE_ANSWERS, $faq, null, self::ZONE_ANSWERS ) . $answer_chips;
		$out .= '</div>';
		$out .= '<div class="linker-library-chips-scroll" data-library-nav="documents">' . $document_chips . '</div>';

		return $out;
	}

	/**
	 * The FAQ tab: the trade rules, then the products' answers, one card per
	 * category and per brand.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function faq( $atts = array() ): string {
		unset( $atts );
		$model = $this->model();

		$cards = '';
		foreach ( $model['trade'] as $category ) {
			$rows = '';
			foreach ( $category['questions'] as $question ) {
				$rows  .= '<details class="linker-library-qa" data-library-item>';
				$rows  .= '<summary class="linker-library-qa-head">';
				$rows  .= '<span class="linker-library-qa-q">' . esc_html( $question['question'] ) . '</span>';
				$rows  .= '</summary>';
				$answer = $question['answer'];
				if ( str_contains( $answer, '?intent=support"' ) ) {
					$answer = str_replace( '?intent=support"', '?intent=support&amp;source=' . rawurlencode( (string) get_permalink() ) . '"', $answer );
				}
				$rows .= '<div class="linker-library-qa-a"><p>' . wp_kses_post( $answer ) . '</p></div>';
				$rows .= '</details>';
			}
			$cards .= $this->card( $category['id'], 'trade', $category['name'], $category['count'], null, $rows, '' );
		}
		$out = $this->zone( self::ZONE_TRADE, (string) __( 'Before your inquiry', 'linker-commerce' ), $cards );

		$cards = '';
		foreach ( $model['brands'] as $brand ) {
			if ( empty( $brand['answers'] ) ) {
				continue;
			}
			$answers = $brand['answers'];
			$rows    = '';
			foreach ( array_slice( $answers, 0, self::FAQ_SSR_PAGE_SIZE ) as $answer ) {
				$rows .= '<details class="linker-library-qa" data-library-item>';
				$rows .= '<summary class="linker-library-qa-head">';
				$rows .= '<span class="linker-library-qa-product">' . esc_html( $answer['product'] ) . '</span>';
				$rows .= '<span class="linker-library-qa-q">' . esc_html( $answer['question'] ) . '</span>';
				$rows .= '</summary>';
				$rows .= '<div class="linker-library-qa-a"><p>' . wp_kses_post( $answer['answer'] ) . '</p>';
				$rows .= '<p class="linker-library-qa-source"><a href="' . esc_url( self::local_href( $answer['url'] ) ) . '">' . esc_html( $answer['product'] ) . '</a>';
				if ( '' !== $answer['source'] ) {
					$rows .= ' — <a data-doc-kind="document" data-doc-brand="' . esc_attr( $brand['name'] ) . '" href="' . esc_url( self::local_href( $answer['source_url'] ) ) . '">' . esc_html( $answer['source'] ) . '</a>';
				}
				$rows .= '</p></div></details>';
			}
			$cards .= $this->card( $brand['answers_id'], 'answer', $brand['name'], count( $answers ), $brand['logo'], $rows, $brand['mark'] );
		}
		$out .= $this->zone( self::ZONE_ANSWERS, (string) __( 'Product answers', 'linker-commerce' ), $cards );

		return $out;
	}

	/**
	 * The document filters and register, grouped by manufacturer.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function documents( $atts = array() ): string {
		unset( $atts );
		$model = $this->model();
		$out   = '<div class="linker-library-filters" data-library-filters><fieldset data-library-brand-filters><legend>' . esc_html__( 'Filter by brand', 'linker-commerce' ) . '</legend>';
		$out  .= $this->filter_button( 'brand', 'all', __( 'All brands', 'linker-commerce' ), $model['document_total'] );
		foreach ( $model['brands'] as $brand ) {
			if ( ! empty( $brand['documents'] ) ) {
				$out .= $this->filter_button( 'brand', sanitize_title( $brand['name'] ), $brand['name'], count( $brand['documents'] ) );
			}
		}
		$out .= '</fieldset><fieldset data-library-type-filters><legend>' . esc_html__( 'Document type', 'linker-commerce' ) . '</legend>';
		$out .= $this->filter_button( 'type', 'all', __( 'All', 'linker-commerce' ), $model['document_total'] );
		foreach ( $model['types'] as $type ) {
			$label = 'certificate' === $type['type'] ? __( 'Grid Certificate (VDE · ZEREZ)', 'linker-commerce' ) : $type['label'];
			$out  .= $this->filter_button( 'type', $type['type'], $label, $type['count'] );
		}
		$out .= '</fieldset></div>';

		$cards = '';
		foreach ( $model['brands'] as $brand ) {
			if ( empty( $brand['documents'] ) ) {
				continue;
			}
			$documents = $brand['documents'];
			$rows      = '';
			foreach ( $documents as $document ) {
				$rows .= $this->document( $document );
			}
			$cards .= $this->card( $brand['documents_id'], 'document', $brand['name'], count( $documents ), $brand['logo'], $rows, $brand['mark'] );
		}
		$out .= $this->zone( self::ZONE_DOCUMENTS, (string) __( 'Manufacturer Certifications & Technical Document Library', 'linker-commerce' ), $cards );

		return $out;
	}

	/**
	 * The interaction layer: the script, and the labels it gives the parts it
	 * renders itself (the counts, the search's empty state, the pager). The
	 * page's own words are in the template; these are the fragments' words,
	 * the same way `Download` and the type names are.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function config( $atts = array() ): string {
		unset( $atts );
		$path = dirname( __DIR__, 2 ) . '/assets/library-ui.js';
		wp_enqueue_script(
			'linker-library-ui',
			plugins_url( 'assets/library-ui.js', dirname( __DIR__, 2 ) . '/linker-commerce.php' ),
			array(),
			substr( (string) md5_file( $path ), 0, 12 ),
			array(
				'strategy'  => 'defer',
				'in_footer' => true,
			)
		);
		$config = array(
			'pageSize'    => self::PAGE_SIZE,
			'faqPageSize' => self::FAQ_SSR_PAGE_SIZE,
			'indexUrl'    => add_query_arg( 'lang', $this->german() ? 'de' : 'en', rest_url( 'linker/v1/library-index' ) ),
			'genieUrl'    => $this->genie_url(),
			'i18n'        => array(
				/* translators: %d: number of matching entries. */
				'resultsOne'    => __( '%d result', 'linker-commerce' ),
				/* translators: %d: number of matching entries. */
				'resultsOther'  => __( '%d results', 'linker-commerce' ),
				'inAnswer'      => __( 'In the answer', 'linker-commerce' ),
				/* translators: %d: number of questions and documents on file. */
				'onFile'        => __( '%d on file', 'linker-commerce' ),
				'empty'         => __( 'Nothing on file matches that search.', 'linker-commerce' ),
				'indexError'    => __( 'The full index could not be loaded. Please try again.', 'linker-commerce' ),
				'emptySoft'     => __( 'No documents of this type.', 'linker-commerce' ),
				'askGenie'      => __( 'Ask Genie', 'linker-commerce' ),
				'trade'         => __( 'Trade rule', 'linker-commerce' ),
				'answer'        => __( 'Answer', 'linker-commerce' ),
				'document'      => __( 'Document', 'linker-commerce' ),
				'previous'      => __( 'Previous', 'linker-commerce' ),
				'next'          => __( 'Next', 'linker-commerce' ),
				'pages'         => __( 'Pages', 'linker-commerce' ),
				'questions'     => __( 'Questions', 'linker-commerce' ),
				'documents'     => __( 'Documents', 'linker-commerce' ),
				/* translators: %s: product name. */
				'coversProduct' => __( 'covers %s', 'linker-commerce' ),
			),
		);

		return '<script type="application/json" id="linker-library-config">' . (string) wp_json_encode( $config ) . '</script>';
	}

	/**
	 * One zone: its heading, its stack of cards, and the zone it belongs to —
	 * the rail and the chip row mark the link of the zone the reader is in, and
	 * every spy target states its own rather than having it guessed from an id.
	 *
	 * @param string $id    Anchor id (the zone's own).
	 * @param string $title Zone title.
	 * @param string $cards The cards.
	 */
	private function zone( string $id, string $title, string $cards ): string {
		return '<section class="linker-library-zone" id="' . esc_attr( $id ) . '" data-library-spy data-library-zone="' . esc_attr( $id ) . '">' .
			'<h2 class="linker-library-zone-title">' . esc_html( $title ) . '</h2>' .
			'<div class="linker-library-stack">' . $cards . '</div></section>';
	}

	/**
	 * One card: its heading (the brand's logo or initials, its name, the row
	 * count the search and the type chips update), its zone, and the rows
	 * themselves.
	 *
	 * @param string                                                                 $id    Anchor id.
	 * @param string                                                                 $kind  `trade`, `answer` or `document`.
	 * @param string                                                                 $title Card title.
	 * @param int                                                                    $count Row count as printed now.
	 * @param array{src:string,srcset:string,sizes:string,width:int,height:int}|null $logo Brand image.
	 * @param string                                                                 $rows  The rows.
	 * @param string                                                                 $mark  Initials the logo falls back to, '' for no mark.
	 */
	private function card( string $id, string $kind, string $title, int $count, ?array $logo, string $rows, string $mark ): string {
		$head = '<header class="linker-library-card-head">';
		if ( null !== $logo ) {
			$head .= '<span class="linker-library-logo"><img src="' . esc_url( $logo['src'] ) . '" srcset="' . esc_attr( $logo['srcset'] ) . '" sizes="' . esc_attr( $logo['sizes'] ) . '" width="' . (int) $logo['width'] . '" height="' . (int) $logo['height'] . '" alt="' . esc_attr( $title ) . '" loading="lazy" decoding="async"></span>';
		} elseif ( '' !== $mark ) {
			$head .= '<span class="linker-library-mark" aria-hidden="true">' . esc_html( $mark ) . '</span>';
		}
		$head .= '<h3 class="linker-library-card-title">' . esc_html( $title ) . '</h3>';
		$head .= '<span class="linker-library-n" data-library-card-count>' . esc_html( (string) $count ) . '</span></header>';

		$list = 'document' === $kind ? '<ul class="linker-library-doc-list">' . $rows . '</ul>' : $rows;

		$zone = match ( $kind ) {
			'document' => self::ZONE_DOCUMENTS,
			'trade'    => self::ZONE_TRADE,
			default    => self::ZONE_ANSWERS,
		};

		return '<article class="linker-library-card" id="' . esc_attr( $id ) . '" data-library-card data-library-kind="' . esc_attr( $kind ) . '" data-library-total="' . $count . '" data-library-spy data-library-zone="' . esc_attr( $zone ) . '">' . $head .
			'<div class="linker-library-rows">' . $list . '</div></article>';
	}

	/**
	 * Preserve external media hosts while shortening first-party links.
	 *
	 * @param string $url Published canonical URL.
	 */
	private static function local_href( string $url ): string {
		$root = PageUrls::root();
		return str_starts_with( $url, $root ) ? '/' . substr( $url, strlen( $root ) ) : $url;
	}

	/** The four bilingual planning references. */
	public function toolkit(): string {
		$cards = ToolkitRegistry::cards_for_locale( $this->german() ? 'de' : 'en' );
		$html  = '<section class="lk-toolkit-band linker-library-wrap" id="linker-engineering-toolkit" aria-labelledby="lk-toolkit-title">';
		$html .= '<div class="lk-toolkit-intro"><p class="lk-toolkit-eyebrow">' . esc_html__( 'Linker Engineering Toolkit', 'linker-commerce' ) . '</p>';
		$html .= '<h2 id="lk-toolkit-title">' . esc_html__( 'Direct engineering references — no form required', 'linker-commerce' ) . '</h2></div>';
		$html .= '<div class="lk-toolkit-grid">';
		foreach ( $cards as $card ) {
			$pdf    = 'pdf' === $card['format'];
			$format = strtoupper( $card['format'] );
			$link   = $pdf ? ' target="_blank" rel="noopener noreferrer"' : ' download';
			$units  = $pdf
				? sprintf( /* translators: %d: number of pages in the PDF. */ __( '%d pages', 'linker-commerce' ), $card['unit_count'] )
				: sprintf( /* translators: %d: number of measurement intervals. */ __( '%d intervals', 'linker-commerce' ), $card['unit_count'] );
			$html  .= '<article class="lk-toolkit-card"><div class="lk-file-meta"><span class="lk-file-symbol" data-suite="' . esc_attr( $card['suite'] ) . '" aria-hidden="true"></span>';
			$html  .= '<span>' . esc_html( $format . ' · ' . $units ) . '</span></div><h3>' . esc_html( $card['title'] ) . '</h3><p>' . esc_html( $card['description'] ) . '</p>';
			$html  .= '<div class="lk-file-revision"><span>Rev. ' . esc_html( $card['revision'] ) . '</span><span>' . esc_html( $card['doc_code'] ) . '</span></div>';
			$html  .= '<div class="lk-file-links"><a class="lk-toolkit-cta" href="' . esc_url( $card['url'] ) . '"' . $link . '>' . esc_html( $pdf ? __( 'Download PDF', 'linker-commerce' ) : __( 'Download CSV', 'linker-commerce' ) ) . '</a>';
			$html  .= '<a href="' . esc_url( $card['alt_url'] ) . '" hreflang="' . esc_attr( $card['alt_lang'] ) . '"' . $link . '>' . esc_html( strtoupper( $card['alt_lang'] ) . ' ' . $format ) . ' ↗</a></div></article>';
		}
		return $html . '</div><p class="lk-toolkit-note">' . esc_html__( 'Technical parameters verified as of 2026-11. Net project pricing, availability, and delivery terms apply per formal written quotation.', 'linker-commerce' ) . '</p></section>';
	}

	/**
	 * A facet button and its current result count.
	 *
	 * @param string $facet Brand or type.
	 * @param string $value Filter value.
	 * @param string $label Filter label.
	 * @param int    $count Document count.
	 */
	private function filter_button( string $facet, string $value, string $label, int $count ): string {
		return '<button type="button" class="linker-library-chip" data-library-' . $facet . '="' . esc_attr( $value ) . '" aria-pressed="' . ( 'all' === $value ? 'true' : 'false' ) . '">' . esc_html( $label ) . ' <span class="linker-library-n">' . $count . '</span></button>';
	}

	/**
	 * One file link and its primary published product. The brand is shared by the containing list.
	 *
	 * @param array<string,mixed> $document Document row.
	 */
	private function document( array $document ): string {
		$products = $document['product_links'];
		$first    = $products[0];
		$pdf      = self::local_href( $document['url'] );
		$out      = '<li data-t=' . esc_attr( $document['type'] ) . '><a href="' . esc_url( $pdf ) . '" target=_blank>' . esc_html( $document['title'] ) . '</a>';
		$out     .= '<i>' . esc_html( $document['type_label'] ) . ' · ' . esc_html( $document['language'] ) . '</i>';
		$out     .= '<a href="' . esc_url( self::local_href( $first['url'] ) ) . '">' . esc_html( $first['title'] ) . '</a>';
		return $out . ( count( $products ) > 1 ? ' (+' . ( count( $products ) - 1 ) . ')' : '' );
	}

	/**
	 * One chip of a chip row. A chip that points at a zone states that zone, so
	 * the spy can mark it whenever the reader stands anywhere inside it; a chip
	 * that points at a card carries the card's count instead.
	 *
	 * @param string      $id    Anchor id.
	 * @param string      $label Visible words.
	 * @param int|null    $count Count, null for a zone link.
	 * @param string|bool $zone  The zone a zone link belongs to; false for a
	 *                           card link.
	 */
	private function chip( string $id, string $label, ?int $count, string|bool $zone = false ): string {
		$out = '<a class="linker-library-chip" href="#' . esc_attr( $id ) . '" data-library-spy-link';
		if ( is_string( $zone ) ) {
			$out .= ' data-library-zone="' . esc_attr( $zone ) . '"';
		}
		$out .= '>' . esc_html( $label );
		if ( null !== $count ) {
			$out .= ' <span class="linker-library-n">' . esc_html( (string) $count ) . '</span>';
		}

		return $out . '</a>';
	}

	/**
	 * A document's type display name.
	 *
	 * @param string $type Stored type key.
	 */
	private static function type_label( string $type ): string {
		$labels = array(
			'datasheet'     => __( 'Datasheet', 'linker-commerce' ),
			'manual'        => __( 'Manual', 'linker-commerce' ),
			'certificate'   => __( 'Certificate', 'linker-commerce' ),
			'compatibility' => __( 'Compatibility', 'linker-commerce' ),
			'warranty'      => __( 'Warranty', 'linker-commerce' ),
			'brochure'      => __( 'Brochure', 'linker-commerce' ),
			'document'      => __( 'Document', 'linker-commerce' ),
		);

		return $labels[ $type ] ?? $labels['document'];
	}

	/**
	 * Whether the request is the German page.
	 */
	private function german(): bool {
		return function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
	}

	/**
	 * The Genie page in the page's language, the language's home when the
	 * page does not exist.
	 */
	private function genie_url(): string {
		return PageUrls::page( 'genie' );
	}

	/**
	 * The brand's light logo from the media library, the reading the product
	 * page's own lockup uses (`our-brand-<slug>-mono-light`); null when the
	 * library holds none, and the card then shows its initials.
	 *
	 * @param string $brand Brand name.
	 * @return array{src:string,srcset:string,sizes:string,width:int,height:int}|null
	 */
	private function logo( string $brand ): ?array {
		return BrandLogo::image( sanitize_title( $brand ), self::LOGO_HEIGHT );
	}

	/** Describe the library, its primary toolkit editions and all server-rendered answers. */
	public function print_schema(): void {
		$page = get_queried_object();
		if ( ! $page instanceof \WP_Post || 'page' !== $page->post_type || ! self::is_library_page( $page ) ) {
			return;
		}
		$model  = $this->model();
		$entity = array();
		foreach ( $model['trade'] as $category ) {
			foreach ( $category['questions'] as $question ) {
				$entity[] = $this->question( $question['question'], $question['answer'] );
			}
		}
		foreach ( $model['brands'] as $brand ) {
			foreach ( array_slice( $brand['answers'] ?? array(), 0, self::FAQ_SSR_PAGE_SIZE ) as $answer ) {
				$entity[] = $this->question( $answer['question'], $this->brand_answer_text( $answer ) );
			}
		}
		$url       = (string) get_permalink( $page->ID );
		$publisher = array( '@id' => PageUrls::root() . '#organization' );
		$dataset   = array(
			'@type'        => 'Dataset',
			'@id'          => $url . '#manufacturer-documents',
			'name'         => __( 'Manufacturer Certifications & Technical Document Library', 'linker-commerce' ),
			'creator'      => $publisher,
			'description'  => sprintf( /* translators: %d: number of manufacturer documents. */ __( '%d manufacturer documents', 'linker-commerce' ), $model['document_total'] ),
			'distribution' => array(
				'@type'          => 'DataDownload',
				'contentUrl'     => PageUrls::root() . 'pdf-sitemap1.xml',
				'encodingFormat' => 'application/xml',
			),
		);
		$catalog   = array(
			'@type'       => 'DataCatalog',
			'@id'         => $url . '#datacatalog',
			'name'        => __( 'Linker Technical Document & Engineering Toolkit Library', 'linker-commerce' ),
			'description' => __( 'Datasheets, VDE grid certificates, compatibility references, and project planning templates for installers and EPCs.', 'linker-commerce' ),
			'url'         => $url,
			'inLanguage'  => $this->german() ? 'de-DE' : 'en',
			'publisher'   => $publisher,
			'isPartOf'    => array( '@id' => $url . '#webpage' ),
			'dataset'     => array( '@id' => $dataset['@id'] ),
			'hasPart'     => array(),
		);
		$assets    = array();
		foreach ( ToolkitRegistry::cards_for_locale( $this->german() ? 'de' : 'en' ) as $card ) {
			$id                   = $card['url'] . '#document';
			$catalog['hasPart'][] = array( '@id' => $id );
			$assets[]             = array(
				'@type'          => 'DigitalDocument',
				'@id'            => $id,
				'name'           => $card['title'],
				'identifier'     => '' !== $card['doc_code'] ? $card['doc_code'] : $card['filename'],
				'url'            => $card['url'],
				'encodingFormat' => $card['mime'],
				'inLanguage'     => $card['content_language'],
				'dateModified'   => $card['lastmod'],
				'publisher'      => $publisher,
			);
		}
		$nodes = array( $catalog, $dataset, ...$assets );
		if ( $entity ) {
			$nodes[] = array(
				'@type'      => 'FAQPage',
				'mainEntity' => $entity,
			);
		}
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON_HEX_TAG escapes script delimiters.
		echo '<script type="application/ld+json">' . wp_json_encode(
			array(
				'@context' => 'https://schema.org',
				'@graph'   => $nodes,
			),
			JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
		) . '</script>';
	}

	/**
	 * The visible text of a brand answer: its answer, product link, and source
	 * link when present. The schema consumes the same words without the links.
	 *
	 * @param array{question: string, answer: string, product: string, url: string, source: string, source_url: string} $answer Brand answer.
	 */
	private function brand_answer_text( array $answer ): string {
		$text = $answer['answer'] . ' ' . $answer['product'];
		if ( '' !== $answer['source'] ) {
			$text .= ' — ' . $answer['source'];
		}
		return $text;
	}

	/**
	 * One FAQPage question node, question and answer as the page prints them.
	 *
	 * @param string $question The question text.
	 * @param string $answer   The visible answer text, with link markup when present.
	 * @return array<string, mixed>
	 */
	private function question( string $question, string $answer ): array {
		return array(
			'@type'          => 'Question',
			'name'           => $this->plain_text( $question ),
			'acceptedAnswer' => array(
				'@type' => 'Answer',
				'text'  => $this->plain_text( $answer ),
			),
		);
	}

	/**
	 * Text the browser shows for an answer that may contain a link. WordPress
	 * strips elements and scripts while keeping the link's visible words; the
	 * entity decode keeps punctuation and names readable in JSON text.
	 *
	 * @param string $html Stored visible text, possibly with links.
	 */
	private function plain_text( string $html ): string {
		$text = html_entity_decode( wp_strip_all_tags( $html ), ENT_QUOTES | ENT_HTML5, 'UTF-8' );
		return trim( (string) preg_replace( '/\s+/u', ' ', $text ) );
	}

	/**
	 * The page's model, assembled once: the trade rules, the answers and the
	 * documents grouped by brand, and the counts over them. Brands keep the
	 * order the answers state them in (the register's own order); a brand with
	 * documents and no answers follows the ones with answers.
	 *
	 * @return array{
	 *   trade: list<array{id: string, name: string, count: int, questions: list<array{question: string, answer: string}>}>,
	 *   brands: list<array{name: string, logo: array{src:string,srcset:string,sizes:string,width:int,height:int}|null, mark: string, answers_id: string, documents_id: string, answers: list<array{question: string, answer: string, product: string, url: string, source: string, source_url: string}>|null, documents: list<array{title: string, url: string, type: string, type_label: string, language: string, product_links:list<array{title:string,url:string}>}>|null}>,
	 *   types: list<array{type: string, label: string, count: int}>,
	 *   faq_total: int,
	 *   document_total: int
	 * }
	 */
	private function model(): array {
		if ( null !== $this->model ) {
			return $this->model;
		}
		$language = $this->german() ? 'de' : 'en';

		$trade = array();
		foreach ( $this->rules->categories( $language ) as $index => $category ) {
			$questions = array();
			foreach ( $category['questions'] as $question ) {
				$questions[] = array(
					'question' => $question['question'],
					'answer'   => $question['answer'],
				);
			}
			$trade[] = array(
				'id'        => self::ID_PREFIX . 'trade-' . $index,
				'name'      => $category['name'],
				'count'     => count( $questions ),
				'questions' => $questions,
			);
		}

		$entries = $this->library->entries( $language );

		/**
		 * The products' answers, filed by the brand of the product that states
		 * them.
		 *
		 * @var array<string, list<array{question: string, answer: string, product: string, url: string, source: string, source_url: string}>> $answers
		 */
		$answers = array();
		foreach ( $entries['answers'] as $answer ) {
			$answers[ $answer['brand'] ][] = array(
				'question'   => $answer['question'],
				'answer'     => $answer['answer'],
				'product'    => $answer['product'],
				'url'        => $answer['url'],
				'source'     => $answer['source'],
				'source_url' => $answer['source_url'],
			);
		}

		/**
		 * The register, filed by brand; one entry per file.
		 *
		 * @var array<string, list<array{title: string, url: string, type: string, type_label: string, language: string, product_links:list<array{title:string,url:string}>}>> $documents
		 */
		$documents = array();
		foreach ( $entries['documents'] as $document ) {
			$type                              = $document['type'];
			$documents[ $document['brand'] ][] = array(
				'title'         => $document['title'],
				'url'           => $document['url'],
				'type'          => $type,
				'type_label'    => self::type_label( $type ),
				'language'      => $document['language'],

				'product_links' => $document['product_links'],
			);
		}

		$names = array_keys( $answers );
		foreach ( array_keys( $documents ) as $brand ) {
			if ( ! in_array( $brand, $names, true ) ) {
				$names[] = $brand;
			}
		}

		$brands         = array();
		$faq_total      = 0;
		$document_total = 0;
		$counts         = array();
		foreach ( $trade as $category ) {
			$faq_total += $category['count'];
		}
		// The trade rules are the page's own; every other count comes from the
		// register below.
		foreach ( $names as $brand ) {
			$rows  = $answers[ $brand ] ?? null;
			$files = $documents[ $brand ] ?? null;
			if ( null !== $rows ) {
				$faq_total += count( $rows );
			}
			if ( null !== $files ) {
				$document_total += count( $files );
				foreach ( $files as $file ) {
					$counts[ $file['type'] ] = ( $counts[ $file['type'] ] ?? 0 ) + 1;
				}
			}
			$brands[] = array(
				'name'         => $brand,
				'logo'         => $this->logo( $brand ),
				'mark'         => strtoupper( substr( $brand, 0, self::MARK_LENGTH ) ),
				'answers_id'   => self::ID_PREFIX . 'answers-' . sanitize_title( $brand ),
				'documents_id' => self::ID_PREFIX . 'docs-' . sanitize_title( $brand ),
				'answers'      => $rows,
				'documents'    => $files,
			);
		}

		$types = array();
		foreach ( self::CHIP_ORDER as $type ) {
			if ( isset( $counts[ $type ] ) ) {
				$types[] = array(
					'type'  => $type,
					'label' => self::type_label( $type ),
					'count' => $counts[ $type ],
				);
			}
		}
		foreach ( $counts as $type => $count ) {
			$known = array();
			foreach ( $types as $row ) {
				$known[] = $row['type'];
			}
			if ( ! in_array( $type, $known, true ) ) {
				$types[] = array(
					'type'  => $type,
					'label' => self::type_label( $type ),
					'count' => $count,
				);
			}
		}

		$this->model = array(
			'trade'          => $trade,
			'brands'         => $brands,
			'types'          => $types,
			'faq_total'      => $faq_total,
			'document_total' => $document_total,
		);

		return $this->model;
	}
}
