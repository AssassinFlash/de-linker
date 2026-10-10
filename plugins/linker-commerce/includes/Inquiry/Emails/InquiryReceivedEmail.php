<?php
/**
 * Confirmation of an inquiry, to the customer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Emails;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\CustomerOrderEmail;

/**
 * Sent when an inquiry is received: its number, the reply promise and the
 * products asked for.
 */
final class InquiryReceivedEmail extends CustomerOrderEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_inquiry_received';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Inquiry received', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when an inquiry is received.', 'linker-commerce' );
		$this->template_html = 'emails/linker-inquiry-received.php';
		$this->placeholders  = array( '{order_number}' => '' );
		add_action( 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED . '_notification', array( $this, 'trigger' ), 10, 2 );
		parent::__construct( $plugin_file );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {order_number} is replaced by the inquiry number. */
		return __( 'Your inquiry #{order_number} has been received', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Inquiry received', 'linker-commerce' );
	}
}
