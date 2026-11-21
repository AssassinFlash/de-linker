<?php
/**
 * Customer submission allowances.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\BusinessPolicy;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/** @covers \Linker\Commerce\Protection\BusinessPolicy */
final class BusinessPolicyTest extends TestCase {

	/** Unrelated customers do not consume each other's allowance. */
	public function test_inquiry_does_not_reserve_a_shared_site_quota(): void {
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'fixture' ) );
		$limits = ( new BusinessPolicy() )->limits( array(), 'inquiry', new Identity( 'browser', '' ) );
		$names  = array_column( $limits, 'name' );

		$this->assertNotContains( 'business_site_ordinary_hour', $names );
		$this->assertNotContains( 'business_site_ordinary_day', $names );
		$this->assertContains( 'business_browser_hour', $names );
	}
}
