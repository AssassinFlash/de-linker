<?php
/**
 * Tests for the language of WooCommerce's customer emails.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\EmailLocale;
use Linker\Commerce\Tests\Fixtures\CustomerEmail;
use Linker\Commerce\Tests\TestCase;
use WC_Email;

/**
 * Tests for EmailLocale.
 *
 * @covers \Linker\Commerce\Mail\EmailLocale
 */
final class EmailLocaleTest extends TestCase {

	/**
	 * Customer emails keep the customer's language; other emails keep WooCommerce's choice.
	 */
	public function test_customer_emails_keep_the_request_language(): void {
		$customer = new CustomerEmail();
		$team     = new WC_Email();

		$this->assertFalse( ( new EmailLocale() )->allow( true, $customer ) );
		$this->assertTrue( ( new EmailLocale() )->allow( true, $team ) );
	}
}
