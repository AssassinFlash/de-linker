<?php
/**
 * Tests for the product page's stylesheet contract.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Tests\TestCase;

/**
 * The product page's rules live in one volume file, and the rules that hid the
 * page's content stay gone (docs/specs/174-pdp.md). Each assertion here is one
 * of the ticket's root causes, read off the files themselves: the class names
 * and the geometry are the contract between the template, the stylesheet and
 * the compile.
 */
final class PdpStylesTest extends TestCase {

	/**
	 * The product page's own stylesheet, relative to the plugin.
	 */
	private const PDP_CSS = 'content/windpress/pdp.css';

	/**
	 * The storefront stylesheet that used to carry a second product-page layer.
	 */
	private const STOREFRONT_CSS = 'content/windpress/storefront.css';

	/**
	 * A stylesheet's text, comments included.
	 *
	 * @param string $file Relative path under the plugin.
	 */
	private function css( string $file ): string {
		return (string) file_get_contents( dirname( __DIR__, 4 ) . '/' . $file );
	}

	/**
	 * One owner: the storefront stylesheet no longer styles the product page,
	 * so nothing it says can land on top of the page's own rules (the
	 * 1024–1100px media queries of the two files used to disagree).
	 */
	public function test_the_storefront_stylesheet_leaves_the_product_page_alone(): void {
		$this->assertStringNotContainsString( 'tv-storefront-pdp', $this->css( self::STOREFRONT_CSS ) );
	}

	/**
	 * The rail's sticky context is the upper half: the grid places the gallery
	 * and the intro in the first column and the rail in the second, with no
	 * content row. The former `"content content purchase"` line let the rail
	 * travel into the blocks below, where it covered them.
	 */
	public function test_the_rail_is_sticky_inside_the_upper_half_only(): void {
		$css = $this->css( self::PDP_CSS );

		$this->assertStringContainsString( '"gallery rail"', $css );
		$this->assertStringContainsString( '"intro rail"', $css );
		$this->assertStringNotContainsString( '"content content purchase"', $css );
		$this->assertStringNotContainsString( 'grid-area: content', $css );
		$this->assertStringContainsString( 'grid-area: rail', $css );
	}

	/**
	 * The sticky offsets follow the measured header, not a number: the rail's
	 * top, the section nav's top and the anchors' scroll margin all read
	 * --lk-header-h, which assets/pdp-ui.js writes from the real header.
	 */
	public function test_the_sticky_offsets_read_the_measured_header(): void {
		$css = $this->css( self::PDP_CSS );

		$this->assertStringContainsString( 'top: calc(var(--lk-header-h, 80px) + 16px)', $css );
		$this->assertStringContainsString( 'top: var(--lk-header-h, 80px)', $css );
		$this->assertStringContainsString( 'scroll-margin-top: calc(var(--lk-header-h, 80px) + var(--pdp-snav-h, 52px) + 16px)', $css );
		$this->assertStringNotContainsString( 'top: 84px', $css );
	}

	/**
	 * One container rule for the page: 1360px wide with the fluid inset, not
	 * the four insets (40/16/32px) the product page used to be laid out with.
	 */
	public function test_one_container_rule(): void {
		$css = $this->css( self::PDP_CSS );

		$this->assertStringContainsString( '--pdp-container: 1360px', $css );
		$this->assertStringContainsString( '--pdp-pad: clamp(20px, 4vw, 40px)', $css );
		$this->assertStringContainsString( 'max-width: var(--pdp-container)', $css );
		$this->assertStringNotContainsString( 'calc(100% - 80px)', $css );
		$this->assertStringNotContainsString( 'calc(100% - 32px)', $css );
	}

	/**
	 * The document cards are a fluid grid: as many columns as the container
	 * holds, so the row can never be wider than its container (the fixed
	 * `repeat(2, 670px)` pair was what dug under the rail).
	 */
	public function test_the_document_grid_is_fluid(): void {
		$css = $this->css( self::PDP_CSS );

		$this->assertStringContainsString( 'repeat(auto-fit, minmax(300px, 1fr))', $css );
		$this->assertStringNotContainsString( '670px', $css );
	}

	/**
	 * The phone action bar is the floating glass pill: fixed, inset from the
	 * edges, blurred, with the safe-area inset under it — and the base rule
	 * that hides the bar sits before the phone block, so the pill is what
	 * shows at 390px.
	 */
	public function test_the_phone_action_bar_is_the_floating_pill(): void {
		$css = $this->css( self::PDP_CSS );

		$hidden = strpos( $css, "#tv-storefront-pdp .pdp-mobile-action {\n\tdisplay: none;\n}" );
		$phone  = strpos( $css, '@media (max-width: 860px)' );

		$this->assertNotFalse( $hidden );
		$this->assertNotFalse( $phone );
		$this->assertLessThan( $phone, $hidden );
		$this->assertStringContainsString( 'backdrop-filter: blur(20px) saturate(1.6)', $css );
		$this->assertStringContainsString( 'left: 12px;', $css );
		$this->assertStringContainsString( 'bottom: calc(12px + env(safe-area-inset-bottom))', $css );
	}
}
