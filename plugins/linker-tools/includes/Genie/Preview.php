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
 * The card names the page from what the page already shows — the product's
 * title, the category's name, the solution page's title. Reading the page's
 * content for Genie is ticket #234; the card switches to that page context
 * once it exists.
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
	 * - solution: the solution page's hero.
	 *
	 * @var array<string, string>
	 */
	private const ANCHORS = array(
		'home'     => '.hero-cinematic',
		'product'  => '.pdp-layout',
		'category' => '.product-card',
		'solution' => '.lk-hero-cinematic',
	);

	/**
	 * Path of the solution hub in English; its German twin is found through
	 * the language layer. The solution pages are its children.
	 */
	private const SOLUTION_HUB = 'solution';

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
			'<aside class="linker-genie-peek" data-linker-genie-peek data-page-type="%1$s" data-anchor="%2$s" aria-labelledby="linker-genie-peek-title" aria-live="polite" hidden><div class="linker-genie-peek__head"><span class="linker-genie-peek__mark" aria-hidden="true">&#10022;</span><span class="linker-genie-peek__name">Genie</span><button type="button" class="linker-genie-peek__close" data-linker-genie-peek-close aria-label="%3$s"><span aria-hidden="true">&times;</span></button></div><p class="linker-genie-peek__title" id="linker-genie-peek-title">%4$s</p><p class="linker-genie-peek__lead">%5$s</p><ul class="linker-genie-peek__asks">%6$s</ul><p class="linker-genie-peek__ai">%7$s<span aria-hidden="true"> · </span>%8$s</p></aside>',
			esc_attr( $context['type'] ),
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
	 * The page the card is for, or null when this page gets no card.
	 *
	 * @return array{type: 'home'|'product'|'category'|'solution', name: string}|null
	 */
	public function context(): ?array {
		if ( is_admin() ) {
			return null;
		}
		if ( is_front_page() ) {
			return array(
				'type' => 'home',
				'name' => '',
			);
		}
		if ( function_exists( 'is_product' ) && is_product() ) {
			return array(
				'type' => 'product',
				'name' => $this->product_name( (string) get_the_title( get_queried_object_id() ) ),
			);
		}
		if ( function_exists( 'is_product_category' ) && is_product_category() ) {
			return array(
				'type' => 'category',
				'name' => $this->plain( (string) single_term_title( '', false ) ),
			);
		}
		if ( is_page() && $this->is_solution( (int) get_queried_object_id() ) ) {
			return array(
				'type' => 'solution',
				'name' => $this->plain( (string) get_the_title( get_queried_object_id() ) ),
			);
		}
		return null;
	}

	/**
	 * A title as plain text. WordPress keeps names entity-encoded ("C&amp;I
	 * battery cabinet", "EMS &amp; Monitoring"); the card escapes once, on
	 * output.
	 *
	 * @param string $title A post title or term name.
	 */
	private function plain( string $title ): string {
		return trim( html_entity_decode( wp_strip_all_tags( $title ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
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
				return array(
					/* translators: %s: the solution's name, e.g. "residential storage". */
					'title' => sprintf( __( 'Planning a %s project?', 'linker-tools' ), $this->in_sentence( $name ) ),
					'lead'  => __( 'Genie sizes the system and picks the products with you.', 'linker-tools' ),
					'asks'  => array(
						/* translators: %s: the solution's name. */
						sprintf( __( 'What do I need for a %s system?', 'linker-tools' ), $this->in_sentence( $name ) ),
						/* translators: %s: the solution's name. */
						sprintf( __( 'Size a %s system for my project', 'linker-tools' ), $this->in_sentence( $name ) ),
					),
				);
			default:
				return array(
					'title' => __( 'Ask Genie about our products', 'linker-tools' ),
					'lead'  => __( 'Genie finds any model in our range and checks what works with it.', 'linker-tools' ),
					'asks'  => array(
						__( 'Find the SAJ H2-10K-T3', 'linker-tools' ),
						__( 'Which batteries work with the GoodWe ESA GW10K-EHA-G20?', 'linker-tools' ),
						__( 'Compare SAJ and GoodWe hybrid inverters', 'linker-tools' ),
					),
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
		$title = $this->plain( $title );
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
