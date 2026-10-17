<?php
/**
 * Tests for the new-inquiry notification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for NewInquiryEmail.
 *
 * @covers \Linker\Commerce\Inquiry\Emails\NewInquiryEmail
 */
final class NewInquiryEmailTest extends TestCase {

	/**
	 * The plugin's text domain may reload while an email renders (LocaleSwitch).
	 */
	public function setUp(): void {
		parent::setUp();
		$this->reload_plugin_textdomain();
	}

	/**
	 * A received inquiry goes to the team mailbox with blind copies and a reply address of the customer.
	 */
	public function test_notifies_the_team(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$this->options(
			array(
				Options::NOTIFY_BCC => 'copy@example.test',
				'WPLANG'            => '',
			)
		);
		$this->expect_action_on_any( 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED . '_notification', NewInquiryEmail::class, 'trigger', 10, 2 );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_billing_company' )->andReturn( 'Solarbau GmbH' );
		$order->allows( 'get_billing_email' )->andReturn( 'maria@example.test' );
		$order->allows( 'get_formatted_billing_full_name' )->andReturn( 'Maria Beispiel' );
		$this->allow_locale_switch( 'en_US' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_new_inquiry', 'sales@sunriverinverter.com' );

		$email = new NewInquiryEmail( '/plugin/linker-commerce.php', new Options() );
		$email->trigger( 20, $order );

		$this->assertSame(
			array(
				'{order_number}' => '20',
				'{company}'      => 'Solarbau GmbH',
			),
			$email->placeholders
		);
		$header = "Content-Type: text/html\r\nX-Linker-Internal: yes\r\nReply-to: Maria Beispiel <maria@example.test>\r\nBcc: copy@example.test\r\n";
		$this->filter_returns( 'woocommerce_email_headers', $header, array( $header, 'linker_new_inquiry', $order, $email ) );
		$this->assertSame( $header, $email->get_headers() );
		$this->assertConditionsMet();
	}
}
