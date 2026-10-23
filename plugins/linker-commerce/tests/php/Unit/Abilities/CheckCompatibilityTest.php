<?php
/**
 * Tests for linker/check-compatibility.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\CheckCompatibility;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Three-valued pairing against data/compatibility.json.
 *
 * @covers \Linker\Commerce\Abilities\CheckCompatibility
 */
final class CheckCompatibilityTest extends TestCase {

	use MocksLiveProducts;

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
	}

	/**
	 * OPTIONS can show the four-value verdict, including unknown.
	 */
	public function test_output_schema_has_the_four_verdicts(): void {
		$schema = ( new CheckCompatibility( $this->publication_data() ) )->args()['output_schema'];

		$this->assertSame(
			array( 'released', 'released_with_accessory', 'not_released', 'unknown' ),
			$schema['properties']['verdict']['enum']
		);
		$this->assertTrue( ( new CheckCompatibility( $this->publication_data() ) )->can_execute() );
	}

	/**
	 * A documented pair of product IDs returns the contract's verdict.
	 *
	 * @dataProvider documented_pairs
	 *
	 * @param int    $inverter Inverter product ID.
	 * @param int    $battery  Battery product ID.
	 * @param string $verdict  Expected verdict.
	 */
	public function test_documented_pairs( int $inverter, int $battery, string $verdict ): void {
		$this->mock_live_products( array( $inverter, $battery ) );
		$ability = new CheckCompatibility( $this->publication_data() );

		$named   = $ability->execute(
			array(
				'inverter_id' => $inverter,
				'battery_id'  => $battery,
			)
		);
		$swapped = $ability->execute( array( 'product_ids' => array( $battery, $inverter ) ) );

		$this->assertSame( $verdict, $named['verdict'] );
		$this->assertSame( $verdict, $swapped['verdict'] );
		if ( 'unknown' !== $verdict ) {
			$this->assertNotSame( array(), $named['documents'] );
			$this->assertNotSame( array(), $named['conditions'] );
		}
	}

	/**
	 * Known product pairs: released and not_released.
	 *
	 * @return list<array{int, int, string}>
	 */
	public function documented_pairs(): array {
		return array(
			array( 3556, 6519, 'released' ),
			// The one-module B2-5.0 runs below the H2 battery window (#481).
			array( 4107, 1832, 'not_released' ),
			array( 1182, 6519, 'not_released' ),
		);
	}

	/**
	 * Missing IDs, or two inverters, are unknown: the contract does not infer.
	 */
	public function test_unknown_when_the_contract_has_no_pair(): void {
		$this->assertSame( 'unknown', ( new CheckCompatibility( $this->publication_data() ) )->execute( array() )['verdict'] );
		$this->mock_live_products( array( 4107, 3556 ) );
		$two_inverters = ( new CheckCompatibility( $this->publication_data() ) )->execute( array( 'product_ids' => array( 4107, 3556 ) ) );
		$this->assertSame( 'unknown', $two_inverters['verdict'] );
		$this->assertSame( array(), $two_inverters['documents'] );
	}
}
