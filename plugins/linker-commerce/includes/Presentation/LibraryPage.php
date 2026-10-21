<?php
/**
 * The FAQ + document library page (/faq-download/).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Products\DocumentThumbnails;
use Linker\Commerce\Products\TradeRules;

/**
 * The page's data fragments: the register's rail, its mobile chip row, the
 * two panels' cards and the counts, plus the interaction layer's translated
 * labels. The page around them — its hero, its tab bar, its layout and its
 * words — is the LiveCanvas dynamic template assigned to the page
 * (`content/livecanvas/faq_page.html` and its German twin); these shortcodes
 * print lists, counts and semantic markup with class names, no script and no
 * inline style, so the page is complete without JavaScript (docs/specs/176-
 * faq-download.md).
 *
 * One reading, one page: model() groups the documents and the answers by
 * brand once per request, so a card's count, the rail's count and the tab's
 * count cannot disagree with the rows under them. The trade rules are the
 * page's own frozen content (`data/faq-trade.json`, read by TradeRules); the
 * answers and the documents come from the products' own readings
 * (DocumentLibrary), the same ones the product pages use.
 *
 * The interaction layer (assets/library-ui.js) only ever toggles this markup:
 * it paginates the rows the server printed, filters them by the type chips,
 * and builds the search's result list by cloning the rows that match. Nothing
 * it renders is content the HTML does not already carry.
 */
final class LibraryPage {

	/**
	 * Rows one page of a card or of the search results shows: the accepted
	 * prototype's page size.
	 */
	public const PAGE_SIZE = 20;

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
	 * The type tile's file icon.
	 */
	private const FILE_ICON = '<svg class="linker-library-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true" focusable="false"><path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M14 3v6h6"/></svg>';

	/**
	 * The download link's arrow.
	 */
	private const DOWNLOAD_ICON = '<svg class="linker-library-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" stroke-linecap="round" stroke-linejoin="round"/></svg>';

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
	 * The register's first-page thumbnails.
	 *
	 * @var DocumentThumbnails
	 */
	private readonly DocumentThumbnails $thumbs;

	/**
	 * The page's model, assembled once per request.
	 *
	 * @var array{
	 *   trade: list<array{id: string, name: string, count: int, questions: list<array{question: string, answer: string}>}>,
	 *   brands: list<array{name: string, logo: string, mark: string, answers_id: string, documents_id: string, answers: list<array{question: string, answer: string, product: string, url: string, source: string, source_url: string}>|null, documents: list<array{title: string, url: string, type: string, type_label: string, language: string, language_label: string, covers: string, thumb: array{src: string, width: int, height: int}|null}>|null}>,
	 *   types: list<array{type: string, label: string, count: int}>,
	 *   faq_total: int,
	 *   document_total: int
	 * }|null
	 */
	private ?array $model = null;

	/**
	 * Sets up the page.
	 *
	 * @param DocumentLibrary|null    $library Register override (tests).
	 * @param TradeRules|null         $rules   Trade-rule data override (tests).
	 * @param DocumentThumbnails|null $thumbs  Thumbnail-manifest override (tests).
	 */
	public function __construct(
		?DocumentLibrary $library = null,
		?TradeRules $rules = null,
		?DocumentThumbnails $thumbs = null
	) {
		$this->library = $library ?? new DocumentLibrary();
		$this->rules   = $rules ?? new TradeRules();
		$this->thumbs  = $thumbs ?? new DocumentThumbnails();
	}

