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
use Mockery;
use WP_Mock;

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

	/**
	 * The known handle is parser-inert until CookieYes releases it after consent.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_google_gtagjs_is_held_before_consent(): void {
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- CookieYes defines CLI_VERSION.
		define( 'CLI_VERSION', '3.5.7' );

		$held = ( new BasicMode() )->hold_google_tag( $this->google_tag( 'google_gtagjs' ), 'google_gtagjs' );

		$this->assertStringContainsString( 'type="text/plain"', $held );
		$this->assertStringContainsString( 'data-cookieyes="cookieyes-analytics"', $held );
		$this->assertStringContainsString( 'googletagmanager.com/gtag/js', $held );
	}

	/**
	 * A Site Kit rename still cannot start a request; the fallback is logged.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_a_renamed_google_handle_is_held_and_reported(): void {
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- CookieYes defines CLI_VERSION.
		define( 'CLI_VERSION', '3.5.7' );
		$this->expect_warning( static fn ( string $message ): bool => str_contains( $message, 'gtag-renamed' ) && str_contains( $message, 'google_gtagjs' ) );

		$held = ( new BasicMode() )->hold_google_tag( $this->google_tag( 'gtag-renamed' ), 'gtag-renamed' );

		$this->assertStringContainsString( 'type="text/plain"', $held );
		$this->assertStringContainsString( 'data-cookieyes="cookieyes-analytics"', $held );
	}

	/**
	 * An unrelated script is not the measurement tag.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_another_handle_is_left_alone(): void {
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- CookieYes defines CLI_VERSION.
		define( 'CLI_VERSION', '3.5.7' );
		$tag = '<script src="https://de-linker.com/theme.js" id="theme-js"></script>'; // phpcs:ignore WordPress.WP.EnqueuedResources.NonEnqueuedScript -- markup under test, not a page enqueue.

		$this->assertSame( $tag, ( new BasicMode() )->hold_google_tag( $tag, 'theme' ) );
	}

	/**
	 * CookieYes inactive means nothing can release a held tag, so the tag is
	 * unchanged and the gap is logged. Deploy verify then fails closed.
	 */
	public function test_inactive_cookieyes_does_not_hold_and_alerts(): void {
		$this->assertFalse( defined( 'CLI_VERSION' ) );
		$this->expect_warning( static fn ( string $message ): bool => str_contains( $message, 'CLI_VERSION' ) );
		$tag = $this->google_tag( 'google_gtagjs' );

		$this->assertSame( $tag, ( new BasicMode() )->hold_google_tag( $tag, 'google_gtagjs' ) );
	}

	/**
	 * Expects one WooCommerce warning whose text identifies the gap.
	 *
	 * @param \Closure $matches Selects the warning text.
	 */
	private function expect_warning( \Closure $matches ): void {
		$logger = Mockery::mock();
		$logger->expects( 'warning' )->once()->with(
			Mockery::on( $matches ),
			array( 'source' => BasicMode::LOG_SOURCE )
		);
		WP_Mock::userFunction( 'wc_get_logger', array( 'return' => $logger ) );
	}

	/**
	 * A Site Kit tag for one handle.
	 *
	 * @param string $handle Script handle.
	 */
	private function google_tag( string $handle ): string {
		// phpcs:ignore WordPress.WP.EnqueuedResources.NonEnqueuedScript -- markup under test, not a page enqueue.
		return '<script src="https://www.googletagmanager.com/gtag/js?id=G-TEST" id="' . $handle . '-js"></script>';
	}
}
