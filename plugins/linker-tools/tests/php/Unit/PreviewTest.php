<?php
/**
 * Tests for Genie's preview card: which pages carry it and what it says.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Preview;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Preview.
 *
 * @covers \Linker\Tools\Genie\Preview
 */
final class PreviewTest extends TestCase {

	/**
	 * The four page types carry the card, each with its anchor; every
	 * other page — the draft, the Proforma request, the account and
	 * sign-in, contact, the solution hub itself — carries none.
	 *
	 * @dataProvider pages
	 *
	 * @param string      $page     The page the request is for.
	 * @param string|null $type     The card's page type, null for no card.
	 * @param string      $name     The name the card gives the page.
	 */
	public function test_context_per_page( string $page, ?string $type, string $name ): void {
		$this->page( $page );

		$context = ( new Preview() )->context();

		if ( null === $type ) {
			$this->assertNull( $context );
		} else {
			$this->assertSame(
				array(
					'type' => $type,
					'name' => $name,
				),
				$context
			);
		}
		$this->assertConditionsMet();
	}

	/**
	 * Pages, the card's type and the name it gives them.
	 *
	 * @return array<string, array{0: string, 1: string|null, 2: string}>
	 */
	public function pages(): array {
		return array(
			'home'             => array( 'home', 'home', 'GoodWe GW60K-STS-G10' ),
			'product'          => array( 'product', 'product', 'SAJ H2-10K-T3' ),
			'category'         => array( 'category', 'category', 'EMS & Monitoring' ),
			'solution (en)'    => array( 'solution', 'solution', 'Residential Storage' ),
			'solution (de)'    => array( 'solution-de', 'solution', 'Heimspeicher' ),
			'solution hub'     => array( 'hub', null, '' ),
			'solution draft'   => array( 'cart', null, '' ),
			'proforma request' => array( 'proforma', null, '' ),
			'account, sign-in' => array( 'account', null, '' ),
			'admin'            => array( 'admin', null, '' ),
		);
	}

