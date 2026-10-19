<?php
/**
 * Tests for the observable count of blocked registrations.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\BlockedRegistrations;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The ticket asks that a blocked registration is observable (#225): one
 * counter per reason, the last time and a hook a monitor can read.
 *
 * @covers \Linker\Commerce\Registration\BlockedRegistrations
 */
final class BlockedRegistrationsTest extends TestCase {

	/**
	 * The stored counts and the time of the last block.
	 */
	public function test_record_counts_each_reason_and_fires_the_hook(): void {
		$stored = false;
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION, array() ),
				'return' => static function () use ( &$stored ) {
					return $stored;
				},
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION, WP_Mock\Functions::type( 'array' ), false ),
				'return' => static function ( string $name, array $value ) use ( &$stored ): bool {
					$stored = $value;
					return true;
				},
			)
		);
		WP_Mock::expectAction( BlockedRegistrations::ACTION, 'honeypot' );
		WP_Mock::expectAction( BlockedRegistrations::ACTION, 'limit' );

		BlockedRegistrations::record( 'honeypot' );
		BlockedRegistrations::record( 'limit' );
		BlockedRegistrations::record( 'honeypot' );

		$counts = BlockedRegistrations::counts();
		$this->assertSame( 2, $counts['counts']['honeypot'] );
		$this->assertSame( 1, $counts['counts']['limit'] );
		$this->assertSame( 3, $counts['total'] );
		$this->assertNotSame( '', $counts['last'] );
	}

	/**
	 * No stored counts read as zero, and a reset removes them.
	 */
	public function test_counts_start_empty_and_reset_clears_the_option(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION, array() ),
				'return' => false,
			)
		);
		$counts = BlockedRegistrations::counts();
		$this->assertSame( array(), $counts['counts'] );
		$this->assertSame( 0, $counts['total'] );
		$this->assertSame( '', $counts['last'] );

		WP_Mock::userFunction(
			'delete_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION ),
				'return' => true,
			)
		);
		BlockedRegistrations::reset();
		$this->assertConditionsMet();
	}
}
