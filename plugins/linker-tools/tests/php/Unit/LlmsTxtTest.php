<?php
/**
 * Public bilingual resource index.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\LlmsTxt;
use WP_Mock;
use WP_Mock\Tools\TestCase;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

/**
 * Check the public text resource.
 *
 * @covers \Linker\Tools\LlmsTxt
 */
final class LlmsTxtTest extends TestCase {
	/** The curated document is a cacheable plain-text resource, outside search results. */
	public function test_document_headers(): void {
		$this->assertSame(
			array(
				'Content-Type'  => 'text/plain; charset=utf-8',
				'X-Robots-Tag'  => 'noindex, follow',
				'Cache-Control' => 'public, max-age=0, must-revalidate',
			),
			LlmsTxt::HEADERS
		);
	}

	/** Select representatives and translated links from the published WordPress records. */
	public function test_directory_resolves_published_series_and_translated_sections(): void {
		$home   = 'https://linker.test';
		$hub    = new \WP_Post( (object) array( 'ID' => 4101 ) );
		$names  = array(
			4101 => 'Solutions',
			4102 => 'Lösungen',
			4103 => 'EcoFlow and European storage',
			1101 => 'ESA One',
			1102 => 'ESA Eins',
			1103 => 'ESA Two',
			1104 => 'ESA Zwei',
			1105 => 'EcoFlow',
		);
		$routes = array(
			4101 => '/solution/',
			4102 => '/de/loesung/',
			4103 => '/ecoflow-and-european-storage/',
			1101 => '/product/esa-one/',
			1102 => '/de/produkt/esa-eins/',
			1103 => '/product/esa-two/',
			1104 => '/de/produkt/esa-zwei/',
		);
		$en     = (object) array(
			'term_id' => 1,
			'name'    => 'Inverters',
		);
		$de     = (object) array(
			'term_id' => 2,
			'name'    => 'Wechselrichter',
		);
		WP_Mock::userFunction( 'get_page_by_path' )->andReturnUsing( static fn( string $path ) => 'solution' === $path ? $hub : null );
		WP_Mock::userFunction( 'pll_get_post' )->andReturnUsing( static fn( int $id, string $lang ) => $id - ( 1 - $id % 2 ) + ( 'de' === $lang ? 1 : 0 ) );
		WP_Mock::userFunction( 'pll_get_term' )->andReturnUsing( static fn( int $id, string $lang ) => 'de' === $lang ? 2 : 1 );
		WP_Mock::userFunction( 'is_wp_error' )->andReturn( false );
		WP_Mock::userFunction( 'get_terms' )->andReturnUsing( static fn( $args ) => 'product_cat' === $args['taxonomy'] ? array( $en, $de ) : array() );
		WP_Mock::userFunction( 'get_term_link' )->andReturnUsing( static fn( \stdClass $term ) => $home . ( 1 === $term->term_id ? '/product-category/inverters/' : '/de/produkt-kategorie/wechselrichter/' ) );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'wc_get_product_visibility_term_ids' )->andReturn( array( 'exclude-from-catalog' => 12 ) );
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing( static fn( $args ) => 'post' === $args['post_type'] ? array( 4101, 4102, 4103 ) : array( 1101, 1102, 1103, 1104, 1105, 1106 ) );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing( static fn( int $id ) => 1105 === $id ? 'draft' : 'publish' );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			static fn( int $id, string $field ) => match ( $field ) {
				'_tv_legacy_acf_json' => '{"product_series":"ESA Series"}',
				'_tv_b2b_figures' => array(
					'rated_energy_kwh' => array(
						'value' => 112.6,
						'unit'  => 'kWh',
					),
				),
				default => '',
			}
		);
		WP_Mock::userFunction( 'get_the_terms' )->andReturnUsing( static fn( int $id, string $taxonomy ) => 'pa_brand' === $taxonomy ? array( (object) array( 'name' => 'GoodWe' ) ) : array() );
		WP_Mock::userFunction( 'get_the_title' )->andReturnUsing( static fn( int $id ) => $names[ $id ] );
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn( int $id ) => $home . $routes[ $id ] );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_option' )->andReturn( 'sales@de-linker.com' );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		WP_Mock::userFunction( 'sanitize_email', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_lastpostmodified' )->andReturnUsing( static fn( string $zone, string $type ) => 'product' === $type ? '2026-11-19 12:00:00' : '2026-11-17 09:00:00' );

		$text = LlmsTxt::document( $home );
		$this->assertSame( 1, substr_count( $text, 'GoodWe · ESA Series' ) );
		$this->assertStringContainsString( '[ESA One](https://linker.test/product/esa-one/) · 112.6 kWh', $text );
		$this->assertStringContainsString( '## Technical journal', $text );
		$this->assertStringContainsString( '## Manufacturers', $text );
		$this->assertStringContainsString( '[ESA Two](https://linker.test/product/esa-two/)', $text );
		$this->assertStringContainsString( '/llms-full.txt', $text );
		$this->assertStringContainsString( '/wp-json/linker/v1/engineering-feed', $text );
		foreach ( \Linker\Commerce\Presentation\ContactChannels::company_same_as() as $profile ) {
			$this->assertStringContainsString( $profile, $text );
		}
		$this->assertStringContainsString( '[ESA Eins](https://linker.test/de/produkt/esa-eins/) · 112,6 kWh', $text );
		$this->assertStringContainsString( '[Lösungen](https://linker.test/de/loesung/)', $text );
		$this->assertStringContainsString( '[Wechselrichter](https://linker.test/de/produkt-kategorie/wechselrichter/)', $text );
		$this->assertStringContainsString( 'Last updated: 2026-11-19', $text );
		$this->assertStringContainsString( 'Official YouTube: https://www.youtube.com/@linkerenergystorage', $text );
		$this->assertStringContainsString( 'Official Facebook: https://www.facebook.com/profile.php?id=61596580037537', $text );
		$this->assertStringNotContainsString( 'EcoFlow', $text );
	}

	/** Both languages share the index and its date comes from published content. */
	public function test_public_resource_sections_and_freshness(): void {
		$sections = array(
			'Solutions'                    => array( '[Solutions](https://linker.test/solution/) · [Lösungen](https://linker.test/de/loesung/)' ),
			'Planning tools and documents' => array( '[Compare products](https://linker.test/compare-products/) · [Produkte vergleichen](https://linker.test/de/produkte-vergleichen/)' ),
			'Product categories'           => array( '[Inverters](https://linker.test/product-category/inverters/) · [Wechselrichter](https://linker.test/de/produkt-kategorie/wechselrichter/)' ),
			'Product families'             => array( '[SAJ H2](https://linker.test/product/saj-h2/)' ),
		);
		WP_Mock::userFunction( 'get_option', array( 'return' => 'sales@de-linker.com' ) );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		WP_Mock::userFunction( 'sanitize_email', array( 'return_arg' => 0 ) );
		$text = LlmsTxt::markdown( $sections, '2026-11-19', 'https://linker.test/sitemaps.xml' );
		$this->assertStringStartsWith( '# Linker Technology GmbH', $text );
		$this->assertStringContainsString( 'Last updated: 2026-11-19', $text );
		$this->assertStringContainsString( 'Official YouTube: https://www.youtube.com/@linkerenergystorage', $text );
		$this->assertStringContainsString( 'Official Facebook: https://www.facebook.com/profile.php?id=61596580037537', $text );
		foreach ( $sections as $name => $links ) {
			$this->assertStringContainsString( "## $name\n\n- " . $links[0], $text );
		}
		$this->assertStringContainsString( 'https://linker.test/sitemaps.xml', $text );
		$this->assertDoesNotMatchRegularExpression( '/EcoFlow|Read More|\b(?:cart|checkout|payment|shipping|Incoterms)\b/i', $text );
	}
}
