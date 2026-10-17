<?php
/**
 * Genie's preview card (ticket #249).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Prints the preview card hidden on the home page, product pages, product
 * categories and the solution pages, and loads the script that decides when
 * it appears (src/preview/; docs/specs/13-genie.md, 目标 4 and "主动预览卡").
 *
 * The card names the page from the page context Genie's turns carry
 * (PageContext, ticket #234): the product's title, the category's name, the
 * solution page's title.
 *
 * Every other page — the solution draft, the Proforma request, the account,
 * sign-in and registration, contact and the rest — gets no card: the list of
 * page types below is the whole list (目标 4: "表单、询盘、登录页不出现").
 */
final class Preview {

	/**
	 * Handle of the built `preview` entry (registered by Assets on init).
	 */
	public const HANDLE = 'linker-tools-preview';

	/**
	 * What counts as "scrolled past the main content", per page type: the
	 * element whose bottom edge must rise above 40% of the viewport
	 * (src/preview/rules.ts). Selectors of the live LiveCanvas templates,
	 * read on de-linker.com 2026-10-18:
	 * - home: the hero (目标 4: "首页在滚过 hero 之后出现");
	 * - product: the gallery and buy box (`.pdp-layout`); the description
	 *   below it is then on screen (INTL.md §0.3: "技术参数区进入视口");
	 * - category: the first product card, i.e. the first row of products
	 *   (INTL.md §0.3: "第一行产品之后");
	 * - solution: the first section after the hero (residential and
	 *   commercial pages: `.lk-hero-cinematic`, then the capabilities strip;
	 *   utility pages: `.lk-hero-utility`, then the systems section), so the
	 *   hero alone is not "the main content".
	 *
	 * @var array<string, string>
	 */
	private const ANCHORS = array(
		'home'     => '.hero-cinematic',
		'product'  => '.pdp-layout',
		'category' => '.product-card',
		'solution' => ':is(.lk-hero-cinematic, .lk-hero-utility) ~ section',
	);

	/**
	 * Path of the solution hub in English; its German twin is found through
	 * the language layer. The solution pages are its children.
	 */
	private const SOLUTION_HUB = 'solution';

	/**
	 * The product category the home card's example model comes from.
	 */
	private const EXAMPLE_CATEGORY = 'inverters';

