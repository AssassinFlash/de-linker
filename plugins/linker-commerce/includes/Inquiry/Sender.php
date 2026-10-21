<?php
/**
 * The shared entry for sending an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\PageUrls;

use Linker\Commerce\Contact\Submission;
use WC_Order;
use WP_Error;

/**
 * Uses Woo's order storage and status-triggered mail for both public doors.
 * Callers verify the request nonce and PublicGuard before calling request() or message().
 */
final class Sender {


	/**
	 * The filter Linker\Tools\Genie\InquirySummary answers with the conversation
	 * summary (#244). The literal is kept here so this plugin needs no class of
	 * the other: an inactive linker-tools simply leaves the filter unanswered.
	 */
	private const SUMMARY_FILTER = 'linker_genie_inquiry_summary';

	/**
	 * Order meta the summary array is stored under; the new-inquiry mail and
	 * the inquiry screen read it (Linker\Tools\Genie\InquirySummary::META).
	 */
	public const SUMMARY_META = '_linker_genie_summary';

	/**
	 * Sends validated details with the current solution draft.
	 * Products, prices and customer identity always come from Woo's session.
	 *
	 * @param Submission                      $details Validated reply details and message.
	 * @param array<string, mixed>            $billing Optional account billing edits; guests cannot supply them.
	 * @param array<string, mixed>|false|null $summary The conversation summary the
	 *        Genie confirmation card showed (#250): an array stores it, false
	 *        stores none (the customer turned the summary off), null asks the
	 *        filter as the request page does (#244).
	 * @return WC_Order|WP_Error Received inquiry or validation failure.
	 */
	public function request( Submission $details, array $billing = array(), array|false|null $summary = null ): WC_Order|WP_Error {
		if ( WC()->cart->is_empty() && '' === $details->message ) {
			return new WP_Error( 'linker_inquiry_empty', __( 'Please add a product or write a message.', 'linker-commerce' ) );
		}
		foreach ( array( WC()->cart->check_cart_item_validity(), WC()->cart->check_cart_item_stock() ) as $valid ) {
			if ( $valid instanceof WP_Error ) {
				return $valid;
			}
		}
		$data = array_merge(
			BillingFields::values( $billing ),
			array(
				'billing_first_name' => $details->name,
				'billing_last_name'  => '',
				'billing_email'      => $details->email,
				'billing_company'    => $details->company,
				'order_comments'     => $details->message,
				'payment_method'     => ProformaGateway::ID,
			)
		);
		WC()->cart->calculate_totals();
		$id = WC()->checkout()->create_order( $data );
		if ( $id instanceof WP_Error ) {
			return $id;
		}
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			return new WP_Error( 'linker_inquiry_create', __( 'Please try sending your inquiry again.', 'linker-commerce' ) );
		}
		$this->attach_summary( $order, $summary );
		$this->receive( $order, $details, 'proforma' );
		WC()->cart->empty_cart();
		return $order;
	}

	/**
	 * Sends a contact message without reading or consuming the solution draft.
	 *
	 * @param Submission           $details Validated reply details and message.
	 * @param array<string, mixed> $meta    Record meta a door adds before the mail goes (Genie's hand-off, #243).
	 */
	public function message( Submission $details, array $meta = array() ): WC_Order {
		$order = new WC_Order();
		$order->set_customer_id( get_current_user_id() );
		$order->set_created_via( 'linker_contact' );
		$order->set_address(
			array(
				'first_name' => $details->name,
				'email'      => $details->email,
				'company'    => $details->company,
			),
			'billing'
		);
		$order->set_customer_note( $details->message );
		$order->set_payment_method( ProformaGateway::ID );
		foreach ( $meta as $key => $value ) {
			$order->update_meta_data( (string) $key, $value );
		}
		$this->receive( $order, $details, 'contact' );
		return $order;
	}

	/**
	 * Stores the conversation summary the team reads with the inquiry (#244).
	 *
	 * The browser's own conversation is summarized (never an id from the form);
	 * an unanswered filter, no conversation or a refused answer leaves the
	 * inquiry without the block — it is never held up (InquirySummary::META).
	 * The Genie confirmation card (#250) hands over the exact summary it showed,
	 * or false when the customer turned the summary off.
	 *
	 * @param WC_Order                        $order   The inquiry just created.
	 * @param array<string, mixed>|false|null $summary The card's summary; null asks the filter.
	 */
	private function attach_summary( WC_Order $order, array|false|null $summary = null ): void {
		if ( false === $summary ) {
			return;
		}
		if ( null === $summary ) {
			// phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- linker-tools' filter (Linker\Tools\Genie\InquirySummary::FILTER) answers with the browser's conversation summary.
			$summary = apply_filters( self::SUMMARY_FILTER, null, 0 );
		}
		if ( is_array( $summary ) && isset( $summary['summary'] ) && '' !== (string) $summary['summary'] ) {
			$order->update_meta_data( self::SUMMARY_META, $summary );
		}
	}

	/**
	 * One stored record and status-driven mail; the receipt alone has a daily cap.
	 *
	 * @param WC_Order   $order Native inquiry.
	 * @param Submission $details Validated reply details.
	 * @param string     $source proforma or contact.
	 */
	private function receive( WC_Order $order, Submission $details, string $source ): void {
		$order->set_payment_method_title( '' );
		$this->line_language( $order, $details->locale );
		$order->update_meta_data( OrderLocale::META, $details->locale );
		$order->update_meta_data( '_linker_inquiry_source', $source );
		$order->update_meta_data( '_linker_inquiry_topic', $details->intent );
		// A real native id stabilizes the receipt reservation across a resumed save.
		$order->save();
		$receipt_reason = 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode()
			? \Linker\Commerce\Protection\ReceiptBudget::reason( $details->email, $order->get_id() )
			: ( ( new ReceiptLimit() )->take() ? '' : 'daily_cap' );
		$order->update_meta_data( ReceiptLimit::SKIPPED_META, $receipt_reason );
		// Unverified destinations receive only a fixed acknowledgement, never
		// attacker-supplied names, products, notes or links.
		$order->update_meta_data( '_linker_fixed_receipt', \Linker\Commerce\Protection\Business::enabled() ? 'yes' : '' );
		$order->save();
		// Woo loads transactional email listeners lazily. Load before the transition.
		WC()->mailer();
		$order->update_status( Statuses::RECEIVED );
	}

	/**
	 * Admin-post cannot use the storefront's name filter; retain the canonical
	 * product id and write its translated title before notifications render.
	 *
	 * @param WC_Order $order Created inquiry.
	 * @param string   $locale Validated form language.
	 */
	private function line_language( WC_Order $order, string $locale ): void {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return;
		}
		foreach ( $order->get_items() as $item ) {
			if ( ! $item instanceof \WC_Order_Item_Product ) {
				continue;
			}
			$twin = PageUrls::twin( $item->get_product_id(), $locale );
			$name = $twin > 0 ? get_post_field( 'post_title', $twin ) : '';
			if ( '' !== $name ) {
				$item->set_name( $name );
				$item->save();
			}
		}
	}
}
