<?php
/**
 * Public inquiry attribution at the marketing consent boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\OrderAttribution;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Campaign values on a new public inquiry.
 *
 * @covers \Linker\Commerce\Inquiry\OrderAttribution
 */
final class OrderAttributionTest extends TestCase {

	/** A stale allow from the WP bridge cannot override a withdrawn CookieYes choice. */
	public function test_withdrawal_ignores_posted_campaign_and_tracking_cookies(): void {
		$_COOKIE['cookieyes-consent']              = 'consent:yes,advertisement:no';
		$_COOKIE['wp_consent_marketing']           = 'allow';
		$_COOKIE['sbjs_current']                   = 'typ=utm|||src=linkedin';
		$_POST['wc_order_attribution_source_type'] = 'utm';
		$_POST['wc_order_attribution_utm_source']  = 'linkedin';
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction( 'wp_has_consent', array( 'return' => true ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_meta_data' )->andReturn( array( (object) array( 'key' => '_wc_order_attribution_source_type' ), (object) array( 'key' => '_linker_inquiry_source' ) ) );
		$order->expects( 'delete_meta_data' )->with( '_wc_order_attribution_source_type' );
		$order->shouldNotReceive( 'update_meta_data' );
		try {
			OrderAttribution::apply_to_order( $order );
			$this->assertFalse( OrderAttribution::tracking_allowed() );
		} finally {
			unset( $_COOKIE['cookieyes-consent'], $_COOKIE['wp_consent_marketing'], $_COOKIE['sbjs_current'], $_POST['wc_order_attribution_source_type'], $_POST['wc_order_attribution_utm_source'] );
		}
	}

	/** Browser form fields take precedence over an older campaign in the same browser. */
	public function test_form_source_and_public_paths_without_private_query_values(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Restore the isolated test request.
		$post    = $_POST;
		$cookies = $_COOKIE;
		try {
			$_COOKIE = array(
				'wp_consent_marketing' => 'allow',
				'sbjs_current'         => 'typ=referral|||src=old',
			);
			$_POST   = array(
				'wc_order_attribution_utm_source'    => 'linkedin',
				'wc_order_attribution_utm_medium'    => 'social',
				'wc_order_attribution_utm_campaign'  => 'ci_case_01',
				'wc_order_attribution_session_entry' => 'https://example.org/my-account/lost-password/?key=private&login=private',
				'wc_order_attribution_referrer'      => 'https://example.org/?s=private#private',
				'wc_order_attribution_other'         => 'unused',
			);
			$meta    = $this->recorded();
			$this->assertSame( 'utm', $meta['source_type'] );
			$this->assertSame( 'linkedin', $meta['utm_source'] );
			$this->assertSame( 'social', $meta['utm_medium'] );
			$this->assertSame( 'ci_case_01', $meta['utm_campaign'] );
			$this->assertSame( 'https://example.org/my-account/lost-password/', $meta['session_entry'] );
			$this->assertSame( 'https://example.org/', $meta['referrer'] );
			$this->assertArrayNotHasKey( 'other', $meta );
		} finally {
			$_POST   = $post;
			$_COOKIE = $cookies;
		}
	}

	/** The CookieYes choice and first-party Sourcebuster cookies accompany Genie JSON requests. */
	public function test_genie_uses_the_current_first_party_campaign_and_session(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Restore the isolated test request.
		$post    = $_POST;
		$cookies = $_COOKIE;
		try {
			$_POST   = array();
			$_COOKIE = array(
				'cookieyes-consent' => 'consent:yes,advertisement:yes',
				'sbjs_current'      => 'typ=utm|||src=linkedin|||mdm=social|||cmp=ci_case_01|||cnt=(none)',
				'sbjs_current_add'  => 'ep=https://example.org/about/?utm_source=linkedin|||rf=https://www.linkedin.com/feed/',
				'sbjs_session'      => 'pgs=2',
				'sbjs_udata'        => 'vst=1',
			);
			$meta    = $this->recorded();
			$this->assertSame( 'utm', $meta['source_type'] );
			$this->assertSame( 'linkedin', $meta['utm_source'] );
			$this->assertSame( 'social', $meta['utm_medium'] );
			$this->assertSame( '2', $meta['session_pages'] );
			$this->assertSame( '1', $meta['session_count'] );
			$this->assertSame( 'https://example.org/about/', $meta['session_entry'] );
			$this->assertSame( 'https://www.linkedin.com/feed/', $meta['referrer'] );
			$this->assertArrayNotHasKey( 'utm_content', $meta );
			$_COOKIE['wp_consent_marketing'] = 'deny';
			$this->assertFalse( OrderAttribution::tracking_allowed() );
		} finally {
			$_POST   = $post;
			$_COOKIE = $cookies;
		}
	}

	/**
	 * Observe what a new Woo inquiry receives.
	 *
	 * @return array<string,string>
	 */
	private function recorded(): array {
		$meta = array();
		WP_Mock::userFunction(
			'wp_has_consent',
			array(
				'args'   => array( 'marketing' ),
				'return' => true,
			)
		);
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::passthruFunction( 'esc_url_raw' );
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn ( $url ) => parse_url( $url ) ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_meta_data' )->andReturn( array() );
		$order->allows( 'update_meta_data' )->andReturnUsing(
			static function ( $key, $value ) use ( &$meta ): void {
				$meta[ substr( $key, strlen( '_wc_order_attribution_' ) ) ] = $value;
			}
		);
		OrderAttribution::apply_to_order( $order );
		return $meta;
	}
}
