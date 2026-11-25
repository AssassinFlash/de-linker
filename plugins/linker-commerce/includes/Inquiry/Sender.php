<?php
/**
 * The shared entry for sending an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Planning\Context;
use Linker\Commerce\Planning\InquiryTransfer;

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
	 * @param Submission                                                     $details Validated reply details and message.
	 * @param array<string, mixed>                                           $billing Optional account billing edits; guests cannot supply them.
	 * @param array<string, mixed>|false|null                                $summary The conversation summary the
	 *                                       Genie confirmation card showed (#250): an array stores it, false
	 *                                       stores none (the customer turned the summary off), null asks the
	 *                                       conversation-summary filter.
	 * @param array<string, mixed>                                           $context Trusted related Genie conversation/page.
	 * @param array{intent:InquiryTransfer,handoff:array<string,mixed>}|null $review Guided review for this send.
	 * @return WC_Order|WP_Error Received inquiry or validation failure.
	 */
	public function request( Submission $details, array $billing = array(), array|false|null $summary = null, array $context = array(), ?array $review = null ): WC_Order|WP_Error {
		$handoff = $review['handoff'] ?? null;
		$error   = Context::preflight( $handoff );
		if ( null === $error && null === $review ) {
			$error = $this->cart_preflight( $details );
		}
		if ( $error instanceof WP_Error ) {
			return $error;
		}
		$data = array_merge(
			BillingFields::values( $billing ),
			array(
				'billing_first_name' => $details->name,
				'billing_last_name'  => '',
				'billing_email'      => $details->email,
				'billing_company'    => $details->company,
				'order_comments'     => $details->message,
				'payment_method'     => InquiryGateway::ID,
			)
		);
		if ( null === $review ) {
			WC()->cart->calculate_totals();
		}
		$lock_refused = false;
		try {
			$order = Context::submit_inquiry(
				function ( array $references, array $projects ) use ( $details, $data, $summary, $context, $review, &$lock_refused ): WC_Order|WP_Error {
					if ( null === $review ) {
						return $this->create( $details, $data, $summary, $context, $references, $projects, $lock_refused );
					}
					return $review['intent']->send(
						$review['handoff'],
						function () use ( $details, $data, $summary, $context, $references, $projects, &$lock_refused ): WC_Order|WP_Error {
							$error = $this->cart_preflight( $details );
							if ( $error instanceof WP_Error ) {
								return $error;
							}
							WC()->cart->calculate_totals();
							return $this->create( $details, $data, $summary, $context, $references, $projects, $lock_refused );
						}
					);
				},
				$handoff
			);
			if ( null === $review && $order instanceof WC_Order ) {
				\Linker\Commerce\Planning\Context::consume_captured_notes( $order );
				WC()->cart->empty_cart();
			}
		} catch ( \Throwable $error ) {
			$order = $this->unknown();
		}
		if ( $order instanceof WP_Error ) {
			$order = match ( $order->get_error_code() ) {
				'planning_transfer_busy', 'planning_transfer_invalid', 'planning_transfer_unavailable' => Context::admission_unavailable(),
				'planning_transfer_unconfirmed' => $this->unknown(),
				default => $order,
			};
		}
		return $lock_refused ? \Linker\Commerce\Planning\Context::admission_unavailable() : $order;
	}

	/**
	 * Create and receive the native order while holding its project locks.
	 *
	 * @param Submission                        $details Validated submission.
	 * @param array<string,mixed>               $data Checkout fields.
	 * @param array<string,mixed>|false|null    $summary Selected conversation summary.
	 * @param array<string,mixed>               $context Related conversation/page.
	 * @param array<string,array<string,mixed>> $references Admitted frozen reports.
	 * @param array<int,string>                 $projects Locked projects including the preliminary revision.
	 * @param bool                              $lock_refused New order stopped at its pre-save project lock check.
	 */
	private function create( Submission $details, array $data, array|false|null $summary, array $context, array $references, array $projects, bool &$lock_refused ): WC_Order|WP_Error {
		$expected    = array();
		$transaction = null;
		$prepare     = function ( WC_Order $order ) use ( $details, $summary, $context, $projects, &$lock_refused, &$expected, &$transaction ): void {
			$this->line_language( $order, $details->locale );
			$awaited = null === $summary && false !== has_filter( self::SUMMARY_FILTER );
			if ( array() !== $projects ) {
				// The form has no provider work. Its business/review slot joins Woo's first save.
				if ( ! $awaited ) {
					$transaction = new NativeTransaction();
				}
				$lock_refused = 0 === $order->get_id();
				\Linker\Commerce\Planning\ProjectReferences::require_locks( $projects );
				$lock_refused = false;
			}
			if ( $awaited ) {
				$this->prepare( $order, $details, 'inquiry', $context );
				$this->attach_summary( $order, $summary );
				Assessment\Queue::refresh_summary( $order );
			} else {
				$this->attach_summary( $order, $summary );
				$this->prepare( $order, $details, 'inquiry', $context );
			}
			$expected = self::prepared_meta( $order );
			// Optional summary/provider work has finished before the first native write.
			if ( null === $transaction ) {
				$transaction = new NativeTransaction();
				// Provider work can lose the connection. Its prior dispatch remains charged.
				\Linker\Commerce\Planning\ProjectReferences::require_locks( $projects );
			}
		};
		add_action( 'woocommerce_checkout_create_order', $prepare );
		try {
			$id = WC()->checkout()->create_order( $data );
			if ( $id instanceof WP_Error ) {
				return $id;
			}
			$order = wc_get_order( $id );
			if ( ! $order instanceof WC_Order ) {
				return new WP_Error( 'linker_inquiry_create', __( 'Please try sending your inquiry again.', 'linker-commerce' ) );
			}
			$stored = $this->verify_saved( $order, $expected );
			if ( $stored instanceof WP_Error ) {
				return $stored;
			}
			if ( ! $transaction instanceof NativeTransaction ) {
				return $this->unknown();
			}
			if ( ! \Linker\Commerce\Planning\Context::matches_admission( $order, $references ) ) {
				return $this->unknown();
			}
			$this->receive( $order, $details, 'inquiry', $context );
			$transaction->commit();
			return $order;
		} catch ( \Linker\Commerce\Protection\CapacityFull $error ) {
			return $error->problem;
		} finally {
			remove_action( 'woocommerce_checkout_create_order', $prepare );
			if ( $transaction instanceof NativeTransaction ) {
				try {
					$transaction->rollback();
				} catch ( \Throwable $error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- A lost commit is unknown; never reconnect to compensate.
				}
			}
		}
	}

	/**
	 * Read-only checks can fail before admission consumes a business attempt.
	 *
	 * @param Submission $details Validated reply details.
	 */
	public function preflight( Submission $details ): ?WP_Error {
		return Context::preflight() ?? $this->cart_preflight( $details );
	}

	/** Check native products after the projected draft becomes the checkout cart.
	 *
	 * @param Submission $details Validated reply details.
	 */
	private function cart_preflight( Submission $details ): ?WP_Error {
		if ( WC()->cart->is_empty() && '' === $details->message && ! \Linker\Commerce\Planning\Context::has_included_notes() ) {
			return new WP_Error( 'linker_inquiry_empty', __( 'Please add a product or write a message.', 'linker-commerce' ) );
		}
		// Woo's check_cart_item_validity removes an invalid line. Before proof
		// consumption, inspect the same native product facts without that write.
		foreach ( WC()->cart->get_cart() as $line ) {
			$product = $line['data'];
			if ( ! $product || ! $product->exists() || 'trash' === $product->get_status() ) {
				return new WP_Error( 'linker_draft_changed', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ) );
			}
		}
		$stock = WC()->cart->check_cart_item_stock();
		return $stock instanceof WP_Error ? $stock : null;
	}

	/**
	 * Sends a contact message without reading or consuming the solution draft.
	 *
	 * @param Submission           $details Validated reply details and message.
	 * @param array<string, mixed> $meta    Record meta a door adds before the mail goes (Genie's hand-off, #243).
	 */
	public function message( Submission $details, array $meta = array() ): WC_Order|WP_Error {
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
		$order->set_payment_method( InquiryGateway::ID );
		foreach ( $meta as $key => $value ) {
			if ( is_array( $value ) ) {
				Assessment\StructuredMeta::update( $order, (string) $key, $value );
			} else {
				$order->update_meta_data( (string) $key, $value );
			}
		}
		try {
			$this->receive( $order, $details, 'contact' );
		} catch ( \Linker\Commerce\Protection\CapacityFull $error ) {
			return $error->problem;
		} catch ( \Throwable $error ) {
			return $this->unknown();
		}
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
			Assessment\StructuredMeta::update( $order, self::SUMMARY_META, $summary );
		}
	}

	/**
	 * One stored record and status-driven mail; the receipt alone has a daily cap.
	 *
	 * @param WC_Order             $order Native inquiry.
	 * @param Submission           $details Validated reply details.
	 * @param string               $source inquiry or contact.
	 * @param array<string, mixed> $context Trusted related Genie conversation/page.
	 */
	private function prepare( WC_Order $order, Submission $details, string $source, array $context = array() ): void {
		$order->set_payment_method_title( '' );
		$order->update_meta_data( OrderLocale::META, $details->locale );
		$order->update_meta_data( '_linker_inquiry_source', $source );
		$order->update_meta_data( '_linker_inquiry_topic', $details->intent );
		if ( 'inquiry' === $source ) {
			( new \Linker\Commerce\Planning\Context() )->capture( $order );
		}
		Assessment\Queue::prepare( $order, $context );
		if ( 0 === $order->get_id() ) {
			$order->update_meta_data( Assessment\SendAuthorization::MARKER, Assessment\SendVerdict::POLICY ); }
		( new \Linker\Commerce\Protection\BusinessRecord() )->stamp( $order );
	}

	/**
	 * Complete the prepared native record and trigger the existing mail owners.
	 *
	 * @param WC_Order             $order Native inquiry.
	 * @param Submission           $details Validated reply details.
	 * @param string               $source inquiry or contact.
	 * @param array<string, mixed> $context Trusted related Genie conversation/page.
	 * @throws \Linker\Commerce\Protection\CapacityFull First save could not be verified.
	 */
	private function receive( WC_Order $order, Submission $details, string $source, array $context = array() ): void {
		if ( 0 === $order->get_id() ) {
			$this->line_language( $order, $details->locale );
			$this->prepare( $order, $details, $source, $context );
		}
		NativeTransaction::run(
			function () use ( $order ): void {
				$expected = self::prepared_meta( $order );
				// A real native id stabilizes the receipt reservation across a resumed save.
				$order->save();
				$stored = $this->verify_saved( $order, $expected );
				if ( $stored instanceof WP_Error ) {
					throw new \Linker\Commerce\Protection\CapacityFull( $stored ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Structured WP_Error is escaped by the native form consumer.
				}
				$order->update_meta_data( ReceiptLimit::SKIPPED_META, 'assessment_pending' );
				$order->save();
				// Woo loads transactional email listeners lazily. Load before the transition.
				WC()->mailer();
				$order->update_status( Statuses::RECEIVED );
				clean_post_cache( $order->get_id() );
				$read = Assessment\CurrentSource::order( $order->get_id() );
				if ( ! $read instanceof WC_Order || ! $read->has_status( Statuses::RECEIVED ) ) {
					throw new \RuntimeException( 'inquiry_received_readback_failed' );
				}
			}
		);
	}

	/**
	 * Woo stores scalar metadata as strings. The legacy data store unslashes arrays.
	 *
	 * @param WC_Order $order Prepared inquiry.
	 * @return array<string,mixed>
	 */
	private static function prepared_meta( WC_Order $order ): array {
		$legacy   = $order->get_data_store() instanceof \WC_Data_Store && is_a( $order->get_data_store()->get_current_class_name(), \WC_Order_Data_Store_CPT::class, true );
		$expected = array();
		foreach ( $order->get_meta_data() as $meta ) {
			$value                           = $legacy && is_array( $meta->value ) ? wp_unslash( $meta->value ) : $meta->value;
			$expected[ (string) $meta->key ] = is_scalar( $value ) ? (string) $value : $value;
		}
		return $expected;
	}

	/**
	 * Read the native order before acknowledging the customer's submission.
	 *
	 * @param WC_Order            $order Saved inquiry.
	 * @param array<string,mixed> $expected Values prepared for this write.
	 */
	private function verify_saved( WC_Order $order, array $expected ): ?WP_Error {
		$fresh = $order->get_id() > 0 ? Assessment\CurrentSource::order( $order->get_id() ) : null;
		if ( ! $fresh instanceof WC_Order ) {
			return $this->unknown();
		}
		foreach ( $expected as $name => $value ) {
			$actual = $fresh->get_meta( $name );
			$actual = is_scalar( $actual ) ? (string) $actual : $actual;
			if ( $value !== $actual ) {
				return $this->unknown();
			}
		}
		return null;
	}

	/** Native writes were not confirmed; preserve the original customer inputs/draft. */
	private function unknown(): WP_Error {
		return new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
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
				if ( $order->get_id() > 0 ) {
					$item->save();
				}
			}
		}
	}
}
