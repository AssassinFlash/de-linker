<?php
/**
 * The inquiry confirmation card (#250, docs/specs/13-genie.md goal 5).
 *
 * Genie drafts an inquiry in the conversation; the shell's card shows every line
 * that will be sent — the solution draft's products and quantities, the message,
 * whether the conversation summary goes with it, and the one-business-day reply
 * promise. Only the customer's Send button sends: this route is the one writer,
 * and the model has no ability that reaches it. A model sentence that claims an
 * inquiry was sent is refused by the service's grounding (inquiry.py,
 * ground._no_sent_claim), and the forged-claim test holds both halves (A8).
 *
 * The send is #246's inquiry, not a second implementation: the route hands the
 * validated details to linker-commerce on SEND_FILTER, whose Genie module calls
 * Inquiry\Sender::request() — the same Woo record, Proforma gateway, statuses,
 * team mail and receipt the request page uses. The conversation summary is #244's
 * InquirySummary, attached or not as the card's switch says; when it is attached
 * the record stores its meta and the team mail shows it.
 *
 * A guest gives the request page's own required details (name, reply address,
 * consent); a signed-in customer's come from the account. When the draft and the
 * message are both empty there is nothing to send: the card leads to the request
 * page, where the solution draft and the message are prefilled (#244), and the
 * route never invents a line.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * GET linker-ai/v1/genie/inquiry states what the card would send; POST sends it.
 */
class InquiryRequest {

	/**
	 * Route, under Proxy::NAMESPACE.
	 */
	public const ROUTE = '/genie/inquiry';

	/**
	 * The filter linker-commerce answers by sending the inquiry
	 * (Linker\Commerce\Genie\Module::INQUIRY_FILTER).
	 */
	public const SEND_FILTER = 'linker_tools_genie_inquiry_send';

	/**
	 * The filter that names the request page in the card's language
	 * (Linker\Commerce\Genie\Module::INQUIRY_PAGE_FILTER: Checkout::request_url()).
	 */
	public const PAGE_FILTER = 'linker_genie_inquiry_page';

	/**
	 * Sends one connection may make per hour: the request page's own limit
	 * (Inquiry\PublicGuard::LIMIT, three an hour, both public doors share it).
	 */
	public const LIMIT = 3;

	/**
	 * Inquiries the whole site takes through the card per day: each is a team
	 * mail and a receipt (two of Mail\Throttle's 80 a day). Genie's card keeps
	 * to 10 (20 mails), beside the contact door's 20 (40) and the conversation
	 * mail's 10, so Genie's share stays at 70 and registrations and approvals
	 * keep their room. On 2026-10-17, the busiest day the live mail log holds,
	 * the site sent 7.
	 */
	public const DAILY = 10;

	/**
	 * Meta key of the sent inquiries on the conversation post: one row per send,
	 * kept so the sent card stays in the history (after the answer it followed).
	 */
	public const NOTE = 'linker_genie_inquiry';

	/**
	 * The inquiry statuses the card names, without WooCommerce's `wc-` prefix
	 * (Linker\Commerce\Inquiry\Statuses and WooCommerce's own ends). The shell
	 * translates each in the page's language.
	 */
	public const STATUSES = array( 'inquiry-received', 'proforma-issued', 'completed', 'cancelled', 'pending' );

	/**
	 * Sets up the route.
	 *
	 * @param Conversations  $conversations The visitor's conversation.
	 * @param Thread         $thread        Its stored messages.
	 * @param PageContext    $pages         The page context the card sends.
	 * @param FormGuard|null $guard         The public form's protections; this door's when omitted.
	 */
	public function __construct(
		private readonly Conversations $conversations,
		private readonly Thread $thread,
		private readonly PageContext $pages,
		?FormGuard $guard = null
	) {
		$this->guard = $guard ?? new FormGuard( 'genie_inquiry', self::LIMIT, self::DAILY );
	}

	/**
	 * The public form's protections (FormGuard).
	 *
	 * @var FormGuard
	 */
	private readonly FormGuard $guard;