	/**
	 * Hooks the script and the card.
	 */
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'assets' ) );
		add_action( 'wp_footer', array( $this, 'card' ) );
	}

	/**
	 * Loads the card's script and stylesheet on the pages that carry it.
	 */
	public function assets(): void {
		if ( null === $this->context() ) {
			return;
		}
		wp_enqueue_script( self::HANDLE );
		wp_enqueue_style( self::HANDLE );
	}

	/**
	 * Prints the card, hidden; the script shows it. Without JavaScript it
	 * never appears. The card takes no focus: it is not a dialog, and
	 * `aria-live` lets a screen reader announce it when it appears
	 * (INTL.md §0.3 "无障碍").
	 */
	public function card(): void {
		$context = $this->context();
		if ( null === $context ) {
			return;
		}
		$copy = $this->copy( $context );
		$asks = '';
		foreach ( $copy['asks'] as $ask ) {
			$asks .= sprintf(
				'<li><button type="button" class="linker-genie-peek__ask" data-linker-genie-peek-ask="%1$s">%2$s</button></li>',
				esc_attr( $ask ),
				esc_html( $ask )
			);
		}
		printf(
			'<aside class="linker-genie-peek" data-linker-genie-peek data-anchor="%1$s" aria-labelledby="linker-genie-peek-title" aria-live="polite" hidden><div class="linker-genie-peek__head"><span class="linker-genie-peek__mark" aria-hidden="true">&#10022;</span><span class="linker-genie-peek__name">Genie</span><button type="button" class="linker-genie-peek__close" data-linker-genie-peek-close aria-label="%2$s"><span aria-hidden="true">&times;</span></button></div><p class="linker-genie-peek__title" id="linker-genie-peek-title">%3$s</p><p class="linker-genie-peek__lead">%4$s</p><ul class="linker-genie-peek__asks">%5$s</ul><p class="linker-genie-peek__ai">%6$s<span aria-hidden="true"> · </span>%7$s</p></aside>',
			esc_attr( self::ANCHORS[ $context['type'] ] ),
			esc_attr__( 'Close. Suggestion cards stay hidden for 30 days.', 'linker-tools' ),
			esc_html( $copy['title'] ),
			esc_html( $copy['lead'] ),
			$asks, // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- every part escaped above.
			esc_html__( 'AI assistant', 'linker-tools' ),
			esc_html__( 'answers can contain mistakes', 'linker-tools' )
		);
	}

	/**
	 * Sets up the card.
	 *
	 * @param PageContext|null $pages The page of the request; a default one is built when omitted.
	 */
	public function __construct( ?PageContext $pages = null ) {
		$this->pages = $pages ?? new PageContext();
	}

	/**
	 * The page of the request (ticket #234's page context).
	 *
	 * @var PageContext
	 */
	private readonly PageContext $pages;

	/**
	 * The page the card is for, or null when this page gets no card.
	 *
	 * @return array{type: 'home'|'product'|'category'|'solution', name: string}|null
	 */
	public function context(): ?array {
		if ( is_admin() ) {
			return null;
		}
		return $this->card_page( $this->pages->current() );
	}

	/**
	 * The card's page for a page context (PageContext), or null for a page
	 * without a card. The name is the page's own: the product's title
	 * without its description, the category's name, the solution page's
	 * title; on the home page, a model of the current range.
	 *
	 * @param array{type: string, title?: string, post_id?: int, category_id?: int} $page The page context.
	 * @return array{type: 'home'|'product'|'category'|'solution', name: string}|null
	 */
	public function card_page( array $page ): ?array {
		$title = (string) ( $page['title'] ?? '' );
		switch ( $page['type'] ) {
			case 'home':
				return array(
					'type' => 'home',
					'name' => $this->example_model(),
				);
			case 'product':
				return array(
					'type' => 'product',
					'name' => $this->product_name( $title ),
				);
			case 'category':
				// The catalogue (/products/) is a category page without a
				// category; the card is for the product categories.
				return isset( $page['category_id'] )
					? array(
						'type' => 'category',
						'name' => $title,
					)
					: null;
			case 'solution':
				// The solutions only: not the hub, About or the audience pages.
				return isset( $page['post_id'] ) && $this->is_solution( (int) $page['post_id'] )
					? array(
						'type' => 'solution',
						'name' => $title,
					)
					: null;
			default:
				return null;
		}
	}

	/**
	 * The questions the card offers on a page, or null for a page without a
	 * card. The dock offers the same questions when it opens on that page
	 * (Entries::prompts), so both name the page the same way.
	 *
	 * @param array{type: string, title?: string, post_id?: int, category_id?: int} $page The page context.
	 * @return list<string>|null
	 */
	public function asks( array $page ): ?array {
		$card = $this->card_page( $page );
		return null === $card ? null : $this->copy( $card )['asks'];
	}

	/**
	 * A model from the current range for the home card's "ask about a
	 * model" suggestion: the newest published inverter (the newest product
	 * is the first card of the product listing, /products/, read
	 * 2026-10-18; the inverter category keeps the example a main product,
	 * not a meter or a cable), in the request's language. Read from the
	 * product data on every page view, so a withdrawn product is never
	 * named; empty when the range is empty, and the card then drops that
	 * suggestion.
	 */
	private function example_model(): string {
		$args = array(
			'post_type'        => 'product',
			'post_status'      => 'publish',
			'numberposts'      => 1,
			'orderby'          => array(
				'date' => 'DESC',
				'ID'   => 'DESC',
			),
			'suppress_filters' => false,
			// Hidden products are not in the listing (Woo's own visibility term).
			'tax_query'        => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- one row, once per home page view.
				'relation' => 'AND',
				array(
					'taxonomy' => 'product_cat',
					'field'    => 'term_id',
					'terms'    => $this->inverter_terms(),
				),
				array(
					'taxonomy' => 'product_visibility',
					'field'    => 'name',
					'terms'    => array( 'exclude-from-catalog' ),
					'operator' => 'NOT IN',
				),
			),
		);
		if ( function_exists( 'pll_current_language' ) && is_string( pll_current_language() ) ) {
			$args['lang'] = pll_current_language();
		}
		$posts = get_posts( $args );
		$first = $posts[0] ?? null;
		return $first instanceof \WP_Post ? $this->product_name( $first->post_title ) : '';
	}

	/**
	 * The inverter category in both languages: the English term
	 * (`inverters`) and its German twin through the language layer.
	 *
	 * @return list<int>
	 */
	private function inverter_terms(): array {
		// `lang => ''` asks the language layer for every language: on a
		// German page it would otherwise hide the English term.
		$terms = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'slug'       => self::EXAMPLE_CATEGORY,
				'hide_empty' => false,
				'number'     => 1,
				'lang'       => '',
			)
		);
		$term  = is_array( $terms ) ? ( $terms[0] ?? null ) : null;
		if ( ! $term instanceof \WP_Term ) {
			return array( 0 );
		}
		$ids = array( (int) $term->term_id );
		if ( function_exists( 'pll_get_term' ) ) {
			$twin = (int) pll_get_term( (int) $term->term_id, 'de' );
			if ( $twin > 0 ) {
				$ids[] = $twin;
			}
		}
		return $ids;
	}

	/**
	 * What the card says on one page: a title naming the page, one sentence,
	 * and two to four questions Genie answers (目标 4). The wording passed the
	 * copy review of docs/acceptance/2026-10-18/249/copy-review.md; German is
	 * written on its own in languages/linker-tools-de_DE_formal.po.
	 *
	 * @param array{type: string, name: string} $context The page.
	 * @return array{title: string, lead: string, asks: list<string>}
	 */
	public function copy( array $context ): array {
		$name = $context['name'];
		switch ( $context['type'] ) {
			case 'product':
				return array(
					/* translators: %s: the product's name, e.g. "SAJ H2-10K-T3". */
					'title' => sprintf( __( 'Looking at the %s?', 'linker-tools' ), $name ),
					'lead'  => __( 'Genie answers from our product data and the manufacturers\' documents.', 'linker-tools' ),
					'asks'  => array(
						/* translators: %s: the product's name. */
						sprintf( __( 'What pairs with the %s?', 'linker-tools' ), $name ),
						/* translators: %s: the product's name. */
						sprintf( __( 'Show the documents for the %s', 'linker-tools' ), $name ),
						/* translators: %s: the product's name. */
						sprintf( __( 'Compare the %s with similar models', 'linker-tools' ), $name ),
					),
				);
			case 'category':
				return array(
					/* translators: %s: the product category's name as the page shows it, e.g. "Inverters". */
					'title' => sprintf( __( 'Looking at %s?', 'linker-tools' ), $name ),
					'lead'  => __( 'Genie compares the models in this category and checks which suit your project.', 'linker-tools' ),
					'asks'  => array(
						/* translators: %s: the product category's name as the page shows it. */
						sprintf( __( '%s: which model fits my project?', 'linker-tools' ), $name ),
						/* translators: %s: the product category's name as the page shows it. */
						sprintf( __( '%s: how do the series differ?', 'linker-tools' ), $name ),
					),
				);
			case 'solution':
				$name = $this->in_sentence( $name );
				return array(
					/* translators: %s: the solution's name, e.g. "residential storage". */
					'title' => sprintf( __( 'Planning a %s project?', 'linker-tools' ), $name ),
					'lead'  => __( 'Genie sizes the system and picks the products with you.', 'linker-tools' ),
					'asks'  => array(
						/* translators: %s: the solution's name. */
						sprintf( __( 'What do I need for a %s system?', 'linker-tools' ), $name ),
						/* translators: %s: the solution's name. */
						sprintf( __( 'Size a %s system for my project', 'linker-tools' ), $name ),
					),
				);
			default:
				$asks = array();
				if ( '' !== $name ) {
					/* translators: %s: an inverter from the current product range, e.g. "SAJ H2-10K-T3". */
					$asks[] = sprintf( __( 'Tell me about the %s', 'linker-tools' ), $name );
				}
				$asks[] = __( 'Which batteries work with my inverter?', 'linker-tools' );
				$asks[] = __( 'Compare SAJ and GoodWe hybrid inverters', 'linker-tools' );
				return array(
					'title' => __( 'Ask Genie about our products', 'linker-tools' ),
					'lead'  => __( 'Genie finds any model in our range and checks what works with it.', 'linker-tools' ),
					'asks'  => $asks,
				);
		}
	}

	/**
	 * The product's name as the card says it: the title without its
	 * description in brackets ("SAJ H2-10K-T3 (10 kW three-phase hybrid
	 * inverter)" → "SAJ H2-10K-T3"), the way the live product titles are
	 * written.
	 *
	 * @param string $title The product's title.
	 */
	public function product_name( string $title ): string {
		$title = $this->pages->plain( $title );
		$short = trim( (string) preg_replace( '/\s*\([^()]*\)\s*$/u', '', $title ) );
		return '' !== $short ? $short : $title;
	}

	/**
	 * A solution's name inside an English sentence: a word in
	 * title case drops its capital ("Hybrid Inverters" → "hybrid
	 * inverters"); an acronym or a word with an inner capital ("EV",
	 * "All-in-One") keeps its letters. German nouns keep their capitals, so
	 * German names pass through as they are.
	 *
	 * @param string $name The name as the page shows it.
	 */
	public function in_sentence( string $name ): string {
		if ( 'de' === $this->locale() ) {
			return $name;
		}
		$words = preg_split( '/(\s+)/u', $name, -1, PREG_SPLIT_DELIM_CAPTURE );
		if ( false === $words ) {
			return $name;
		}
		foreach ( $words as $i => $word ) {
			if ( 1 === preg_match( '/^\p{Lu}[\p{Ll}\-]*$/u', $word ) ) {
				$words[ $i ] = mb_strtolower( $word );
			}
		}
		return implode( '', $words );
	}

	/**
	 * Whether a page is one of the solution pages: a child of the solution
	 * hub (`/solution/…` in English, its twin's children in German).
	 *
	 * @param int $page_id The page.
	 */
	private function is_solution( int $page_id ): bool {
		$hub = get_page_by_path( self::SOLUTION_HUB );
		if ( ! $hub instanceof \WP_Post ) {
			return false;
		}
		$hubs = array( (int) $hub->ID );
		if ( function_exists( 'pll_get_post' ) ) {
			$twin = (int) pll_get_post( (int) $hub->ID, 'de' );
			if ( $twin > 0 ) {
				$hubs[] = $twin;
			}
		}
		return in_array( (int) wp_get_post_parent_id( $page_id ), $hubs, true );
	}

	/**
	 * `en` or `de` from the page's language.
	 *
	 * @return 'en'|'de'
	 */
	private function locale(): string {
		$lang = function_exists( 'determine_locale' ) ? determine_locale() : 'en_US';
		return str_starts_with( strtolower( $lang ), 'de' ) ? 'de' : 'en';
	}
}
