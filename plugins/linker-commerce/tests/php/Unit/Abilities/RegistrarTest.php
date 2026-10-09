<?php
/**
 * Tests for the ability registration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\GetCommerceVersion;
use Linker\Commerce\Abilities\Registrar;
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
	 */
	public function test_registers_each_ability_in_the_category(): void {
		WP_Mock::passthruFunction( '__' );
		$expected = array( 'category' => Registrar::CATEGORY ) + ( new GetCommerceVersion( self::FILE ) )->args();
		WP_Mock::userFunction(
			'wp_register_ability',
			array(
				'times' => 1,
				'args'  => array(
					GetCommerceVersion::NAME,
					Mockery::on(
						static fn ( array $args ): bool => $args == $expected // phpcs:ignore Universal.Operators.StrictComparisons.LooseEqual -- the callbacks belong to another, equal instance.
					),
				),
			)
		);

		( new Registrar( self::FILE ) )->register_abilities();

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
