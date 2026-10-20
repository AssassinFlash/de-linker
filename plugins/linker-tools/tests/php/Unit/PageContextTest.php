<?php
/**
 * Tests for the page context Genie's turns carry (ticket #234).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\PageContext;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for PageContext.
 *
 * @covers \Linker\Tools\Genie\PageContext
 */
final class PageContextTest extends TestCase {

	use PageQuery;

	/**
	 * Each of the eight kinds of page, in English and German, and the rest
	 * as `other`: the type, the title, the address and the IDs.
	 *
	 * @dataProvider pages
	 *
	 * @param string               $page     A page of PageQuery.
	 * @param array<string, mixed> $expected The page context.
	 */
	public function test_current_names_the_page( string $page, array $expected ): void {
		$this->query( $page );

		$this->assertSame( $expected, ( new PageContext() )->current() );
	}

	/**
	 * Pages and their context.
	 *
	 * @return array<string, array{0: string, 1: array<string, mixed>}>
	 */
	public function pages(): array {
		$url = static fn( string $path ): string => 'https://de-linker.test' . $path;
		return array(
			'home'              => array(
				'home',
				array(
					'type'    => 'home',
					'title'   => 'Home',
					'post_id' => 13,
					'url'     => $url( '/' ),
				),
			),
			'home (de)'         => array(
				'home-de',
				array(
					'type'    => 'home',
					'title'   => 'Startseite',
					'post_id' => 6913,
					'url'     => $url( '/de/' ),
				),
			),
			'product'           => array(
				'product',
				array(
					'type'       => 'product',
					'title'      => 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)',
					'product_id' => 4107,
					'post_id'    => 4107,
					'url'        => $url( '/product/saj-h2-10k-t3/' ),
				),
			),
			// The turn's product is the English post; the page is the German one.
			'product (de)'      => array(
				'product-de',
				array(
					'type'       => 'product',
					'title'      => 'SAJ H2-10K-T3 (10 kW Dreiphasen-Hybridwechselrichter)',
					'product_id' => 4107,
					'post_id'    => 6741,
					'url'        => $url( '/de/produkt/saj-h2-10k-t3/' ),
				),
			),
			'product category'  => array(
				'category',
				array(
					'type'        => 'category',
					'title'       => 'EMS & Monitoring',
					'category_id' => 449,
					'url'         => $url( '/product-category/ems-monitoring/' ),
				),
			),
			'all products'      => array(
				'shop',
				array(
					'type'  => 'category',
					'title' => 'Products',
					'url'   => $url( '/products/' ),
				),
			),
			'solution'          => array(
				'solution',
				array(
					'type'    => 'solution',
					'title'   => 'Residential Storage',
					'post_id' => 749,
					'url'     => $url( '/solution/residential-storage/' ),
				),
			),
			'solution (de)'     => array(
				'solution-de',
				array(
					'type'    => 'solution',
					'title'   => 'Heimspeicher',
					'post_id' => 6923,
					'url'     => $url( '/de/loesung/heimspeicher/' ),
				),
			),
			'solution hub'      => array(
				'hub',
				array(
					'type'    => 'solution',
					'title'   => 'Application',
					'post_id' => 746,
					'url'     => $url( '/solution/' ),
				),
			),
			'about (marketing)' => array(
				'about',
				array(
					'type'    => 'solution',
					'title'   => 'About',
					'post_id' => 862,
					'url'     => $url( '/about/' ),
				),
			),
			'blog post'         => array(
				'post',
				array(
					'type'    => 'blog',
					'title'   => 'How to Choose Between a Hybrid Inverter and an AC-Coupled Storage Setup',
					'post_id' => 551,
					'url'     => $url( '/hybrid-inverter-vs-ac-coupled-storage/' ),
				),
			),
			'blog index'        => array(
				'blog',
				array(
					'type'  => 'blog',
					'title' => 'Blog',
					'url'   => $url( '/blog/' ),
				),
			),
			'faq'               => array(
				'faq',
				array(
					'type'    => 'faq',
					'title'   => 'FAQ Download',
					'post_id' => 932,
					'url'     => $url( '/faq-download/' ),
				),
			),
			'faq (de)'          => array(
				'faq-de',
				array(
					'type'    => 'faq',
					'title'   => 'FAQ-Download',
					'post_id' => 6863,
					'url'     => $url( '/de/faq-download/' ),
				),
			),
			'solution draft'    => array(
				'cart',
				array(
					'type'  => 'draft',
					'title' => 'Solution draft',
					'url'   => $url( '/cart/' ),
				),
			),
			'account'           => array(
				'account',
				array(
					'type'  => 'account',
					'title' => 'My account',
					'url'   => $url( '/my-account/' ),
				),
			),
			'contact'           => array(
				'contact',
				array(
					'type'    => 'other',
					'title'   => 'Contact',
					'post_id' => 28,
					'url'     => $url( '/contact/' ),
				),
			),
			'proforma request'  => array(
				'proforma',
				array(
					'type'    => 'other',
					'title'   => 'Proforma request',
					'post_id' => 1036,
					'url'     => $url( '/proforma-request/' ),
				),
			),
			'search results'    => array(
				'search',
				array(
					'type'  => 'other',
					'title' => 'Search Results for “ems” – Linker',
					'url'   => $url( '/' ),
				),
			),
		);
	}

	/**
	 * What a browser sends is kept key by key: a known type, positive IDs,
	 * an address and a title; anything else is dropped, and the draft's
	 * products are not taken from it.
	 */
	public function test_sanitize_keeps_only_what_the_service_accepts(): void {
		WP_Mock::passthruFunction( 'esc_url_raw' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );

		$pages = new PageContext();

		$this->assertSame(
			array(
				'type'       => 'product',
				'product_id' => 4107,
				'post_id'    => 6741,
				'url'        => 'https://de-linker.test/de/produkt/saj-h2-10k-t3/',
				'title'      => 'SAJ H2-10K-T3',
			),
			$pages->sanitize(
				array(
					'type'        => 'product',
					'product_id'  => '4107',
					'post_id'     => 6741,
					'category_id' => -3,
					'url'         => 'https://de-linker.test/de/produkt/saj-h2-10k-t3/',
					'title'       => 'SAJ H2-10K-T3',
					'draft_ids'   => array( 1, 2 ),
					'draft_lines' => array(
						array(
							'product_id' => 1,
							'quantity'   => 99,
						),
					),
					'secret'      => 'x',
				)
			)
		);
		$this->assertSame( array( 'type' => 'other' ), $pages->sanitize( array( 'type' => 'checkout' ) ) );
		$this->assertSame( array( 'type' => 'other' ), $pages->sanitize( 'product' ) );
	}

	/**
	 * A listing keeps its query: a filtered product category is a page of
	 * its own (the service drops the query of a single page).
	 */
	public function test_current_keeps_the_query_of_a_listing(): void {
		$this->query( 'category' );
		$_SERVER['REQUEST_URI'] = '/product-category/inverters/?filter_brand=saj';

		$this->assertSame(
			'https://de-linker.test/product-category/inverters/?filter_brand=saj',
			( new PageContext() )->current()['url']
		);
	}

	/**
	 * The address is cut after it is escaped: escaping lengthens it (every
	 * "ü" becomes "%C3%BC"), and the service refuses anything over 2,048
	 * characters. A percent-encoding the cut splits is dropped.
	 */
	public function test_an_escaped_address_never_exceeds_the_services_limit(): void {
		WP_Mock::userFunction(
			'esc_url_raw',
			array(
				'return' => static fn( string $url ): string => (string) preg_replace_callback(
					'/[^\x00-\x7F]/u',
					static fn( array $found ): string => rawurlencode( $found[0] ),
					$url
				),
			)
		);
		WP_Mock::passthruFunction( 'sanitize_text_field' );

		$long = 'https://de-linker.test/de/suche/?s=' . str_repeat( 'Lösung%20', 400 );
		$page = ( new PageContext() )->sanitize(
			array(
				'type' => 'other',
				'url'  => $long,
			)
		);
		$url  = $page['url'] ?? '';

		$this->assertLessThanOrEqual( 2048, mb_strlen( $url ) );
		$this->assertStringStartsWith( 'https://de-linker.test/de/suche/?s=L%C3%B6sung', $url );
		$this->assertDoesNotMatchRegularExpression( '/%[0-9A-Fa-f]?$/', $url );
	}

	/**
	 * The draft's products are the visitor's own draft, as English posts and
	 * each once.
	 */
	public function test_draft_ids_are_the_visitors_draft_in_english(): void {
		$this->query( 'cart' );
		WP_Mock::userFunction( 'wc_load_cart', array( 'times' => 1 ) );
		$cart = new class() {
			/**
			 * Lines of the draft.
			 *
			 * @return array<string, array{product_id: int}>
			 */
			public function get_cart(): array {
				return array(
					'a' => array( 'product_id' => 6741 ),
					'b' => array( 'product_id' => 2003 ),
					'c' => array( 'product_id' => 4107 ),
				);
			}
		};
		WP_Mock::userFunction(
			'WC',
			array(
				'return' => (object) array( 'cart' => $cart ),
			)
		);

		$this->assertSame( array( 4107, 2003 ), ( new PageContext() )->draft_ids() );
		$this->assertConditionsMet();
	}

	/**
	 * The cart quantity the inquiry and contact handoff already read.
	 * Duplicate English products are one line, quantities added. A missing
	 * quantity is 0, never 1. A negative quantity is omitted, not guessed.
	 */
	public function test_draft_lines_carry_the_cart_quantity(): void {
		$this->query( 'cart' );
		WP_Mock::userFunction( 'wc_load_cart', array( 'times' => 1 ) );
		$cart = new class() {
			/**
			 * Lines of the draft, including a German twin of 4107.
			 *
			 * @return array<string, array{product_id: int, quantity?: int}>
			 */
			public function get_cart(): array {
				return array(
					'german' => array(
						'product_id' => 6741,
						'quantity'   => 2,
					),
					'same'   => array(
						'product_id' => 4107,
						'quantity'   => 3,
					),
					'other'  => array(
						'product_id' => 2003,
						'quantity'   => '1',
					),
					'blank'  => array( 'product_id' => 2004 ),
					'bad'    => array(
						'product_id' => 2005,
						'quantity'   => -4,
					),
					'zero'   => array(
						'product_id' => 0,
						'quantity'   => 9,
					),
				);
			}
		};
		WP_Mock::userFunction(
			'WC',
			array(
				'return' => (object) array( 'cart' => $cart ),
			)
		);

		$this->assertSame(
			array(
				array(
					'product_id' => 4107,
					'quantity'   => 5,
				),
				array(
					'product_id' => 2003,
					'quantity'   => 1,
				),
				array(
					'product_id' => 2004,
					'quantity'   => 0,
				),
			),
			( new PageContext() )->draft_lines()
		);
		$this->assertConditionsMet();
	}
}
