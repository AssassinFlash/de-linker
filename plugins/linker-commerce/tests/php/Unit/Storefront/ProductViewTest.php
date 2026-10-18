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
	 * The German series label is the manufacturer's label with the German
	 * compound word (#264 M4): "ET Series" becomes "ET-Serie", the stored
	 * English phase word becomes the German one, and labels that carry no
	 * English suffix stay as they are.
	 */
	public function test_the_german_series_label_uses_serie_and_the_german_phase_word(): void {
		$this->assertSame( 'ET-Serie', ProductView::series_label( 'ET Series', true ) );
		$this->assertSame( 'ESA-Serie', ProductView::series_label( 'ESA Series', true ) );
		$this->assertSame( 'STS-Serie', ProductView::series_label( 'STS Series', true ) );
		$this->assertSame( 'EcoFlow OCEAN 2 (dreiphasig)', ProductView::series_label( 'EcoFlow OCEAN 2 (Three-Phase)', true ) );
		$this->assertSame( 'GoodWe BAT-C', ProductView::series_label( 'GoodWe BAT-C', true ) );
		$this->assertSame( 'ET-Serie', ProductView::series_label( 'ET-Serie', true ) );
	}

	/**
	 * The English page keeps the stored label byte for byte.
	 */
	public function test_the_english_series_label_is_unchanged(): void {
		$this->assertSame( 'ET Series', ProductView::series_label( 'ET Series', false ) );
		$this->assertSame( 'EcoFlow OCEAN 2 (Three-Phase)', ProductView::series_label( 'EcoFlow OCEAN 2 (Three-Phase)', false ) );
	}
}
