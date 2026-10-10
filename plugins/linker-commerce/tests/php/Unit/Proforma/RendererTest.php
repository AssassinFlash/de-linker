<?php
/**
 * Tests for the PDF renderer, with the real dompdf.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use Linker\Commerce\Proforma\Renderer;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Renderer.
 *
 * @covers \Linker\Commerce\Proforma\Renderer
 */
final class RendererTest extends TestCase {

	/**
	 * A one-page A4 PDF with the text in an embedded font that covers umlauts and the euro sign.
	 */
	public function test_pdf(): void {
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => dirname( __DIR__, 4 ) . '/' ) );
		WP_Mock::userFunction( 'get_temp_dir', array( 'return' => sys_get_temp_dir() . '/' ) );

		$pdf = ( new Renderer( dirname( __DIR__, 4 ) . '/linker-commerce.php' ) )->pdf( '<html><head><meta charset="utf-8"></head><body><h1>Proformarechnung</h1><p>Gesamtbetrag: 58.809,80 € – Straße</p></body></html>' );

		$this->assertSame( '%PDF-', substr( $pdf, 0, 5 ) );
		$this->assertSame( 1, preg_match( '/\/MediaBox \[0(\.0+)? 0(\.0+)? 595\.280* 841\.890*\]/', $pdf ), 'A4 is 595.28 × 841.89 points' );
		$this->assertSame( 1, preg_match( '/DejaVuSans/', $pdf ), 'embedded DejaVu Sans' );
		$this->assertSame( 1, preg_match_all( '/\/Type \/Page\b/', $pdf ), 'one page' );
	}

	/**
	 * The template is filled by WooCommerce's loader from this plugin's templates (a theme may override it).
	 */
	public function test_html(): void {
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction(
			'wc_get_template_html',
			array(
				'times'  => 1,
				'args'   => array( 'proforma/proforma.php', array( 'proforma' => array( 'number' => 'PI-2026-0001' ) ), '', '/plugin/templates/' ),
				'return' => '<html></html>',
			)
		);

		$this->assertSame( '<html></html>', ( new Renderer( '/plugin/linker-commerce.php' ) )->html( array( 'number' => 'PI-2026-0001' ) ) );
	}
}
