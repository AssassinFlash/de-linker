<?php
/**
 * Test double for the WordPress query of one page of the site.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use WP_Mock;

/**
 * Mocks the conditional tags, titles, paths and language twins of one page,
 * with the IDs, titles and paths of de-linker.com (read 2026-10-18).
 */
trait PageQuery {

	/**
	 * The pages: what the conditional tags answer, the queried ID, the
	 * title, the request path and the English page path.
	 *
	 * @var array<string, array<string, mixed>>
	 */
	private static array $site_pages = array(
		'home'        => array(
			'front' => true,
			'page'  => true,
			'id'    => 13,
			'title' => 'Home',
			'uri'   => '/',
		),
		'home-de'     => array(
			'front'  => true,
			'page'   => true,
			'id'     => 6913,
			'title'  => 'Startseite',
			'uri'    => '/de/',
			'locale' => 'de_DE_formal',
		),
		'product'     => array(
			'product' => true,
			'id'      => 4107,
			'title'   => 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)',
			'uri'     => '/product/saj-h2-10k-t3/',
		),
		'product-de'  => array(
			'product' => true,
			'id'      => 6741,
			'title'   => 'SAJ H2-10K-T3 (10 kW Dreiphasen-Hybridwechselrichter)',
			'uri'     => '/de/produkt/saj-h2-10k-t3/',
			'locale'  => 'de_DE_formal',
		),
		'category'    => array(
			'category' => true,
			'id'       => 449,
			'term'     => 'EMS &amp; Monitoring',
			'uri'      => '/product-category/ems-monitoring/',
		),
		'shop'        => array(
			'shop'  => true,
			'id'    => 1034,
			'title' => 'Products',
			'uri'   => '/products/',
		),
		'cart'        => array(
			'cart'  => true,
			'page'  => true,
			'id'    => 1035,
			'title' => 'Solution draft',
			'uri'   => '/cart/',
		),
		'account'     => array(
			'account' => true,
			'page'    => true,
			'id'      => 1037,
			'title'   => 'My account',
			'uri'     => '/my-account/',
		),
		'post'        => array(
			'post'  => true,
			'id'    => 551,
			'title' => 'How to Choose Between a Hybrid Inverter and an AC-Coupled Storage Setup',
			'uri'   => '/hybrid-inverter-vs-ac-coupled-storage/',
		),
		'blog'        => array(
			'blog'  => true,
			'id'    => 14,
			'title' => 'Blog',
			'uri'   => '/blog/',
		),
		'faq'         => array(
			'page'  => true,
			'id'    => 932,
			'title' => 'FAQ Download',
			'uri'   => '/faq-download/',
		),
		'faq-de'      => array(
			'page'   => true,
			'id'     => 6863,
			'title'  => 'FAQ-Download',
			'uri'    => '/de/faq-download/',
			'locale' => 'de_DE_formal',
		),
		'solution'    => array(
			'page'  => true,
			'id'    => 749,
			'title' => 'Residential Storage',
			'uri'   => '/solution/residential-storage/',
		),
		'solution-de' => array(
			'page'   => true,
			'id'     => 6923,
			'title'  => 'Heimspeicher',
			'uri'    => '/de/loesung/heimspeicher/',
			'locale' => 'de_DE_formal',
		),
		'hub'         => array(
			'page'  => true,
			'id'    => 746,
			'title' => 'Application',
			'uri'   => '/solution/',
		),
		'about'       => array(
			'page'  => true,
			'id'    => 862,
			'title' => 'About',
			'uri'   => '/about/',
		),
		'contact'     => array(
			'page'  => true,
			'id'    => 28,
			'title' => 'Contact',
			'uri'   => '/contact/',
		),
		'proforma'    => array(
			'page'  => true,
			'id'    => 1036,
			'title' => 'Proforma request',
			'uri'   => '/proforma-request/',
		),
		'search'      => array(
			'id'       => 0,
			'uri'      => '/',
			'document' => 'Search Results for “ems” – Linker',
		),
		'admin'       => array(
			'admin' => true,
			'id'    => 0,
			'uri'   => '/wp-admin/',
		),
	);

	/**
	 * The English twin of each German post (Polylang).
	 *
	 * @var array<int, int>
	 */
	private static array $english = array(
		42   => 41,
		6913 => 13,
		6741 => 4107,
		6863 => 932,
		6923 => 749,
		6871 => 746,
	);

	/**
	 * The English page paths (get_page_uri).
	 *
	 * @var array<int, string>
	 */
	private static array $paths = array(
		13   => 'home',
		932  => 'faq-download',
		749  => 'solution/residential-storage',
		746  => 'solution',
		862  => 'about',
		28   => 'contact',
		1036 => 'proforma-request',
		1035 => 'cart',
		1037 => 'my-account',
	);

	/**
	 * Mocks the query of one page.
	 *
	 * @param string      $name     A key of `$site_pages`.
	 * @param string|null $locale   determine_locale()'s answer, when not the page's.
	 * @param string|null $language The language layer's answer, when not the page's; empty for none.
	 */
	private function query( string $name, ?string $locale = null, ?string $language = null ): void {
		$page = self::$site_pages[ $name ];
		$is   = static fn( string $key ): bool => ! empty( $page[ $key ] );
		if ( null === $language ) {
			$language = isset( $page['locale'] ) ? 'de' : 'en';
		}
		WP_Mock::userFunction( 'is_admin', array( 'return' => $is( 'admin' ) ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => $locale ?? $page['locale'] ?? 'en_US' ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => '' === $language ? false : $language ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => $is( 'front' ) ) );
		WP_Mock::userFunction( 'is_product', array( 'return' => $is( 'product' ) ) );
		WP_Mock::userFunction( 'is_product_category', array( 'return' => $is( 'category' ) ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => $is( 'shop' ) ) );
		WP_Mock::userFunction( 'is_product_taxonomy', array( 'return' => $is( 'category' ) ) );
		WP_Mock::userFunction( 'is_cart', array( 'return' => $is( 'cart' ) ) );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => $is( 'account' ) ) );
		WP_Mock::userFunction( 'is_singular', array( 'return' => $is( 'post' ) ) );
		WP_Mock::userFunction( 'is_home', array( 'return' => $is( 'blog' ) ) );
		WP_Mock::userFunction( 'is_category', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_tag', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_page', array( 'return' => $is( 'page' ) ) );
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => $page['id'] ) );
		$titles = array();
		foreach ( self::$site_pages as $other ) {
			if ( isset( $other['title'] ) ) {
				$titles[ $other['id'] ] = $other['title'];
			}
		}
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'return' => static fn( int $id = 0 ): string => $titles[ $id ] ?? '',
			)
		);
		WP_Mock::userFunction( 'single_term_title', array( 'return' => $page['term'] ?? '' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 1034 ) );
		WP_Mock::userFunction( 'wp_get_document_title', array( 'return' => $page['document'] ?? '' ) );
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn( string $name ) => array(
					'home'           => 'https://de-linker.test',
					'page_for_posts' => 14,
				)[ $name ] ?? false,
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static function ( int $id, string $lang ): int {
					if ( 'en' === $lang ) {
						return self::$english[ $id ] ?? $id;
					}
					$german = array_flip( self::$english );
					return $german[ $id ] ?? 0;
				},
			)
		);
		WP_Mock::userFunction(
			'get_page_uri',
			array(
				'return' => static fn( int $id ): string => self::$paths[ $id ] ?? '',
			)
		);
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'return' => static fn( string $path ): ?\WP_Post => array(
					'solution' => new \WP_Post( (object) array( 'ID' => 746 ) ),
					'genie'    => new \WP_Post(
						(object) array(
							'ID'        => 41,
							'post_name' => 'genie',
						)
					),
				)[ $path ] ?? null,
			)
		);
		$parents = array(
			749  => 746,
			6923 => 6871,
		);
		WP_Mock::userFunction(
			'wp_get_post_parent_id',
			array(
				'return' => static fn( int $id ): int => $parents[ $id ] ?? 0,
			)
		);
		WP_Mock::passthruFunction( 'wp_strip_all_tags' );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::passthruFunction( 'esc_url_raw' );
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static fn( string $url, int $component = -1 ) => -1 === $component ? parse_url( $url ) : parse_url( $url, $component ), // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- test double of wp_parse_url.
			)
		);
		$_SERVER['REQUEST_URI'] = $page['uri'];
	}
}