	/**
	 * Adds the fragments' shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_library_count', array( $this, 'count' ) );
		add_shortcode( 'linker_library_total', array( $this, 'total' ) );
		add_shortcode( 'linker_library_rail', array( $this, 'rail' ) );
		add_shortcode( 'linker_library_chips', array( $this, 'chips' ) );
		add_shortcode( 'linker_library_faq', array( $this, 'faq' ) );
		add_shortcode( 'linker_library_documents', array( $this, 'documents' ) );
		add_shortcode( 'linker_library_config', array( $this, 'config' ) );
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
		$trade = (string) __( 'Before you order', 'linker-commerce' );
		$faq   = (string) __( 'Product answers', 'linker-commerce' );
		$docs  = (string) __( 'Brands', 'linker-commerce' );

		$links = '';
		foreach ( $model['trade'] as $category ) {
			$links .= '<a href="#' . esc_attr( $category['id'] ) . '" data-library-spy-link>' . esc_html( $category['name'] ) . ' <span class="linker-library-n">' . esc_html( (string) $category['count'] ) . '</span></a>';
		}
		$brand_links = '';
		foreach ( $model['brands'] as $brand ) {
			$brand_links .= '<a href="#' . esc_attr( $brand['answers_id'] ) . '" data-library-spy-link>' . esc_html( $brand['name'] ) . ' <span class="linker-library-n">' . esc_html( (string) count( $brand['answers'] ?? array() ) ) . '</span></a>';
		}
		$document_links = '';
		foreach ( $model['brands'] as $brand ) {
			$document_links .= '<a href="#' . esc_attr( $brand['documents_id'] ) . '" data-library-spy-link>' . esc_html( $brand['name'] ) . ' <span class="linker-library-n">' . esc_html( (string) count( $brand['documents'] ?? array() ) ) . '</span></a>';
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
		$trade       = (string) __( 'Before you order', 'linker-commerce' );
		$faq         = (string) __( 'Product answers', 'linker-commerce' );
		$trade_chips = '';
		foreach ( $model['trade'] as $category ) {
			$trade_chips .= $this->chip( $category['id'], $category['name'], $category['count'] );
		}
		$answer_chips = '';
		foreach ( $model['brands'] as $brand ) {
			$answer_chips .= $this->chip( $brand['answers_id'], $brand['name'], count( $brand['answers'] ?? array() ) );
		}
		$document_chips = '';
		foreach ( $model['brands'] as $brand ) {
			$document_chips .= $this->chip( $brand['documents_id'], $brand['name'], count( $brand['documents'] ?? array() ) );
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
		$where = '<span class="linker-library-qa-where" hidden>' . esc_html( (string) __( 'In the answer', 'linker-commerce' ) ) . '</span>';

		$cards = '';
		foreach ( $model['trade'] as $category ) {
			$rows = '';
			foreach ( $category['questions'] as $question ) {
				$rows .= '<details class="linker-library-qa" data-library-item data-library-group="' . esc_attr( $category['name'] ) . '">';
				$rows .= '<summary class="linker-library-qa-head"><span class="linker-library-qa-text">';
				$rows .= '<span class="linker-library-qa-q">' . esc_html( $question['question'] ) . '</span>' . $where;
				$rows .= '</span></summary>';
				$rows .= '<div class="linker-library-qa-a"><p>' . wp_kses_post( $question['answer'] ) . '</p></div>';
				$rows .= '</details>';
			}
			$cards .= $this->card( $category['id'], 'trade', $category['name'], $category['count'], '', $rows, '' );
		}
		$out = $this->zone( self::ZONE_TRADE, (string) __( 'Before you order', 'linker-commerce' ), $cards );

		$cards = '';
		foreach ( $model['brands'] as $brand ) {
			$answers = $brand['answers'] ?? array();
			$rows    = '';
			foreach ( $answers as $answer ) {
				$rows .= '<details class="linker-library-qa" data-library-item data-library-group="' . esc_attr( $brand['name'] ) . '">';
				$rows .= '<summary class="linker-library-qa-head"><span class="linker-library-qa-text">';
				$rows .= '<span class="linker-library-qa-product">' . esc_html( $answer['product'] ) . '</span>';
				$rows .= '<span class="linker-library-qa-q">' . esc_html( $answer['question'] ) . '</span>' . $where;
				$rows .= '</span></summary>';
				$rows .= '<div class="linker-library-qa-a"><p>' . wp_kses_post( $answer['answer'] ) . '</p>';
				$rows .= '<p class="linker-library-qa-source"><a href="' . esc_url( $answer['url'] ) . '">' . esc_html( $answer['product'] ) . '</a>';
				if ( '' !== $answer['source'] ) {
					$rows .= ' — <a href="' . esc_url( $answer['source_url'] ) . '">' . esc_html( $answer['source'] ) . '</a>';
				}
				$rows .= '</p></div></details>';
			}
			$cards .= $this->card( $brand['answers_id'], 'answer', $brand['name'], count( $answers ), $brand['logo'], $rows, $brand['mark'] );
		}
		$out .= $this->zone( self::ZONE_ANSWERS, (string) __( 'Product answers', 'linker-commerce' ), $cards );

		return $out;
	}

	/**
	 * The documents tab: the type chips, then the register, one card per
	 * brand. A row carries its first-page thumbnail where the build shipped
	 * one and the type tile where it did not.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function documents( $atts = array() ): string {
		unset( $atts );
		$model = $this->model();
		$out   = '<div class="linker-library-filters" data-library-filters hidden role="group" aria-label="' . esc_attr( (string) __( 'Document type', 'linker-commerce' ) ) . '">';
		$out  .= '<button type="button" class="linker-library-chip" data-library-type="all" aria-pressed="true">' . esc_html( (string) __( 'All', 'linker-commerce' ) ) . ' <span class="linker-library-n">' . esc_html( (string) $model['document_total'] ) . '</span></button>';
		foreach ( $model['types'] as $type ) {
			$out .= '<button type="button" class="linker-library-chip" data-library-type="' . esc_attr( $type['type'] ) . '" aria-pressed="false">' . esc_html( $type['label'] ) . ' <span class="linker-library-n">' . esc_html( (string) $type['count'] ) . '</span></button>';
		}
		$out .= '</div>';

		$cards = '';
		foreach ( $model['brands'] as $brand ) {
			$documents = $brand['documents'] ?? array();
			$rows      = '';
			foreach ( $documents as $document ) {
				$rows .= $this->document( $document );
			}
			$cards .= $this->card( $brand['documents_id'], 'document', $brand['name'], count( $documents ), $brand['logo'], $rows, $brand['mark'] );
		}
		$out .= $this->zone( self::ZONE_DOCUMENTS, (string) __( 'Brands', 'linker-commerce' ), $cards );

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
			(string) filemtime( $path ),
			array(
				'strategy'  => 'defer',
				'in_footer' => true,
			)
		);
		$config = array(
			'pageSize' => self::PAGE_SIZE,
			'genieUrl' => $this->genie_url(),
			'i18n'     => array(
				/* translators: %d: number of matching entries. */
				'resultsOne'   => __( '%d result', 'linker-commerce' ),
				/* translators: %d: number of matching entries. */
				'resultsOther' => __( '%d results', 'linker-commerce' ),
				/* translators: %d: number of questions and documents on file. */
				'onFile'       => __( '%d on file', 'linker-commerce' ),
				'empty'        => __( 'Nothing on file matches that search.', 'linker-commerce' ),
				'emptySoft'    => __( 'No documents of this type.', 'linker-commerce' ),
				'askGenie'     => __( 'Ask Genie', 'linker-commerce' ),
				'trade'        => __( 'Trade rule', 'linker-commerce' ),
				'answer'       => __( 'Answer', 'linker-commerce' ),
				'document'     => __( 'Document', 'linker-commerce' ),
				'previous'     => __( 'Previous', 'linker-commerce' ),
				'next'         => __( 'Next', 'linker-commerce' ),
				'pages'        => __( 'Pages', 'linker-commerce' ),
				'questions'    => __( 'Questions', 'linker-commerce' ),
				'documents'    => __( 'Documents', 'linker-commerce' ),
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
	 * @param string $id    Anchor id.
	 * @param string $kind  `trade`, `answer` or `document`.
	 * @param string $title Card title.
	 * @param int    $count Row count as printed now.
	 * @param string $logo  Brand logo URL, '' for a card without one.
	 * @param string $rows  The rows.
	 * @param string $mark  Initials the logo falls back to, '' for no mark.
	 */
	private function card( string $id, string $kind, string $title, int $count, string $logo, string $rows, string $mark ): string {
		$head = '<header class="linker-library-card-head">';
		if ( '' !== $logo ) {
			$head .= '<span class="linker-library-logo"><img src="' . esc_url( $logo ) . '" alt="' . esc_attr( $title ) . '" height="' . esc_attr( (string) self::LOGO_HEIGHT ) . '" loading="lazy" decoding="async"></span>';
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

		return '<article class="linker-library-card" id="' . esc_attr( $id ) . '" data-library-card data-library-kind="' . esc_attr( $kind ) . '" data-library-spy data-library-zone="' . esc_attr( $zone ) . '">' . $head .
			'<div class="linker-library-rows">' . $list . '</div></article>';
	}

	/**
	 * One document row: its first-page thumbnail (or its type tile), its type,
	 * its title, what it covers, its language and its download.
	 *
	 * @param array{title: string, url: string, type: string, type_label: string, language: string, language_label: string, covers: string, thumb: array{src: string, width: int, height: int}|null} $document Document.
	 */
	private function document( array $document ): string {
		// `has-tile` is constant: the design gives every row the same 52x72
		// slot, and what varies is only whether a page image fills it (the
		// fragments' `has-src`) or the type tile stands alone.
		$out = '<li class="linker-library-doc has-tile" data-library-item data-library-type="' . esc_attr( $document['type'] ) . '">';
		if ( null !== $document['thumb'] ) {
			// `has-src` is what hides the tile's icon while the page image is
			// there; a reader without the script sees the image, and the
			// script's error path takes the class back off.
			$out .= '<span class="linker-library-thumb has-src" aria-hidden="true"><img src="' . esc_url( $document['thumb']['src'] ) . '" alt="" width="' . esc_attr( (string) $document['thumb']['width'] ) . '" height="' . esc_attr( (string) $document['thumb']['height'] ) . '" loading="lazy" decoding="async">' . self::FILE_ICON . '</span>';
		} else {
			$out .= '<span class="linker-library-thumb is-type is-' . esc_attr( $document['type'] ) . '" aria-hidden="true">' . self::FILE_ICON . '</span>';
		}
		$out .= '<span class="linker-library-doc-lead"><span class="linker-library-badge is-' . esc_attr( $document['type'] ) . '">' . esc_html( $document['type_label'] ) . '</span>';
		$out .= '<span class="linker-library-doc-title">' . esc_html( $document['title'] ) . '</span></span>';
		$out .= '<p class="linker-library-doc-meta"><span class="linker-library-doc-covers">' . esc_html( $document['covers'] ) . '</span>';
		$out .= '<span class="linker-library-lang"><span aria-hidden="true">' . esc_html( $document['language'] ) . '</span><span class="linker-library-sr">' . esc_html( $document['language_label'] ) . '</span></span></p>';
		$out .= '<a class="linker-library-dl" href="' . esc_url( $document['url'] ) . '" target="_blank" rel="noopener noreferrer">' . esc_html( (string) __( 'Download', 'linker-commerce' ) ) . '<span class="linker-library-sr"> ' . esc_html( $document['title'] ) . '</span>' . self::DOWNLOAD_ICON . '</a>';
		$out .= '</li>';

		return $out;
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
	 * A document language's display name; the combined forms read as stored.
	 *
	 * @param string $language Stored language.
	 */
	private static function language_label( string $language ): string {
		$labels = array(
			'EN'  => __( 'English', 'linker-commerce' ),
			'DE'  => __( 'German', 'linker-commerce' ),
			'MUL' => __( 'Multilingual', 'linker-commerce' ),
		);

		return $labels[ $language ] ?? $language;
	}

	/**
	 * What a document covers: the products whose pages state it.
	 *
	 * @param string[] $covers Product names.
	 * @return string The sentence.
	 */
	private static function covers( array $covers ): string {
		if ( 1 === count( $covers ) ) {
			/* translators: %s: product name. */
			return sprintf( __( 'covers %s', 'linker-commerce' ), $covers[0] );
		}

		return sprintf(
			/* translators: %d: number of products. */
			_n( 'covers %d product', 'covers %d products', count( $covers ), 'linker-commerce' ),
			count( $covers )
		);
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
	 * page's own lockup uses (`our-brand-<slug>-mono-light`); '' when the
	 * library holds none, and the card then shows its initials.
	 *
	 * @param string $brand Brand name.
	 */
	private function logo( string $brand ): string {
		$slug = sanitize_title( $brand );
		if ( '' === $slug ) {
			return '';
		}
		$attachment = get_posts(
			array(
				'post_type'      => 'attachment',
				'posts_per_page' => 1,
				'fields'         => 'ids',
				'no_found_rows'  => true,
				'post_status'    => 'inherit',
				'meta_key'       => '_wp_attached_file', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- the media library's own lookup.
				's'              => 'our-brand-' . $slug . '-mono-light',
			)
		);
		$id         = array() !== $attachment ? (int) reset( $attachment ) : 0;
		$source     = $id > 0 ? wp_get_attachment_image_src( $id, 'full' ) : false;

		return is_array( $source ) ? (string) $source[0] : '';
	}

	/**
	 * The page's model, assembled once: the trade rules, the answers and the
	 * documents grouped by brand, and the counts over them. Brands keep the
	 * order the answers state them in (the register's own order); a brand with
	 * documents and no answers follows the ones with answers.
	 *
	 * @return array{
	 *   trade: list<array{id: string, name: string, count: int, questions: list<array{question: string, answer: string}>}>,
	 *   brands: list<array{name: string, logo: string, mark: string, answers_id: string, documents_id: string, answers: list<array{question: string, answer: string, product: string, url: string, source: string, source_url: string}>|null, documents: list<array{title: string, url: string, type: string, type_label: string, language: string, language_label: string, covers: string, thumb: array{src: string, width: int, height: int}|null}>|null}>,
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

		/**
		 * The products' answers, filed by the brand of the product that states
		 * them.
		 *
		 * @var array<string, list<array{question: string, answer: string, product: string, url: string, source: string, source_url: string}>> $answers
		 */
		$answers = array();
		foreach ( $this->library->answers( $language ) as $answer ) {
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
		 * @var array<string, list<array{title: string, url: string, type: string, type_label: string, language: string, language_label: string, covers: string, thumb: array{src: string, width: int, height: int}|null}>> $documents
		 */
		$documents = array();
		foreach ( $this->library->documents() as $document ) {
			$type                              = $document['type'];
			$documents[ $document['brand'] ][] = array(
				'title'          => $document['title'],
				'url'            => $document['url'],
				'type'           => $type,
				'type_label'     => self::type_label( $type ),
				'language'       => $document['language'],
				'language_label' => self::language_label( $document['language'] ),
				'covers'         => self::covers( $document['covers'] ),
				'thumb'          => $this->thumbs->of( $document['url'] ),
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
