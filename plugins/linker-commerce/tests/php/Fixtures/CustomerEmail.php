<?php
/**
 * A WooCommerce customer email, for tests of the email language rule.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use WC_Email;

/**
 * An email to a customer.
 */
final class CustomerEmail extends WC_Email {

	/**
	 * Marks the email as a customer email, as WooCommerce's customer emails do.
	 */
	public function __construct() {
		$this->customer_email = true;
	}
}
