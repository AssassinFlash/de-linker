<?php
/**
 * Tests that a maintained condition stays beside the value it limits.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Materials;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use ReflectionProperty;
use WC_Product;
use WP_Mock;

/**
 * The GoodWe BAT-C user manual states its rated charge/discharge current and
 * power for Australia only (note 2, pdf p. 83) and says its certification
 * list is not exhaustive (note 5). A row that prints "100 / 100 A" or the
 * standard list without those conditions reads as an unconditional European
 * rating, so the qualifier travels with any vocabulary key, not only `temp`.
 *
 * @covers \Linker\Commerce\Products\Materials::spec_text
 * @covers \Linker\Commerce\Products\Materials::specs
 */
final class MaterialsQualifierTest extends TestCase {

	/**
	 * Restores the registry statics after each test.
	 */
	public function tearDown(): void {
		$this->seed_registry( null );
		parent::tearDown();
	}

	/**
	 * The labels read the vocabulary arrays; translation returns its input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_the_terms', array( 'return' => false ) );
	}

	/**
	 * A rated row's condition reaches the customer, and the maximum rating
	 * beside it stays unqualified.
	 */
	public function test_a_rated_row_carries_its_condition(): void {
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => fn ( int $id ) => $this->product( $id ),
			)
		);
		$this->seed_registry(
			array(
				'mat_test_bat_rated' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9101 ) ),
					'identity'    => array(
						'kind'         => 'battery_system',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-TEST-BAT',
					),
					'material_id' => 'mat_test_bat_rated',
					'technical'   => array(
						'specifications' => array(
							'max_charge_current_a' => array(
								'value' => '180',
								'unit'  => 'A',
							),
							'rated_charge_discharge_current_a' => array(
								'value'     => '100 / 100',
								'unit'      => 'A',
								'qualifier' => array(
									'en' => 'Rated value; Australia only, manual note 2.',
									'de' => 'Nennwert; nur für Australien, Handbuch Anmerkung 2.',
								),
							),
						),
					),
				),
			),
		);

		$english = Materials::specs( $this->product( 9101 ) );

		$this->assertSame( '100 / 100 A (Rated value; Australia only, manual note 2.)', $english['rated_charge_discharge_current_a']['value'] );
		$this->assertSame( '180 A', $english['charge_a']['value'], 'An unqualified maximum keeps its own row.' );
	}

	/**
	 * A qualifier never becomes the row's label, so the vocabulary stays the
	 * only naming authority.
	 */
	public function test_a_condition_never_replaces_the_row_label(): void {
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => fn ( int $id ) => $this->product( $id ),
			)
		);
		$this->seed_registry(
			array(
				'mat_test_bat_label' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9102 ) ),
					'identity'    => array(
						'kind'         => 'battery_system',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-TEST-LABEL',
					),
					'material_id' => 'mat_test_bat_label',
					'technical'   => array(
						'specifications' => array(
							'certification' => array(
								'value'     => 'IEC62619 / UN38.3',
								'unit'      => null,
								'qualifier' => array(
									'en' => 'Not all standards are listed; see the manufacturer website.',
									'de' => 'Nicht alle Normen sind aufgeführt; siehe Herstellerwebsite.',
								),
							),
						),
					),
				),
			),
		);

		$row = Materials::specs( $this->product( 9102 ) )['certification'];

		$this->assertSame( 'Certification', $row['label'] );
		$this->assertSame( 'IEC62619 / UN38.3 (Not all standards are listed; see the manufacturer website.)', $row['value'] );
	}

	/**
	 * The EMC row the manual prints beside the safety list reaches a customer
	 * under its own vocabulary label, unqualified: the standards the manual
	 * prints for it carry no condition of their own.
	 */
	public function test_the_emc_row_is_its_own_labelled_row(): void {
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => fn ( int $id ) => $this->product( $id ),
			)
		);
		$this->seed_registry(
			array(
				'mat_test_bat_emc' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9104 ) ),
					'identity'    => array(
						'kind'         => 'battery_system',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-TEST-EMC',
					),
					'material_id' => 'mat_test_bat_emc',
					'technical'   => array(
						'specifications' => array(
							'emc' => array(
								'value'    => 'IEC/EN 61000-6-1/2/3/4',
								'value_de' => 'IEC/EN 61000-6-1/2/3/4',
								'unit'     => null,
							),
						),
					),
				),
			),
		);

		$row = Materials::specs( $this->product( 9104 ) )['emc'];

		$this->assertSame( 'EMC', $row['label'] );
		$this->assertSame( 'IEC/EN 61000-6-1/2/3/4', $row['value'] );
	}

	/**
	 * A key outside the reviewed set keeps its row exactly as before, so the
	 * condition cannot silently reshape other products' visible specs.
	 */
	public function test_a_key_outside_the_reviewed_set_is_unchanged(): void {
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => fn ( int $id ) => $this->product( $id ),
			)
		);
		$this->seed_registry(
			array(
				'mat_test_bat_other' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9103 ) ),
					'identity'    => array(
						'kind'         => 'battery_system',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-TEST-OTHER',
					),
					'material_id' => 'mat_test_bat_other',
					'technical'   => array(
						'specifications' => array(
							'cycle_life' => array(
								'value'     => '6000',
								'unit'      => 'cycles',
								'qualifier' => array( 'en' => 'At 25 °C.' ),
							),
						),
					),
				),
			),
		);

		$this->assertSame( '6000 cycles', Materials::specs( $this->product( 9103 ) )['cycles']['value'] );
	}

	/**
	 * The shipped BAT-C rows carry the manual's own conditions: the rating is
	 * Australia-only (note 2, p. 83) and the certification list is explicitly
	 * partial (note 5). Data-level, so a later edit cannot quietly drop them.
	 */
	public function test_the_shipped_bat_c_rows_keep_their_page_citations_and_conditions(): void {
		$registry = Materials::registry();
		foreach ( array( 'mat_goodwe_gw61_4_bat_ac_g10', 'mat_goodwe_gw112_6_bat_ac_g10' ) as $material_id ) {
			$specs = $registry['materials'][ $material_id ]['technical']['specifications'];
			foreach ( array( 'rated_charge_discharge_current_a', 'rated_charge_discharge_power_kw' ) as $field ) {
				$this->assertSame( 'GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf', $specs[ $field ]['citation']['doc'] );
				$this->assertSame( 81, $specs[ $field ]['citation']['page'] );
				$this->assertStringContainsString( 'Australia', $specs[ $field ]['qualifier']['en'] );
				$this->assertStringContainsString( 'Australien', $specs[ $field ]['qualifier']['de'] );
			}
			$this->assertSame( 82, $specs['certification']['citation']['page'] );
			$this->assertStringContainsString( 'VDE2510', $specs['certification']['value'] );
			$this->assertStringContainsString( 'N140', $specs['certification']['value'] );
			$this->assertStringNotContainsString( 'N143', $specs['certification']['value'] );
			// The manual prints the certification block as two rows; the page
			// shows both, so the EMC row is the same fact at the same page.
			$this->assertSame( 82, $specs['emc']['citation']['page'] );
			$this->assertSame( 'IEC/EN 61000-6-1/2/3/4', $specs['emc']['value'] );
			$this->assertSame( $specs['emc']['value'], $specs['emc']['value_de'] );
		}
	}

	/**
	 * A minimal product whose identity the registry binding resolves.
	 *
	 * @param int $id The product ID.
	 */
	private function product( int $id ): WC_Product {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( $id );
		return $product;
	}

	/**
	 * Seeds (or clears) the registry statics. Reflection reads and writes
	 * non-public properties as of PHP 8.1 without setAccessible().
	 *
	 * @param array<string, mixed>|null $materials The registry's materials, null to reset.
	 */
	private function seed_registry( ?array $materials ): void {
		$registry = new ReflectionProperty( Materials::class, 'registry' );
		$registry->setValue( null, null === $materials ? null : array( 'materials' => $materials ) );
		$index = new ReflectionProperty( Materials::class, 'product_index' );
		$index->setValue( null, null );
	}
}
