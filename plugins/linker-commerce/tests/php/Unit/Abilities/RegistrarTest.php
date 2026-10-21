<?php
/**
 * Tests for the ability registration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\CheckCompatibility;
use Linker\Commerce\Abilities\CompareProducts;
use Linker\Commerce\Abilities\GetCommerceVersion;
use Linker\Commerce\Abilities\GetProduct;
use Linker\Commerce\Abilities\HandoffTeam;
use Linker\Commerce\Abilities\InquiryStatus;
use Linker\Commerce\Abilities\ReadSolution;
use Linker\Commerce\Abilities\Registrar;
use Linker\Commerce\Abilities\SearchProducts;
use Linker\Commerce\Abilities\SizeHint;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Registrar.
 *
 * @covers \Linker\Commerce\Abilities\Registrar
 */
final class RegistrarTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * The eight Genie abilities plus the version probe, in registration order.
	 *
	 * @return list<string>
	 */
	private const NAMES = array(
		GetCommerceVersion::NAME,
		SearchProducts::NAME,
		GetProduct::NAME,
		CompareProducts::NAME,
		CheckCompatibility::NAME,
		SizeHint::NAME,
		InquiryStatus::NAME,
		ReadSolution::NAME,
		HandoffTeam::NAME,
	);

	/**
	 * The category carries a label and a description.
	 */
	public function test_registers_the_category(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'wp_register_ability_category',
			array(
				'times' => 1,
				'args'  => array(
					'linker',
					array(
						'label'       => 'Linker',
						'description' => 'Products and inquiries of de-linker.com.',
					),
				),
			)
		);

		( new Registrar( self::FILE ) )->register_category();

		$this->assertConditionsMet();
	}

	/**
	 * Each ability is registered with its own arguments, inside the category.
	 * Write actions are not abilities.
	 */
	public function test_registers_each_ability_in_the_category(): void {
		WP_Mock::passthruFunction( '__' );
		$registrar = new Registrar( self::FILE );
		$this->assertSame( self::NAMES, array_keys( $registrar->abilities() ) );
		foreach ( $registrar->abilities() as $ability ) {
			$args = $ability->args();
			$this->assertArrayHasKey( 'output_schema', $args );
			$this->assertTrue( $args['meta']['show_in_rest'] );
			$this->assertTrue( $args['meta']['annotations']['readonly'] );
		}
		WP_Mock::userFunction(
			'wp_register_ability',
			array(
				'times' => count( self::NAMES ),
				'args'  => array(
					Mockery::type( 'string' ),
					Mockery::on(
						static fn ( array $args ): bool => Registrar::CATEGORY === ( $args['category'] ?? null )
							&& isset( $args['output_schema'] )
					),
				),
			)
		);

		$registrar->register_abilities();

		$this->assertConditionsMet();
	}

	/**
	 * Without the Abilities API nothing is registered and nothing fails.
	 *
	 * Runs in its own process, where no test has defined the API functions yet.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_skips_registration_without_the_abilities_api(): void {
		$registrar = new Registrar( self::FILE );
		$registrar->register_category();
		$registrar->register_abilities();

		$this->assertFalse( function_exists( 'wp_register_ability_category' ) );
		$this->assertFalse( function_exists( 'wp_register_ability' ) );
	}
}
