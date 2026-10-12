<?php
/**
 * Tests for the product page's condition functions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Tests\TestCase;
use WP_Mock;

require_once dirname( __DIR__, 4 ) . '/includes/Presentation/template-functions.php';

/**
 * The `#fit` gate the product template and the nav's Applications link both
 * read: a scenario with a checklist. Measured against the live pages
 * 2026-10-13: the GW60K-STS-G10 carries a checklist and no scene image and the
 * live page renders the section, while a scenario with only a scene image is
 * the live page's other variant, which this tree's scenes shortcode does not
 * render.
 *
 * @covers ::linker_commerce_pdp_has_scenes
 */
final class TemplateFunctionsTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * The page's product leaves the global after the test.
	 */
	public function tearDown(): void {
		unset( $GLOBALS['product'] );
		parent::tearDown();
	}

	/**
	 * A checklist without a scene image still opens the section and the nav
	 * link — the GW60K case, whose live page renders "Where this model fits."
	 * with no image in it.
	 */
	public function test_a_checklist_scenario_opens_the_fit_section_without_a_scene_image(): void {
		$this->product_with_scenarios(
			array(
				array(
					'scenario_kind'      => 'application',
					'scenario_title'     => 'Backup switching on an ESA system up to 60 kW',
					'scenario_checklist' => array( 'One hybrid inverter, ≤ 60 kVA on the grid side.' ),
					'scenario_image'     => 0,
				),
			)
		);

		$this->assertTrue( linker_commerce_pdp_has_scenes() );
	}

	/**
	 * A scene image with no checklist is the live page's "Product views and
	 * project settings." variant; the scenes shortcode renders the project-fit
	 * variant, so the section stays closed instead of printing markup it
	 * cannot fill.
	 */
	public function test_a_scene_image_alone_does_not_open_the_fit_section(): void {
		$this->product_with_scenarios(
			array(
				array(
					'scenario_title'     => 'Residential PV storage systems with up to 7500 Wp of PV',
					'scenario_checklist' => array(),
					'scenario_image'     => 4748,
				),
			)
		);

		$this->assertFalse( linker_commerce_pdp_has_scenes() );
	}

	/**
	 * No scenario at all: no section and no nav link, as the live page of the
	 * ESA power modules renders none.
	 */
	public function test_a_product_without_scenarios_stays_closed(): void {
		$this->product_with_scenarios( array() );

		$this->assertFalse( linker_commerce_pdp_has_scenes() );
	}

	/**
	 * A checklist whose only row is blank parses to an empty list (the parser
	 * trims rows), so it does not open the section.
	 */
	public function test_a_blank_checklist_does_not_open_the_fit_section(): void {
		$this->product_with_scenarios(
			array(
				array(
					'scenario_title'     => 'A scenario with no limits written down',
					'scenario_checklist' => array( array( 'check_text' => '   ' ) ),
				),
			)
		);

		$this->assertFalse( linker_commerce_pdp_has_scenes() );
	}

	/**
	 * The page's product and its scenario records.
	 *
	 * @param list<array<string, mixed>> $scenarios The `application_scenarios` branch.
	 */
	private function product_with_scenarios( array $scenarios ): void {
		$product = \Mockery::mock( \WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 6530 );
		$GLOBALS['product'] = $product; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- WooCommerce's global.
		$legacy             = array( 'application_scenarios' => $scenarios );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): string => '_tv_legacy_acf_json' === $key
					? (string) json_encode( $legacy )
					: '',
			)
		);
	}
}
