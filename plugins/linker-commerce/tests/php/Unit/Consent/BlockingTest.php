<?php
/**
 * Tests for the consent path's Google half.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Consent;

use Linker\Commerce\Consent\Blocking;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Blocking.
 *
 * The class is the one piece of #201 that is code rather than data: the
 * carrier (Complianz + WP Consent API + Site Kit) does not reach Consent Mode
 * Basic on its own. These tests pin the three filter shapes and the cookie
 * cleanup's attachment; the browser-side behaviour they produce is measured in
 * docs/research/2026-10-16/consent-ga4-carrier.md and guarded by
 * tests/e2e/specs/consent.spec.ts and `just cutover verify`'s consent segment.
 *
 * @covers \Linker\Commerce\Consent\Blocking
 */
final class BlockingTest extends TestCase {

	/**
	 * Complianz's Site Kit integration whitelists the tag script and its
	 * inline config call; both have to leave the whitelist, or the blocker
	 * skips them and the tag runs before the visitor answered.
	 */
	public function test_the_tags_own_whitelist_entries_leave_the_whitelist(): void {
		$blocked = ( new Blocking() )->block_site_kit_tag(
			array( 'user_banner_id', 'google_gtagjs-js-after', 'google_gtagjs-js' )
		);

		$this->assertSame( array( 'user_banner_id', Blocking::CONSENT_DEFAULT_ID ), $blocked );
	}

	/**
	 * The consent defaults must run before the banner holds every Google
	 * purpose at denied; the whitelist matches by substring, so that snippet
	 * keeps its own exact entry and gains it exactly once on a re-run.
	 */
	public function test_the_consent_default_snippet_keeps_its_own_entry_exactly_once(): void {
		$blocked = ( new Blocking() )->block_site_kit_tag(
			array( Blocking::CONSENT_DEFAULT_ID, 'google_gtagjs-js' )
		);

		$this->assertSame( array( Blocking::CONSENT_DEFAULT_ID ), $blocked );
	}

	/**
	 * The whitelist is a filter: a value that is not a list (or holds
	 * non-strings) is normalized rather than passed on as-is.
	 */
	public function test_non_string_entries_are_dropped(): void {
		$blocked = ( new Blocking() )->block_site_kit_tag(
			array( 0, 'google_gtagjs-js', array( 'nested' ), 'kept' )
		);

		$this->assertSame( array( 'kept', Blocking::CONSENT_DEFAULT_ID ), $blocked );
	}

	/**
	 * Site Kit scopes its defaults to the European region list; outside it
	 * Google treats every purpose as granted. Every visitor of this site gets
	 * the denied defaults, so the region key goes and nothing else moves.
	 */
	public function test_every_visitor_gets_the_denied_defaults(): void {
		$defaults = ( new Blocking() )->deny_everywhere(
			array(
				'ad_storage'        => 'denied',
				'analytics_storage' => 'denied',
				'region'            => array( 'DE', 'AT' ),
				'wait_for_update'   => 500,
			)
		);

		$this->assertSame(
			array(
				'ad_storage'        => 'denied',
				'analytics_storage' => 'denied',
				'wait_for_update'   => 500,
			),
			$defaults
		);
	}

	/**
	 * The site has no Google advertising tag: the marketing answer grants
	 * Google nothing, and the statistics answer stays the one Google purpose.
	 */
	public function test_marketing_grants_google_nothing(): void {
		$map = ( new Blocking() )->statistics_only(
			array(
				'statistics' => array( 'analytics_storage' ),
				'marketing'  => array( 'ad_storage', 'ad_user_data', 'ad_personalization' ),
				'functional' => array( 'functionality_storage', 'security_storage' ),
			)
		);

		$this->assertSame(
			array(
				'statistics' => array( 'analytics_storage' ),
				'marketing'  => array(),
				'functional' => array( 'functionality_storage', 'security_storage' ),
			),
			$map
		);
	}

	/**
	 * The cookie cleanup rides WP Consent API's own script, so it runs
	 * wherever that script runs and nowhere else (Complianz free deletes only
	 * the cookies of its own cookie database, which this site leaves empty;
	 * GA4 does not delete its own cookies).
	 */
	public function test_the_cookie_cleanup_rides_the_consent_api_script(): void {
		WP_Mock::userFunction(
			'wp_script_is',
			array(
				'args'   => array( Blocking::CONSENT_API_HANDLE, 'enqueued' ),
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'wp_add_inline_script',
			array(
				'times' => 1,
				'args'  => array( Blocking::CONSENT_API_HANDLE, Blocking::CLEAR_ANALYTICS_COOKIES ),
			)
		);

		( new Blocking() )->add_cookie_cleanup();

		$this->assertConditionsMet();
	}

	/**
	 * Without that script the cleanup is not printed: it would have nothing to
	 * read the visitor's answer from.
	 */
	public function test_no_consent_api_script_no_cleanup(): void {
		WP_Mock::userFunction( 'wp_script_is', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_add_inline_script', array( 'times' => 0 ) );

		( new Blocking() )->add_cookie_cleanup();

		$this->assertConditionsMet();
	}
}
