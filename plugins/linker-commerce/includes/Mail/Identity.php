<?php
/**
 * A mail sender's name and address.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * The identity shared by internal Woo emails and plain wp_mail alerts.
 */
final readonly class Identity {

	/**
	 * Sets the sender identity.
	 *
	 * @param string $name  Sender name.
	 * @param string $email Sender address.
	 */
	public function __construct( public string $name, public string $email ) {}
}
