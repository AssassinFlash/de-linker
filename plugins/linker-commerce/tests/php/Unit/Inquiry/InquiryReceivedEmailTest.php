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
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED . '_notification', InquiryReceivedEmail::class, 'trigger', 10, 2 );
		$this->email = new InquiryReceivedEmail( '/plugin/linker-commerce.php' );
	}

	/**
	 * The confirmation goes to the billing address, in the inquiry's language.
	 */
	public function test_sends_in_the_inquiry_language(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_billing_email' )->andReturn( 'maria@example.test' );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_meta' )->with( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META )->andReturn( '' );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'de_DE_formal' );
		$this->allow_locale_switch( 'de_DE_formal' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_inquiry_received', 'maria@example.test' );

		$this->email->trigger( 20, $order );

		$this->assertTrue( $this->email->is_customer_email() );
		$this->assertSame( '20', $this->email->placeholders['{order_number}'] );
		$this->assertSame( 'Your inquiry #{order_number} has been received', $this->email->get_default_subject() );
		$this->assertConditionsMet();
	}

	/**
	 * The body is this plugin's template with the inquiry; WooCommerce's own language switch stays off.
	 */
	public function test_content(): void {
		$this->email->object = Mockery::mock( WC_Order::class );
		WP_Mock::userFunction(
			'wc_get_template_html',
			array(
				'times'  => 1,
				'args'   => array( 'emails/linker-inquiry-received.php', Mockery::on( fn ( array $args ): bool => $args['order'] === $this->email->object && false === $args['sent_to_admin'] ), '', '/plugin/templates/' ),
				'return' => '<p>Hello</p>',
			)
		);

		$this->email->setup_locale();
		$this->email->restore_locale();
		$this->assertSame( '<p>Hello</p>', $this->email->get_content_html() );
		$this->assertSame( '', $this->email->get_content_plain() );
		$this->assertSame( '', $this->email->get_default_additional_content() );
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
