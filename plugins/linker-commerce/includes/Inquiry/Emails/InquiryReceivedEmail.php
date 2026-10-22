<?php
/**
 * Confirmation of an inquiry, to the customer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Emails;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Inquiry\ReceiptLimit;
use Linker\Commerce\Mail\CustomerOrderEmail;
use WC_Order;

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
	 * A public-door receipt omitted at the cap must not be enqueued by the
	 * status notification; the independent team notification still runs.
	 *
	 * @param int                $order_id Inquiry ID.
	 * @param WC_Order|false|int $order Inquiry, if already loaded.
	 */
	public function trigger( $order_id, $order = false ): void {
		$order = $order instanceof WC_Order ? $order : wc_get_order( (int) $order_id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		if ( '' !== $order->get_meta( ReceiptLimit::SKIPPED_META ) ) {
			return;
		}
		\Linker\Commerce\Inquiry\Assessment\Queue::defer( $order );
	}

	/** Capture the native receipt without sending or spending a mail allowance.
	 *
	 * @param WC_Order $order Native inquiry.
	 */
	public function capture( WC_Order $order ): ?\Linker\Commerce\Mail\Message {
		return \Linker\Commerce\Mail\Capture::run(
			$this,
			function () use ( $order ): void {
				parent::trigger( $order->get_id(), $order );
			}
		);
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
