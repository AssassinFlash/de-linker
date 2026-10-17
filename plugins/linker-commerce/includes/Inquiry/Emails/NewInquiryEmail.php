<?php
/**
 * Notification of a new inquiry, to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Emails;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\TeamEmail;
use Linker\Commerce\Settings\Options;
use WC_Order;

/**
 * Sent to the team mailbox when an inquiry is received (owner ruling
 * 2026-10-07: after an inquiry the company is notified).
 */
final class NewInquiryEmail extends TeamEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_new_inquiry';

	/**
	 * Sets up the email.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( string $plugin_file, Options $options ) {
		$this->id            = self::ID;
		$this->title         = __( 'New inquiry', 'linker-commerce' );
		$this->description   = __( 'Sent to the internal notification address, with blind copies, when an inquiry is received.', 'linker-commerce' );
		$this->template_html = 'emails/linker-new-inquiry.php';
		$this->placeholders  = array(
			'{order_number}' => '',
			'{company}'      => '',
		);
		add_action( 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED . '_notification', array( $this, 'trigger' ), 10, 2 );
		parent::__construct( $plugin_file, $options );
	}

	/**
	 * Sends the notification about an inquiry.
	 *
	 * @param int                $order_id Order id.
	 * @param WC_Order|false|int $order    Order, when the caller has it.
	 */
	public function trigger( $order_id, $order = false ): void {
		$order = $order instanceof WC_Order ? $order : wc_get_order( (int) $order_id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$this->placeholders['{order_number}'] = $order->get_order_number();
		$this->placeholders['{company}']      = $order->get_billing_company();
		$this->notify( $order );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {order_number}: inquiry number, {company}: customer's company. */
		return __( 'New inquiry #{order_number} from {company}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		/* translators: {order_number}: inquiry number. */
		return __( 'New inquiry #{order_number}', 'linker-commerce' );
	}

	/**
	 * The inquiry for the template.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array( 'order' => $this->object );
	}
}
