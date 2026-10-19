<?php
/**
 * Tests the Site Kit gaps without replacing either plugin's consent engine.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Consent;

use Linker\Commerce\Consent\BasicMode;
use Linker\Commerce\Tests\TestCase;

/**
 * Exercises the consent boundaries in the Site Kit adapter.
 *
 * @covers \Linker\Commerce\Consent\BasicMode
 */
final class BasicModeTest extends TestCase {

	/** Region-scoped defaults are unsafe for a worldwide opt-in banner. */
	public function test_first_visit_has_denied_defaults_without_a_region(): void {
		$defaults = ( new BasicMode() )->deny_everywhere(
			array(
				'region'            => array( 'DE' ),
				'analytics_storage' => 'granted',
				'wait_for_update'   => 500,
			)
		);
		$this->assertArrayNotHasKey( 'region', $defaults );
		foreach ( array( 'analytics_storage', 'ad_storage', 'ad_user_data', 'ad_personalization' ) as $key ) {
			$this->assertSame( 'denied', $defaults[ $key ] );
		}
		$this->assertSame( 500, $defaults['wait_for_update'] );
	}

	/** Local source attribution must never authorize Google advertising. */
	public function test_attribution_consent_does_not_authorize_ads(): void {
		$this->assertSame(
			array(
				'statistics' => array( 'analytics_storage' ),
				'functional' => array( 'security_storage' ),
			),
			( new BasicMode() )->without_ads(
				array(
					'statistics' => array( 'analytics_storage' ),
					'marketing'  => array( 'ad_storage', 'ad_user_data', 'ad_personalization' ),
					'functional' => array( 'security_storage' ),
				)
			)
		);
	}
}
