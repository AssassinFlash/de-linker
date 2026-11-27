<?php
/**
 * Bilingual public matrix sections.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use DOMDocument;
use DOMXPath;
use Linker\Commerce\Presentation\CompatibilityMatrixPage;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Public model and document bindings in the bilingual matrix.
 *
 * @covers \Linker\Commerce\Presentation\CompatibilityMatrixPage
 */
final class CompatibilityMatrixPageTest extends TestCase {
	/**
	 * Only known releases with a published counterpart and accessory can enter either pairing table.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_published_declarations_and_documented_boundaries(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnUsing( 'strip_tags' );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		WP_Mock::userFunction( 'get_permalink' )->andReturn( 'https://linker.test/inverter-battery-compatibility/' );
		WP_Mock::userFunction( 'get_locale' )->andReturn( 'en_US' );
		$products = array();
		foreach ( array(
			1 => 'Home inverter',
			2 => 'Battery A',
			3 => 'Battery B',
			4 => 'Controller',
			5 => 'Commercial inverter',
		) as $id => $model ) {
			$products[ $id ] = array(
				'name'         => $model,
				'url'          => 'https://linker.test/product/' . $id,
				'application'  => 5 === $id ? 'commercial' : 'home',
				'brand'        => 1 === $id ? 'SAJ' : 'GoodWe',
				'series'       => 1 === $id ? 'SAJ H2' : 'GoodWe BAT-C',
				'rating'       => '',
				'category'     => '',
				'certificates' => array(),
			);
		}
		$url                           = 'https://linker.test/uploads/manual.pdf';
		$pdf                           = array(
			'url'  => $url,
			'name' => 'Document',
		);
		$products[1]['certificates'][] = array(
			'url'       => $url,
			'standards' => array( 'EN 50549' ),
		);
		$pair                          = array(
			'inverter_product_id' => 1,
			'battery_product_id'  => 2,
			'verdict'             => 'released_with_accessory',
			'conditions'          => array(
				array(
					'en' => 'Two modules.',
					'de' => 'Zwei Module.',
				),
			),
			'accessories'         => array(
				array(
					'product_id' => 4,
					'per'        => 'stack',
					'quantity'   => 1,
				),
			),
			'documents'           => array(
				array(
					'url'  => $url,
					'page' => 7,
				),
			),
		);
		$claims                        = array(
			'available'    => true,
			'pairs'        => array(
				$pair,
				array_merge( $pair, array( 'conditions' => array() ) ),
				array_merge(
					$pair,
					array(
						'inverter_product_id' => 5,
						'verdict'             => 'released',
						'accessories'         => array(),
					)
				),
				array_merge(
					$pair,
					array(
						'battery_product_id' => 3,
						'verdict'            => 'not_released',
					)
				),
				array_merge( $pair, array( 'battery_product_id' => 60 ) ),
				array_merge( $pair, array( 'accessories' => array( array( 'product_id' => 61 ) ) ) ),
			),
			'requirements' => array(
				array_merge(
					$pair,
					array(
						'kind'     => 'parallel_controller',
						'included' => false,
					)
				),
			),
		);
		$html                          = CompatibilityMatrixPage::body( $products, $claims, array( '/uploads/manual.pdf' => $pdf ) );
		$dom                           = new DOMDocument();
		$dom->loadHTML( $html, LIBXML_NOERROR | LIBXML_NOWARNING );
		$xpath = new DOMXPath( $dom );
		$this->assertSame( 4.0, $xpath->evaluate( 'count(//section//table)' ) );
		foreach ( array( 'residential-pairings', 'commercial-pairings', 'system-requirements', 'grid-certificates' ) as $section ) {
			$this->assertSame( 'residential-pairings' === $section ? 2.0 : 1.0, $xpath->evaluate( 'count(//section[@id="' . $section . '"]//tbody/tr)' ) );
		}
		$this->assertStringContainsString( 'cover 2 inverter and battery combinations. An accessory is required for 1 of them.', $html );
		$this->assertSame( '3', $xpath->evaluate( 'string(//dt[.="Release declarations"]/following-sibling::dd)' ) );
		$this->assertSame( '2', $xpath->evaluate( 'string(//dt[.="Declarations requiring an accessory"]/following-sibling::dd)' ) );
		$this->assertSame( 5.0, $xpath->evaluate( 'count(//nav[@class="lk-matrix-anchors"]/a[starts-with(@href,"https://linker.test/inverter-battery-compatibility/#")])' ) );
		$this->assertStringNotContainsString( 'Battery B', (string) $xpath->evaluate( 'string(//section[@id="residential-pairings"])' ) );
		$this->assertStringContainsString( 'Battery B', (string) $xpath->evaluate( 'string(//section[@id="not-released-boundaries"])' ) );
		$this->assertStringContainsString( 'SAJ H2 × GoodWe BAT-C', $html );
		$this->assertStringNotContainsString( 'GoodWe GoodWe', $html );
		$this->assertStringNotContainsString( 'SAJ SAJ', $html );
		$this->assertStringContainsString( 'Controller', (string) $xpath->evaluate( 'string(//section[@id="residential-pairings"])' ) );
		$this->assertSame( $url . '#page=7', $xpath->evaluate( 'string(//section[@id="residential-pairings"]//a[@target="_blank"]/@href)' ) );
		$this->assertStringContainsString( 'EN 50549', (string) $xpath->evaluate( 'string(//section[@id="grid-certificates"])' ) );
		$this->assertStringContainsString( 'Supplied separately', (string) $xpath->evaluate( 'string(//section[@id="system-requirements"])' ) );
	}

	/** A missing projection retains the page title and navigation without reporting zero releases. */
	public function test_unavailable_declarations(): void {
		$this->plain_text();
		$html = CompatibilityMatrixPage::body( array(), array( 'available' => false ), array() );
		$this->assertStringContainsString( '<h1>', $html );
		$this->assertStringContainsString( 'temporarily unavailable', $html );
		$this->assertStringContainsString( 'lk-matrix-crumb', $html );
		$this->assertStringNotContainsString( 'lk-matrix-kpis', $html );
		$this->assertStringNotContainsString( '<table', $html );
	}
}