	/**
	 * The product's name is its title without the description in brackets,
	 * with WordPress's entities decoded.
	 */
	public function test_product_name(): void {
		WP_Mock::passthruFunction( 'wp_strip_all_tags' );
		$preview = new Preview();

		$this->assertSame( 'SAJ H2-10K-T3', $preview->product_name( 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)' ) );
		$this->assertSame( 'SAJ CB2-100.3-HV5', $preview->product_name( 'SAJ CB2-100.3-HV5 (100.3 kWh C&amp;I battery cabinet)' ) );
		$this->assertSame( 'EcoFlow OCEAN 2 Battery 8.03 kWh', $preview->product_name( 'EcoFlow OCEAN 2 Battery 8.03 kWh (EF BD-8-S2)' ) );
		$this->assertSame( 'GoodWe GW60K-STS-G10', $preview->product_name( 'GoodWe GW60K-STS-G10' ) );
		$this->assertSame( '(Spare part)', $preview->product_name( '(Spare part)' ) );
	}

	/**
	 * Solution names drop their title-case capitals inside an English
	 * sentence and keep acronyms; German keeps its nouns as they are.
	 */
	public function test_in_sentence(): void {
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		$preview = new Preview();
		$this->assertSame( 'residential storage', $preview->in_sentence( 'Residential Storage' ) );
		$this->assertSame( 'EV chargers', $preview->in_sentence( 'EV Chargers' ) );
		$this->assertSame( 'All-in-One systems', $preview->in_sentence( 'All-in-One Systems' ) );
	}

	/**
	 * German names pass through.
	 */
	public function test_in_sentence_keeps_german_nouns(): void {
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'de_DE_formal' ) );
		$this->assertSame( 'Gewerblicher Speicher', ( new Preview() )->in_sentence( 'Gewerblicher Speicher' ) );
	}

	/**
	 * Each page type says two to four things Genie answers, and names the
	 * page in the title and the questions that need it.
	 *
	 * @dataProvider copies
	 *
	 * @param string $type The page type.
	 * @param string $name The page's name.
	 */
	public function test_copy_names_the_page( string $type, string $name ): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );

		$copy = ( new Preview() )->copy(
			array(
				'type' => $type,
				'name' => $name,
			)
		);

		$this->assertGreaterThanOrEqual( 2, count( $copy['asks'] ) );
		$this->assertLessThanOrEqual( 4, count( $copy['asks'] ) );
		$this->assertNotSame( '', $copy['lead'] );
		if ( '' !== $name && 'home' !== $type ) {
			$this->assertStringContainsStringIgnoringCase( $name, $copy['title'] );
		}
		if ( '' !== $name ) {
			$this->assertStringContainsStringIgnoringCase( $name, $copy['asks'][0] );
		}
		// The home card names no fixed product: a fixed name goes stale when
		// the product is withdrawn; the model comes from the product data.
		if ( 'home' === $type ) {
			foreach ( $copy['asks'] as $ask ) {
				$this->assertDoesNotMatchRegularExpression( '/H2-10K-T3|GW10K-EHA-G20/', $ask );
			}
		}
		foreach ( $copy['asks'] as $ask ) {
			$this->assertStringNotContainsString( '%s', $ask );
		}
	}

	/**
	 * Page types and names.
	 *
	 * @return array<string, array{0: string, 1: string}>
	 */
	public function copies(): array {
		return array(
			'home'              => array( 'home', 'GoodWe GW60K-STS-G10' ),
			'home, empty range' => array( 'home', '' ),
			'product'           => array( 'product', 'SAJ H2-10K-T3' ),
			'category'          => array( 'category', 'Inverters' ),
			'solution'          => array( 'solution', 'Residential Storage' ),
		);
	}

	/**
	 * The card is printed hidden, with its anchor, the questions as both
	 * label and payload, the close button's label and the AI disclosure.
	 */
	public function test_card_prints_the_hidden_card(): void {
		$this->page( 'product' );
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'esc_attr__' );
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::passthruFunction( 'esc_attr' );
		WP_Mock::passthruFunction( 'esc_html' );

		ob_start();
		( new Preview() )->card();
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'data-linker-genie-peek ', $html );
		$this->assertStringContainsString( ' hidden>', $html );
		$this->assertStringContainsString( 'data-anchor=".pdp-layout"', $html );
		$this->assertStringNotContainsString( 'data-page-type', $html );
		$this->assertStringContainsString( 'aria-live="polite"', $html );
		$this->assertStringNotContainsString( 'autofocus', $html );
		$this->assertStringContainsString( 'SAJ H2-10K-T3', $html );
		$this->assertSame( 3, substr_count( $html, 'data-linker-genie-peek-ask=' ) );
		$this->assertStringContainsString( 'data-linker-genie-peek-close', $html );
		$this->assertStringContainsString( 'AI assistant', $html );
		// Its own attribute: the dock loader's click handler must not also
		// open on a suggestion (the card dispatches the ask event once).
		$this->assertStringNotContainsString( 'data-linker-genie-open', $html );
		$this->assertConditionsMet();
	}

	/**
	 * A solution page's main content is the first section after its hero
	 * (both hero templates), not the hero itself.
	 */
	public function test_solution_anchor_is_the_section_after_the_hero(): void {
		$this->page( 'solution' );
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'esc_attr__' );
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::passthruFunction( 'esc_attr' );
		WP_Mock::passthruFunction( 'esc_html' );

		ob_start();
		( new Preview() )->card();
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'data-anchor=":is(.lk-hero-cinematic, .lk-hero-utility) ~ section"', $html );
		$this->assertStringContainsString( 'Planning a residential storage project?', $html );
		$this->assertConditionsMet();
	}

	/**
	 * A page without the card prints nothing and loads nothing.
	 */
	public function test_other_pages_get_nothing(): void {
		$this->page( 'cart' );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );

		$preview = new Preview();
		ob_start();
		$preview->card();
		$html = (string) ob_get_clean();
		$preview->assets();

		$this->assertSame( '', $html );
		$this->assertConditionsMet();
	}

	/**
	 * A page with the card loads the card's script and stylesheet.
	 */
	public function test_assets_load_with_the_card(): void {
		$this->page( 'home' );
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'times' => 1,
				'args'  => array( Preview::HANDLE ),
			)
		);
		WP_Mock::userFunction(
			'wp_enqueue_style',
			array(
				'times' => 1,
				'args'  => array( Preview::HANDLE ),
			)
		);

		( new Preview() )->assets();

		$this->assertConditionsMet();
	}

	/**
	 * Mocks the conditional tags for one page.
	 *
	 * @param string $page home, product, category, solution, solution-de, hub, cart, proforma, account or admin.
	 */
	private function page( string $page ): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => 'admin' === $page ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'solution-de' === $page ? 'de_DE_formal' : 'en_US' ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => 'home' === $page ) );
		WP_Mock::userFunction( 'is_product', array( 'return' => 'product' === $page ) );
		WP_Mock::userFunction( 'is_product_category', array( 'return' => 'category' === $page ) );
		WP_Mock::userFunction( 'is_page', array( 'return' => in_array( $page, array( 'solution', 'solution-de', 'hub', 'cart', 'proforma', 'account' ), true ) ) );
		$ids = array(
			'product'     => 4107,
			'solution'    => 750,
			'solution-de' => 6923,
			'hub'         => 746,
			'cart'        => 11,
			'proforma'    => 12,
			'account'     => 13,
		);
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => $ids[ $page ] ?? 0 ) );
		$titles = array(
			4107 => 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)',
			750  => 'Residential Storage',
			6923 => 'Heimspeicher',
		);
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'return' => static fn( int $id ): string => $titles[ $id ] ?? 'Page',
			)
		);
		WP_Mock::userFunction( 'single_term_title', array( 'return' => 'EMS &amp; Monitoring' ) );
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => static fn(): array => array( new \WP_Term( (object) array( 'term_id' => 449 ) ) ),
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'solution-de' === $page ? 'de' : 'en' ) );
		WP_Mock::userFunction( 'pll_get_term', array( 'return' => 610 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => array(
					new \WP_Post(
						(object) array(
							'ID'         => 6530,
							'post_title' => 'GoodWe GW60K-STS-G10',
						)
					),
				),
			)
		);
		WP_Mock::passthruFunction( 'wp_strip_all_tags' );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'return' => static fn( string $path ): ?\WP_Post => 'solution' === $path
					? new \WP_Post( (object) array( 'ID' => 746 ) )
					: null,
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static fn( int $id, string $lang ): int => 746 === $id && 'de' === $lang ? 6871 : 0,
			)
		);
		$parents = array(
			750  => 746,
			6923 => 6871,
		);
		WP_Mock::userFunction(
			'wp_get_post_parent_id',
			array(
				'return' => static fn( int $id ): int => $parents[ $id ] ?? 0,
			)
		);
	}
}
