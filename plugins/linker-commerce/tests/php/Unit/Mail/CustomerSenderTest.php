<?php
/**
 * Customer mail retains WooCommerce's sender settings.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Contact\Emails\ReceiptEmail;
use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Customer email objects keep the external Woo sender contract, supplied by
 * the WC_Email double. NotificationRoutingTest verifies native Woo and Outbox.
 *
 * @covers \Linker\Commerce\Mail\CustomerOrderEmail
 * @covers \Linker\Commerce\Contact\Emails\ContactEmail
 */
final class CustomerSenderTest extends TestCase {

	/**
	 * Both customer email families ignore the internal sender and follow Woo.
	 *
	 * @testWith ["", "Linker", "sales@de-linker.com"]
	 *           ["alerts@example.test", "Linker", "sales@de-linker.com"]
	 *           ["alerts@example.test", "Linker customer team", "customers@example.test"]
	 *
	 * @param string $internal Internal sender setting.
	 * @param string $name     Woo sender name.
	 * @param string $address  Woo sender address.
	 */
	public function test_customer_sender_follows_woocommerce( string $internal, string $name, string $address ): void {
		$this->plain_text();
		$this->options(
			array(
				Options::NOTIFY_FROM             => $internal,
				'woocommerce_email_from_name'    => $name,
				'woocommerce_email_from_address' => $address,
			)
		);
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED . '_notification', InquiryReceivedEmail::class, 'trigger', 10, 2 );
		foreach ( array( new InquiryReceivedEmail( '/plugin/linker-commerce.php' ), new ReceiptEmail( '/plugin/linker-commerce.php' ) ) as $email ) {
			$this->assertSame( $name, $email->get_from_name() );
			$this->assertSame( $address, $email->get_from_address() );
		}
	}
}
