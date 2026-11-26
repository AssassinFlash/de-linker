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
				'X-Robots-Tag'  => 'noindex',
				'Cache-Control' => 'public, max-age=3600',
			),
			LlmsTxt::HEADERS
		);
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
		WP_Mock::userFunction( 'sanitize_email', array( 'return_arg' => 0 ) );
		$text = LlmsTxt::markdown( $sections, '2026-11-19', 'https://linker.test/sitemaps.xml' );
		$this->assertStringStartsWith( '# Linker Technology GmbH', $text );
		$this->assertStringContainsString( 'Last updated: 2026-11-19', $text );
		foreach ( $sections as $name => $links ) {
			$this->assertStringContainsString( "## $name\n\n- " . $links[0], $text );
		}
		$this->assertStringContainsString( 'https://linker.test/sitemaps.xml', $text );
		$this->assertDoesNotMatchRegularExpression( '/EcoFlow|Read More|\b(?:cart|checkout|payment|shipping|Incoterms)\b/i', $text );
	}
}
