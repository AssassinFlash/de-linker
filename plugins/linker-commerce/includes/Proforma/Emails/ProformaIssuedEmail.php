<?php
/**
 * The Proforma invoice is ready, to the customer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma\Emails;

use DateTimeImmutable;
use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\CustomerOrderEmail;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Vocabulary\LocaleFormat;
use WC_Order;

/**
 * Sent when staff issue the Proforma: number, validity and a link to the PDF in
 * the account. The PDF is not attached and the email names no bank account:
 * the account copy is the one a customer can trust for the bank details
 * (docs/specs/11-commerce.md, journey step 5; account-workspace.md §0.2).
 */
final class ProformaIssuedEmail extends CustomerOrderEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_proforma_issued';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Proforma invoice issued', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when staff issue the Proforma invoice of an inquiry.', 'linker-commerce' );
		$this->template_html = 'emails/linker-proforma-issued.php';
		$this->placeholders  = array(
			'{order_number}'    => '',
			'{proforma_number}' => '',
		);
		add_action( 'woocommerce_order_status_' . Statuses::RECEIVED . '_to_' . Statuses::PROFORMA . '_notification', array( $this, 'trigger' ), 10, 2 );
		parent::__construct( $plugin_file );
	}

	/**
	 * Sends the email about an inquiry that already has a Proforma number.
	 *
	 * WooCommerce fires this on the status transition, before Issuer::ensure_issued()
	 * writes the number (woocommerce_order_status_{to} runs first; the email action
	 * is the from_to hook). A blocked inquiry — no bank account, an empty inquiry,
	 * a line without a price — keeps the new status and never gets a number. Sending
	 * then names an empty number, a validity of 1970-01-30 (issued meta 0 plus the
	 * 30-day term) and a download that 404s. No number, no mail. The Issue button
	 * writes the number before it changes the status, so that path still sends.
	 *
	 * @param int                $order_id Order id.
	 * @param WC_Order|false|int $order    Order, when the caller has it.
	 */
	public function trigger( $order_id, $order = false ): void {
		$order = $order instanceof WC_Order ? $order : wc_get_order( (int) $order_id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$number = (string) $order->get_meta( Issuer::NUMBER_META );
		if ( '' === $number ) {
			return;
		}
		$this->placeholders['{proforma_number}'] = $number;
		parent::trigger( $order_id, $order );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {proforma_number}: Proforma number, {order_number}: inquiry number. */
		return __( 'Your Proforma invoice {proforma_number} for inquiry #{order_number}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Your Proforma invoice is ready', 'linker-commerce' );
	}

	/**
	 * Number, validity and link for the template.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		$order = $this->object;
		if ( ! $order instanceof WC_Order ) {
			return array();
		}
		$issued = ( new DateTimeImmutable() )->setTimestamp( (int) $order->get_meta( Issuer::ISSUED_META ) );
		return array(
			'proforma_number' => (string) $order->get_meta( Issuer::NUMBER_META ),
			'valid_until'     => wp_date( LocaleFormat::date_format(), Document::valid_until( $issued )->getTimestamp() ),
			'download_url'    => DocumentDownload::proforma_url( $order ),
			'inquiry_url'     => $order->get_view_order_url(),
		);
	}
}
