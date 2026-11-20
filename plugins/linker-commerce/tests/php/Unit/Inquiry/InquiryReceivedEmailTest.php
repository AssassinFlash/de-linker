<?php
/**
 * Tests for the inquiry confirmation email.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for InquiryReceivedEmail and, through it, the CustomerOrderEmail base.
 *
 * @covers \Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail
 * @covers \Linker\Commerce\Mail\CustomerOrderEmail
 */
final class InquiryReceivedEmailTest extends TestCase {

	/**
	 * The email of a test.
	 *
	 * @var InquiryReceivedEmail
	 */
	private InquiryReceivedEmail $email;

	/**
	 * The email listens for "pending → inquiry received".
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		$this->options( array() );
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED . '_notification', InquiryReceivedEmail::class, 'trigger', 10, 2 );
		$this->email = new InquiryReceivedEmail( '/plugin/linker-commerce.php' );
	}

	/**
	 * The confirmation goes to the billing address, in the inquiry's language.
	 */
	public function test_captures_in_the_inquiry_language(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_billing_email' )->andReturn( 'maria@example.test' );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_meta' )->with( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META )->andReturn( '' );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'de_DE_formal' );
		$this->allow_locale_switch( 'de_DE_formal' );
		// Capture renders after authorization; native Queue tests cover actual dispatch.
		WP_Mock::expectFilterAdded( 'pre_wp_mail', \Closure::class, 9, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_email_log_enabled', \Closure::class, 10, 3 );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_inquiry_received', 'maria@example.test' );

		$this->email->capture( $order );

		$this->assertTrue( $this->email->is_customer_email() );
		$this->assertSame( '20', $this->email->placeholders['{order_number}'] );
		$this->assertSame( 'Your inquiry #{order_number} has been received', $this->email->get_default_subject() );
		$this->assertConditionsMet();
	}

	/** Render the customer acknowledgement with Woo's brand header and footer. */
	private function receipt_html( WC_Order $order ): string {
		$email         = $this->email;
		$email_heading = $email->get_default_heading();
		WP_Mock::expectAction( 'woocommerce_email_header', $email_heading, $email );
		WP_Mock::expectAction( 'woocommerce_email_footer', $email );
		ob_start();
		require dirname( __DIR__, 4 ) . '/templates/emails/linker-inquiry-received.php';
		return (string) ob_get_clean();
	}

	/** Registered customers can view the inquiry in their account. */
	public function test_fixed_account_receipt_links_to_the_inquiry(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_customer_id' )->andReturn( 8 );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://site.test/account/view-order/20/' );
		$body = $this->receipt_html( $order );
		self::assertStringContainsString( 'https://site.test/account/view-order/20/', $body );
		self::assertStringContainsString( '#20', $body );
	}

	/** An accepted guest receives a fixed acknowledgement and the native link for their inquiry. */
	public function test_fixed_guest_receipt_contains_number_and_full_registration_link(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_customer_id' )->andReturn( 0 );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_order_key' )->andReturn( 'wc_order_complete_key' );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'en_US' );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 42 ) );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->shouldNotReceive( 'get_formatted_billing_full_name' );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://site.test/account/' ) );
		WP_Mock::userFunction( 'wc_get_endpoint_url', array( 'return' => 'https://site.test/account/register/' ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) )
		);

		$body = $this->receipt_html( $order );

		self::assertStringContainsString( '#20', $body );
		self::assertStringContainsString( 'one business day', $body );
		self::assertStringContainsString( 'https://site.test/account/register/?linker_inquiry=20&linker_key=wc_order_complete_key', html_entity_decode( $body ) );
		self::assertSame( 1, substr_count( $body, 'href=' ) );
	}

	/**
	 * Without an order nothing is sent (WP_Mock's strict mode would fail on the send action).
	 */
	public function test_without_order(): void {
		WP_Mock::userFunction(
			'wc_get_order',
			array(
				'times'  => 1,
				'return' => false,
			)
		);

		$this->email->trigger( 99 );

		$this->assertConditionsMet();
	}
}