	/**
	 * Registers the route; runs on rest_api_init.
	 */
	public function register(): void {
		register_rest_route(
			Proxy::NAMESPACE,
			self::ROUTE,
			array(
				array(
					'methods'             => 'GET',
					'callback'            => array( $this, 'state' ),
					'permission_callback' => '__return_true',
					'args'                => array(
						'locale' => array(
							'type' => 'string',
							'enum' => array( 'en', 'de' ),
						),
					),
				),
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'send' ),
					'permission_callback' => '__return_true',
					'args'                => array(
						'name'           => array( 'type' => 'string' ),
						'email'          => array( 'type' => 'string' ),
						'company'        => array( 'type' => 'string' ),
						'website'        => array( 'type' => 'string' ),
						'started'        => array( 'type' => 'string' ),
						'started_nonce'  => array( 'type' => 'string' ),
						'consent'        => array( 'type' => 'string' ),
						'message'        => array( 'type' => 'string' ),
						'attach_summary' => array( 'type' => 'string' ),
						// The lines the card showed: the send is refused when the
						// solution draft changed since (review the card again).
						'lines'          => array( 'type' => 'string' ),
						'locale'         => array(
							'type' => 'string',
							'enum' => array( 'en', 'de' ),
						),
						'page'           => array( 'type' => 'object' ),
					),
				),
			)
		);
	}

	/**
	 * What the card would send, and whether this conversation already sent it.
	 *
	 * @param WP_REST_Request $request The card's request.
	 */
	public function state( WP_REST_Request $request ): WP_REST_Response {
		$locale       = 'de' === $request->get_param( 'locale' ) ? 'de' : 'en';
		$conversation = $this->conversations->existing_id();
		$stamp        = $this->guard->stamp();
		$draft        = $conversation > 0 ? $this->draft( $locale ) : $this->nothing();
		$summary      = $conversation > 0 ? $this->summary( $conversation, $locale ) : null;
		$message      = null !== $summary ? (string) ( $summary['note'] ?? '' ) : '';
		$reply        = new WP_REST_Response(
			array(
				'conversation'  => $conversation,
				'started'       => $stamp['started'],
				'started_nonce' => $stamp['nonce'],
				'account'       => $this->customer(),
				'lines'         => $draft['lines'],
				'lines_digest'  => $draft['digest'],
				'message'       => $message,
				'summary'       => null !== $summary ? (string) ( $summary['summary'] ?? '' ) : '',
				'sent'          => $conversation > 0 ? $this->sent( $conversation, $locale ) : null,
				'page_url'      => $this->page_url( $locale ),
				// Nothing to send: the card leads to the request page.
				'ready'         => array() !== $draft['lines'] || '' !== trim( $message ),
			)
		);
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * Sends the card's inquiry through #246's one writer.
	 *
	 * @param WP_REST_Request $request The card's request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function send( WP_REST_Request $request ) {
		$conversation = $this->conversations->existing_id();
		if ( $conversation < 1 ) {
			return $this->error( 'linker_genie_inquiry_conversation', 409 );
		}
		$locale   = 'de' === $request->get_param( 'locale' ) ? 'de' : 'en';
		$customer = $this->customer();
		if ( null === $customer ) {
			$guard    = array(
				'website'       => $request->get_param( 'website' ) ?? '',
				'started'       => $request->get_param( 'started' ),
				'started_nonce' => $request->get_param( 'started_nonce' ),
			);
			$customer = array(
				'user_id' => 0,
				'email'   => sanitize_email( (string) $request->get_param( 'email' ) ),
				'name'    => sanitize_text_field( (string) $request->get_param( 'name' ) ),
				'company' => sanitize_text_field( (string) $request->get_param( 'company' ) ),
			);
			if ( $this->guard->trapped( $guard ) ) {
				// A bot: answered 200 and sent nowhere (the request page's rule).
				return $this->reply( $customer['email'], null );
			}
			if ( ! $this->guard->passes( $guard ) ) {
				return $this->error( 'linker_genie_inquiry_retry', 400 );
			}
			if ( ! is_email( $customer['email'] ) ) {
				return $this->error( 'linker_genie_inquiry_email', 400 );
			}
			if ( '' === $customer['name'] ) {
				return $this->error( 'linker_genie_inquiry_name', 400 );
			}
			if ( '1' !== (string) $request->get_param( 'consent' ) ) {
				return $this->error( 'linker_genie_inquiry_consent', 400 );
			}
		}
		$existing = $this->existing( $conversation, $locale );
		if ( null !== $existing ) {
			// Nothing was said since this conversation's inquiry went out: not twice.
			return $this->reply( (string) $existing['email'], $existing );
		}
		$draft = $this->draft( $locale );
		if ( ! hash_equals( (string) $draft['digest'], (string) $request->get_param( 'lines' ) ) ) {
			// The solution draft changed after the card showed it (review and send again).
			return $this->error( 'linker_genie_inquiry_changed', 409 );
		}
		$message = trim( sanitize_textarea_field( (string) $request->get_param( 'message' ) ) );
		if ( array() === $draft['lines'] && '' === $message ) {
			return $this->error( 'linker_genie_inquiry_empty', 409 );
		}
		if ( ! has_filter( self::SEND_FILTER ) ) {
			return $this->error( 'linker_genie_inquiry_unavailable', 503 );
		}
		if ( '' !== $this->guard->take() ) {
			return $this->error( 'linker_genie_inquiry_limited', 429 );
		}
		$summary = '1' === (string) $request->get_param( 'attach_summary' ) ? $this->summary( $conversation, $locale ) : null;
		$page    = $this->pages->sanitize( $request->get_param( 'page' ) );
		/**
		 * The inquiry confirmation card hands its details to the site's one
		 * writer (#250): linker-commerce answers with Sender::request()'s record
		 * and whether the receipt went, or with the WP_Error Woo returned.
		 *
		 * @param mixed                $sent    null until a listener sent it; then array{order: int, receipt: bool} or WP_Error.
		 * @param array<string, mixed> $details See send().
		 * @since 0.1.0
		 */
		$sent = apply_filters(
			self::SEND_FILTER, // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- self::SEND_FILTER is linker_tools_genie_inquiry_send.
			null,
			array(
				'conversation' => $conversation,
				'customer'     => $customer,
				'message'      => $message,
				'locale'       => $locale,
				// false tells the sender the customer turned the summary off;
				// an array is the exact summary the card showed.
				'summary'      => null === $summary ? false : $summary,
				'page'         => $page,
			)
		);
		if ( ! is_array( $sent ) || ! isset( $sent['order'] ) ) {
			if ( is_wp_error( $sent ) ) {
				// Woo refused the card's lines (stock, an empty record): the card
				// names the request page rather than guessing a cause.
				return $this->error( 'linker_genie_inquiry_refused', 409 );
			}
			return $this->error( 'linker_genie_inquiry_unavailable', 503 );
		}
		$inquiry = $this->inquiry( (int) $sent['order'], $locale );
		if ( null === $inquiry ) {
			return $this->error( 'linker_genie_inquiry_unavailable', 503 );
		}
		add_post_meta(
			$conversation,
			self::NOTE,
			array(
				'at'       => time(),
				'order'    => (int) $sent['order'],
				'email'    => $customer['email'],
				'user_id'  => (int) $customer['user_id'],
				'messages' => count( $this->thread->read( $conversation )['messages'] ),
				'summary'  => null !== $summary,
				'receipt'  => ! empty( $sent['receipt'] ),
				'page'     => $this->own_url( (string) ( $page['url'] ?? '' ) ),
			)
		);
		return $this->reply( $customer['email'], $inquiry );
	}

	/**
	 * The sent inquiries of a conversation, for its history: each after the
	 * message it followed (the stored messages' count when it was sent, which is
	 * the index of the answer that showed the card).
	 *
	 * @param int $conversation Conversation post ID.
	 * @return list<array<string, mixed>>
	 */
	public static function cards( int $conversation ): array {
		$cards = array();
		foreach ( $conversation > 0 ? (array) get_post_meta( $conversation, self::NOTE, false ) : array() as $note ) {
			if ( ! is_array( $note ) || (int) ( $note['order'] ?? 0 ) < 1 ) {
				continue;
			}
			$order = wc_get_order( (int) $note['order'] );
			if ( ! $order instanceof \WC_Order ) {
				continue;
			}
			$cards[] = array(
				'after'   => (int) ( $note['messages'] ?? 0 ),
				'order'   => $order->get_id(),
				'number'  => (string) $order->get_order_number(),
				'status'  => $order->get_status(),
				'receipt' => '' === (string) $order->get_meta( '_linker_receipt_skipped' ),
				'email'   => (string) ( $note['email'] ?? $order->get_billing_email() ),
				'url'     => 0 === (int) $order->get_customer_id() ? $order->get_checkout_order_received_url() : $order->get_view_order_url(),
			);
		}
		return $cards;
	}

	/**
	 * The lines of the visitor's solution draft, exactly what the request page
	 * sends and shows (Form::lines): Woo's own price line, under the price gate.
	 *
	 * @param string $locale The card's language (a product's translated title).
	 * @return array{lines: list<array<string, mixed>>, digest: string}
	 */
	protected function draft( string $locale ): array {
		if ( ! function_exists( 'wc_load_cart' ) || ! function_exists( 'WC' ) ) {
			return $this->nothing();
		}
		// A REST request starts without WooCommerce's session: it comes from
		// the visitor's cookie (PageContext::draft_ids() does the same).
		wc_load_cart();
		// The price line is Woo's sentence in the site's language; the card is
		// on a page of the visitor's, so the request reads it in that language.
		$switched = 'de' === $locale && switch_to_locale( 'de_DE_formal' );
		// The customer confirms what was shown: products, quantities, the price
		// line and the stock state, all of which the request page's own checks
		// read at the send. A change after the card appeared refuses the send
		// (the card shows the draft again).
		$fingerprint = array();
		try {
			$lines = array();
			foreach ( WC()->cart->get_cart() as $key => $line ) {
				$product = $line['data'] ?? null;
				if ( ! $product instanceof \WC_Product ) {
					continue;
				}
				// The card is rendered on a page of the visitor's language; the
				// REST request's own language is the site's (Sender::line_language()
				// writes the same twin into the record).
				$twin          = function_exists( 'pll_get_post' ) ? (int) pll_get_post( (int) $product->get_id(), $locale ) : 0;
				$lines[]       = array(
					'product_id' => (int) $product->get_id(),
					'name'       => $twin > 0 ? (string) get_the_title( $twin ) : $product->get_name(),
					'sku'        => (string) $product->get_sku(),
					'quantity'   => (int) ( $line['quantity'] ?? 0 ),
					'price_html' => $product->get_price_html(),
					'url'        => $twin > 0 ? esc_url_raw( (string) get_permalink( $twin ) ) : esc_url_raw( (string) $product->get_permalink() ),
				);
				$fingerprint[] = array(
					(int) $product->get_id(),
					(int) ( $line['quantity'] ?? 0 ),
					$product->get_price_html(),
					$product->is_in_stock(),
				);
			}
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
		}
		$digest = md5( (string) wp_json_encode( $fingerprint ) );
		return array(
			'lines'  => $lines,
			'digest' => $digest,
		);
	}

	/**
	 * An empty draft: the card leads to the request page.
	 *
	 * @return array{lines: list<array<string, mixed>>, digest: string}
	 */
	private function nothing(): array {
		return array(
			'lines'  => array(),
			'digest' => md5( '[]' ),
		);
	}

	/**
	 * #244's summary of the conversation, or null when there is none.
	 *
	 * The summary is written in the card's language: #244 reads the language of
	 * the request (determine_locale()), and this route's request is the site's
	 * (en) whatever page the card stands on, so the locale is switched for it.
	 *
	 * @param int    $conversation Conversation post ID.
	 * @param string $locale       The card's language (en/de).
	 * @return array<string, mixed>|null
	 */
	private function summary( int $conversation, string $locale ): ?array {
		$switched = 'de' === $locale && switch_to_locale( 'de_DE_formal' );
		try {
			// phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- linker-tools' filter (InquirySummary::FILTER) answers the browser's conversation summary.
			$summary = apply_filters( InquirySummary::FILTER, null, $conversation );
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
		}
		if ( ! is_array( $summary ) || '' === trim( (string) ( $summary['summary'] ?? '' ) ) ) {
			return null;
		}
		return $summary;
	}

	/**
	 * This conversation's inquiry, when nothing was said since it went out.
	 *
	 * @param int    $conversation Conversation post ID.
	 * @param string $locale       The card's language.
	 * @return array<string, mixed>|null
	 */
	private function existing( int $conversation, string $locale ): ?array {
		$notes = get_post_meta( $conversation, self::NOTE, false );
		$last  = is_array( $notes ) && array() !== $notes ? end( $notes ) : null;
		if ( ! is_array( $last ) || (int) ( $last['order'] ?? 0 ) < 1 ) {
			return null;
		}
		if ( (int) ( $last['messages'] ?? -1 ) !== count( $this->thread->read( $conversation )['messages'] ) ) {
			return null;
		}
		$inquiry = $this->inquiry( (int) $last['order'], $locale );
		if ( null !== $inquiry ) {
			$inquiry['email'] = (string) ( $last['email'] ?? $inquiry['email'] );
		}
		return $inquiry;
	}

	/**
	 * The sent state the card shows, read from the record.
	 *
	 * @param int    $conversation Conversation post ID.
	 * @param string $locale       The card's language.
	 * @return array<string, mixed>|null
	 */
	private function sent( int $conversation, string $locale ): ?array {
		return $this->existing( $conversation, $locale );
	}

	/**
	 * One inquiry as the card states it: number, status, receipt and where the
	 * customer reads it — from the Woo record itself.
	 *
	 * @param int    $order_id Order ID.
	 * @param string $locale   The card's language.
	 * @return array<string, mixed>|null
	 */
	private function inquiry( int $order_id, string $locale ): ?array {
		$order = $order_id > 0 ? wc_get_order( $order_id ) : false;
		if ( ! $order instanceof \WC_Order ) {
			return null;
		}
		$status = (string) $order->get_status();
		return array(
			'order'   => $order->get_id(),
			'number'  => (string) $order->get_order_number(),
			'status'  => in_array( $status, self::STATUSES, true ) ? $status : 'inquiry-received',
			'receipt' => '' === (string) $order->get_meta( '_linker_receipt_skipped' ),
			'email'   => (string) $order->get_billing_email(),
			'url'     => 0 === (int) $order->get_customer_id() ? $order->get_checkout_order_received_url() : $order->get_view_order_url(),
			'locale'  => $locale,
		);
	}

	/**
	 * The signed-in customer's details from the account; null for a guest.
	 *
	 * @return array{user_id: int, email: string, name: string, company: string}|null
	 */
	private function customer(): ?array {
		if ( ! is_user_logged_in() ) {
			return null;
		}
		$user    = wp_get_current_user();
		$id      = (int) $user->ID;
		$billing = (string) get_user_meta( $id, 'billing_email', true );
		$name    = trim( get_user_meta( $id, 'billing_first_name', true ) . ' ' . get_user_meta( $id, 'billing_last_name', true ) );
		return array(
			'user_id' => $id,
			'email'   => is_email( $billing ) ? $billing : (string) $user->user_email,
			'name'    => '' !== $name ? $name : (string) $user->display_name,
			'company' => (string) get_user_meta( $id, 'billing_company', true ),
		);
	}

	/**
	 * The request page in the card's language (Checkout::request_url()), so a
	 * card that cannot send leads to the prefilled page, never a dead end.
	 *
	 * @param string $locale The card's language.
	 */
	private function page_url( string $locale ): string {
		/**
		 * The request page in the card's language (linker-commerce answers with
		 * Checkout::request_url()).
		 *
		 * @param string $url    '' until a plugin names it.
		 * @param string $locale The card's language (en/de).
		 * @since 0.1.0
		 */
		$url = apply_filters( self::PAGE_FILTER, '', $locale ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- self::PAGE_FILTER is linker_genie_inquiry_page.
		if ( '' !== $url ) {
			return $url;
		}
		return function_exists( 'wc_get_checkout_url' ) ? (string) wc_get_checkout_url() : '';
	}

	/**
	 * A page address of this site, '' for any other.
	 *
	 * @param string $url The page address.
	 */
	private function own_url( string $url ): string {
		$home = wp_parse_url( (string) get_option( 'home' ), PHP_URL_HOST );
		$host = wp_parse_url( $url, PHP_URL_HOST );
		return is_string( $home ) && is_string( $host ) && strtolower( $home ) === strtolower( $host ) ? $url : '';
	}

	/**
	 * The card's answer to a request that is with the team.
	 *
	 * @param string                    $email   Where the team replies.
	 * @param array<string, mixed>|null $inquiry The sent state.
	 */
	private function reply( string $email, ?array $inquiry ): WP_REST_Response {
		$reply = new WP_REST_Response(
			array(
				'sent'    => null !== $inquiry,
				'email'   => $email,
				'inquiry' => $inquiry,
			)
		);
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * A refusal the card turns into its own sentence.
	 *
	 * @param string $code   Error code.
	 * @param int    $status HTTP status.
	 */
	private function error( string $code, int $status ): WP_Error {
		return new WP_Error( $code, $code, array( 'status' => $status ) );
	}
}
