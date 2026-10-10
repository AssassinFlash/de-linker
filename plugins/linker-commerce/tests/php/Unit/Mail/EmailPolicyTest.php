<?php
/**
 * Tests for which WooCommerce emails stay on.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\EmailPolicy;
use Linker\Commerce\Tests\Fixtures\PluginEmail;
use Linker\Commerce\Tests\TestCase;
use WC_Email;
use WP_Mock;

/**
 * Tests for EmailPolicy.
 *
 * @covers \Linker\Commerce\Mail\EmailPolicy
 */
final class EmailPolicyTest extends TestCase {

	/**
	 * Order, payment and shipping emails go off; the welcome email, the password reset, the
	 * administrator's gateway notice and this plugin's emails stay on.
	 */
	public function test_switches_off_the_order_emails(): void {
		$emails = array();
		foreach ( array( 'new_order', 'customer_processing_order', 'customer_completed_order', 'customer_invoice', 'customer_review_request', 'customer_new_account', 'customer_reset_password', 'admin_payment_gateway_enabled' ) as $id ) {
			$email         = new WC_Email();
			$email->id     = $id;
			$emails[ $id ] = $email;
		}
		$emails[ PluginEmail::class ] = new PluginEmail();

		foreach ( array( 'new_order', 'customer_processing_order', 'customer_completed_order', 'customer_invoice', 'customer_review_request' ) as $id ) {
			WP_Mock::expectFilterAdded( 'woocommerce_email_enabled_' . $id, '__return_false' );
		}

		$this->assertSame( $emails, ( new EmailPolicy() )->switch_off_others( $emails ) );
		$this->assertConditionsMet();
	}
}
