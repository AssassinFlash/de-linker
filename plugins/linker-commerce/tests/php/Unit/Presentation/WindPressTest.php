<?php
/**
 * Tests for the WindPress scan provider.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\WindPress;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for WindPress.
 *
 * @covers \Linker\Commerce\Presentation\WindPress
 */
final class WindPressTest extends TestCase {

	/**
	 * The plugin registers on the official compile.providers filter, and on
	 * LiveCanvas's own render filter (the dynamic templates are scanned as
	 * source, see render_raw()).
	 */
	public function test_register_adds_the_provider(): void {
		$windpress = new WindPress();
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/integration/livecanvas/compile:get_contents.render', array( $windpress, 'render_raw' ), 10, 2 );

		$windpress->register();

		$this->assertConditionsMet();
	}

	/**
	 * A dynamic template is scanned as its own source: rendering it in the
	 * scan request would put the WooCommerce template tags' markup
	 * (`<h2>Additional information</h2>`) in front of the scan answer's JSON,
	 * and the cache builder stops on an answer it cannot parse. Everything
	 * else keeps the provider's own decision.
	 */
	public function test_render_raw_skips_the_dynamic_templates(): void {
		$windpress = new WindPress();
		$template  = new \WP_Post(
			(object) array(
				'ID'        => 6933,
				'post_type' => 'lc_dynamic_template',
			)
		);
		$page      = new \WP_Post(
			(object) array(
				'ID'        => 932,
				'post_type' => 'page',
			)
		);

		$this->assertFalse( $windpress->render_raw( true, $template ) );
		$this->assertTrue( $windpress->render_raw( true, $page ) );
		$this->assertFalse( $windpress->render_raw( false, $page ) );
		$this->assertTrue( $windpress->render_raw( true, 'not a post' ) );
	}

	/**
	 * The provider is enabled and points at this plugin's scanner.
	 */
	public function test_providers_appends_linker_commerce(): void {
		$windpress = new WindPress();
		$providers = $windpress->providers( array() );

		$this->assertSame( 'linker-commerce', $providers[0]['id'] );
		$this->assertSame( array( $windpress, 'scan' ), $providers[0]['callback'] );
		$this->assertTrue( $providers[0]['enabled'] );
	}

	/**
	 * The scanner returns the LiveCanvas templates and the PHP that prints Tailwind classes.
	 */
	public function test_scan_includes_templates_and_php(): void {
		$contents = ( new WindPress() )->scan();
		$names    = array_column( $contents, 'name' );

		$this->assertContains( 'livecanvas/checkout_page.html', $names );
		$this->assertContains( 'livecanvas/single_product.html', $names );
		// The PHP half enters the scan surface by name, so its classes compile.
		$this->assertContains( 'includes/Presentation/Shortcodes.php', $names );
		$this->assertContains( 'includes/Presentation/LoginGate.php', $names );
		$this->assertNotSame( array(), $contents );
		foreach ( $contents as $file ) {
			$this->assertArrayHasKey( 'name', $file );
			$this->assertArrayHasKey( 'content', $file );
			$this->assertNotSame( '', $file['content'] );
		}
	}
}
