<?php
/**
 * Tests for the product view's scenario reader.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The application scenarios (#16 GAP-2): both record shapes of the legacy
 * ACF JSON parse, rows without a title are skipped.
 *
 * @covers \Linker\Commerce\Storefront\ProductView::scenarios
 */
final class ProductViewTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * The rich shape (situation, fit, verdict, checklist, image) and the
	 * plain shape (body, link) come back with the fields they carry.
	 */
	public function test_scenarios_parse_both_record_shapes(): void {
		$legacy = array(
			'application_scenarios' => array(
				array(
					'scenario_kind'      => 'application',
					'scenario_title'     => 'A larger storage step',
					'scenario_situation' => 'The project needs four modules of storage.',
					'scenario_fit'       => '<p>The assembled tower measures 600 × 935 mm.</p>',
					'scenario_verdict'   => 'Our engineers plan it where the footprint allows 935 mm.',
					'scenario_checklist' => array(
						array( 'check_text' => 'Floor carries 201 kg' ),
						array( 'check_text' => '  ' ),
						'A plain string row',
					),
					'scenario_image'     => 4818,
				),
				array(
					'scenario_title' => 'Backup autonomy sizing',
					'scenario_body'  => 'Size outage coverage in 10.65 kWh steps.',
					'scenario_image' => 0,
					'scenario_link'  => array(
						'url'    => 'https://de-linker.com/product-category/battery-storage/',
						'target' => '_self',
					),
				),
				array( 'scenario_kind' => 'broken — no title' ),
			),
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): string => '_tv_legacy_acf_json' === $key
					? (string) json_encode( $legacy )
					: '',
			)
		);

		$scenarios = ( new ProductView( new CommerceState() ) )->scenarios( 1178 );

		$this->assertCount( 2, $scenarios );
		$this->assertSame( 'A larger storage step', $scenarios[0]['title'] );
		$this->assertSame( 'The project needs four modules of storage.', $scenarios[0]['situation'] );
		$this->assertSame( '<p>The assembled tower measures 600 × 935 mm.</p>', $scenarios[0]['fit'] );
		$this->assertSame( array( 'Floor carries 201 kg', 'A plain string row' ), $scenarios[0]['checklist'] );
		$this->assertSame( 4818, $scenarios[0]['image'] );
		$this->assertSame( '', $scenarios[0]['url'] );
		$this->assertSame( 'Backup autonomy sizing', $scenarios[1]['title'] );
		$this->assertSame( 'Size outage coverage in 10.65 kWh steps.', $scenarios[1]['situation'] );
		$this->assertSame( '', $scenarios[1]['fit'] );
		$this->assertSame( 'https://de-linker.com/product-category/battery-storage/', $scenarios[1]['url'] );
	}

	/**
	 * A product without the branch answers an empty list.
	 */
	public function test_scenarios_are_empty_without_the_branch(): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => '',
			)
		);

		$this->assertSame( array(), ( new ProductView( new CommerceState() ) )->scenarios( 6521 ) );
	}

	/**
	 * The "Ask about this product" button opens the contact page of the
	 * product page's language, so the contact form's receipt speaks it too
	 * (AUDIT.md H1).
	 */
	public function test_ask_url_opens_the_contact_page_of_the_current_language(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'pll_home_url',
			array(
				'args'   => array( 'de' ),
				'return' => 'http://linker.test/de/',
			)
		);
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'contact' ),
				'return' => new \WP_Post( (object) array( 'ID' => 33 ) ),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 33, 'de' ),
				'return' => 58,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 58 ),
				'return' => 'http://linker.test/de/kontakt/',
			)
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static function ( array $args, string $url ): string {
					return $url . '?' . http_build_query( $args );
				},
			)
		);
		WP_Mock::userFunction( 'esc_url_raw', array( 'return' => static fn( string $url ): string => $url ) );
		$product = \Mockery::mock( \WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 7 );
		$product->allows( 'get_name' )->andReturn( 'GoodWe GW10K-ET' );
		$product->allows( 'get_permalink' )->andReturn( 'http://linker.test/de/produkt/goodwe-gw10k-et/' );

		$view   = new ProductView( new CommerceState() );
		$method = new \ReflectionMethod( ProductView::class, 'ask_url' );
		$url    = $method->invoke( $view, $product );

		$this->assertStringStartsWith( 'http://linker.test/de/kontakt/?', $url );
		$this->assertStringContainsString( 'intent=product', $url );
		$this->assertStringContainsString( 'product_id=7', $url );
	}
}
