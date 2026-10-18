<?php
/**
 * "Let Linker contact me": the contact card's route.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * GET linker-ai/v1/genie/contact tells the contact card what it needs when it
 * appears: a signed start time (FormGuard), the signed-in customer's
 * address (a customer with an account is never asked for one, #243),
 * whether this conversation's request is already with the team, and the team
 * mailbox customers see (MAILBOX_FILTER).
 *
 * POST passes the conversation on to the team. The hand-off is noted on the
 * conversation post (meta NOTE, one row per request, read by the admin's
 * conversation view) and handed to the mail through the action ACTION; the
 * team mail itself is linker-commerce's (Genie\ContactEmail, a
 * Mail\TeamEmail: recipients from the internal notification settings,
 * docs/specs/11-commerce.md "内部通知收件人"). No mail goes to the customer:
 * the card shows the confirmation, and an address a guest typed never
 * receives mail from this route.
 *
 * The hand-off carries the link to the whole conversation in the admin, a
 * summary (the customer's last messages, newest first), the page the card
 * was on and the solution draft (docs/specs/13-genie.md goal 6, A6).
 */
class ContactRequest {

	/**
	 * Route, under Proxy::NAMESPACE.
	 */
	public const ROUTE = '/genie/contact';

	/**
	 * The action that sends the team mail (linker-commerce listens).
	 */
	public const ACTION = 'linker_genie_contact_requested';

	/**
	 * Filter that names the team mailbox customers see (linker-commerce's
	 * Options::team_mailbox()); the card names it when a request is refused,
	 * so a customer who asked for a person never meets a dead end.
	 */
	public const MAILBOX_FILTER = 'linker_genie_team_mailbox';

	/**
	 * Requests one connection may send per hour: the contact form's limit
	 * (Linker\Commerce\Contact\Handler::LIMIT, three an hour), the site's
	 * other public door to the team.
	 */
	public const LIMIT = 3;

	/**
	 * Requests the whole site passes on per day. Every request is one team
	 * mail; the site takes at most 80 of the host's 100 mails a day
	 * (Linker\Commerce\Mail\Throttle::PER_DAY). With Genie's own
	 * conversation mail (ConversationMail::DAILY_CAP, 10) Genie takes at most
	 * 30 of them, which leaves 50 for registrations, inquiries and their
	 * receipts. On 2026-10-17, the busiest day the live mail log holds (the
	 * owner's test of the account chain), the site sent 7.
	 */
	public const DAILY = 20;

	/**
	 * Meta key of the hand-off notes on the conversation post.
	 */
	public const NOTE = 'linker_genie_contact';

	/**
	 * The offer's reasons (the service's schema.ContactReason).
	 */
	public const REASONS = array( 'asked', 'service', 'dissatisfied', 'repeat' );

	/**
	 * Customer messages the summary shows: the repeat rule's three rounds and
	 * the two before them (contact.REPEATS in the service), so a repeated
	 * question reads as repeated, with what led to it. The link has the rest.
	 */
	public const SUMMARY_MESSAGES = 5;

	/**
	 * Sets up the route.
	 *
	 * @param Conversations  $conversations The visitor's conversation.
	 * @param Thread         $thread        Its stored messages.
	 * @param PageContext    $pages         The page context the card sends.
	 * @param FormGuard|null $guard The public form's protections; this door's when omitted.
	 */
	public function __construct(
		private readonly Conversations $conversations,
		private readonly Thread $thread,
		private readonly PageContext $pages,
		?FormGuard $guard = null
	) {
		$this->guard = $guard ?? new FormGuard( 'genie_contact', self::LIMIT, self::DAILY );
	}

	/**
	 * The public form's protections (FormGuard).
	 *
	 * @var FormGuard
	 */
	private readonly FormGuard $guard;

	/**
	 * Why Genie offered the contact, in words: the one place the reasons
	 * (REASONS, the service's schema.ContactReason) get their labels. The
	 * hand-off carries the label in the site's language to the team mail, and
	 * the note keeps it for the admin's conversation view.
	 *
	 * @param string $reason One of REASONS.
	 */
	public static function reason_label( string $reason ): string {
		return match ( $reason ) {
			'service'      => __( 'Asked about the company, delivery or service', 'linker-tools' ),
			'dissatisfied' => __( 'Seemed frustrated or wanted a person', 'linker-tools' ),
			'repeat'       => __( 'Asked the same question three times in a row', 'linker-tools' ),
			default        => __( 'Asked to talk to a person', 'linker-tools' ),
		};
	}

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
				),
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'send' ),
					'permission_callback' => '__return_true',
					'args'                => array(
						'email'         => array( 'type' => 'string' ),
						'website'       => array( 'type' => 'string' ),
						'started'       => array( 'type' => 'string' ),
						'started_nonce' => array( 'type' => 'string' ),
						'reason'        => array(
							'type' => 'string',
							'enum' => self::REASONS,
						),
						'locale'        => array(
							'type' => 'string',
							'enum' => array( 'en', 'de' ),
						),
						'page'          => array( 'type' => 'object' ),
					),
				),
			)
		);
	}

	/**
	 * What the card needs when it appears.
	 */
	public function state(): WP_REST_Response {
		$conversation = $this->conversations->existing_id();
		$sent         = $conversation > 0 ? $this->sent( $conversation ) : null;
		$stamp        = $this->guard->stamp();
		$reply        = new WP_REST_Response(
			array(
				'started'       => $stamp['started'],
				'started_nonce' => $stamp['nonce'],
				'email'         => $this->customer()['email'] ?? null,
				'sent'          => null === $sent ? null : array( 'email' => $sent['email'] ),
				'mailbox'       => $this->mailbox(),
			)
		);
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * Passes the conversation on to the team.
	 *
	 * @param WP_REST_Request $request The card's request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function send( WP_REST_Request $request ) {
		$conversation = $this->conversations->existing_id();
		if ( $conversation < 1 ) {
			return $this->error( 'linker_genie_contact_conversation', 409 );
		}
		$customer = $this->customer();
		if ( null === $customer ) {
			$guard = array(
				'website'       => $request->get_param( 'website' ) ?? '',
				'started'       => $request->get_param( 'started' ),
				'started_nonce' => $request->get_param( 'started_nonce' ),
			);
			$email = sanitize_email( (string) $request->get_param( 'email' ) );
			if ( $this->guard->trapped( $guard ) ) {
				// A bot: answered like a delivery, sent nowhere (the contact form's rule).
				return $this->reply( $email );
			}
			if ( ! $this->guard->passes( $guard ) ) {
				return $this->error( 'linker_genie_contact_retry', 400 );
			}
			if ( ! is_email( $email ) ) {
				return $this->error( 'linker_genie_contact_email', 400 );
			}
			$customer = array(
				'user_id' => 0,
				'email'   => $email,
				'name'    => '',
			);
		}
		$sent = $this->sent( $conversation );
		if ( null !== $sent && $sent['email'] === $customer['email'] ) {
			// Nothing new since the team got this conversation: not twice.
			return $this->reply( $customer['email'] );
		}
		if ( ! has_action( self::ACTION ) ) {
			return $this->error( 'linker_genie_contact_unavailable', 503 );
		}
		if ( '' !== $this->guard->take() ) {
			return $this->error( 'linker_genie_contact_limited', 429 );
		}
		$handoff = $this->handoff( $conversation, $customer, $request );
		add_post_meta(
			$conversation,
			self::NOTE,
			array(
				'at'       => time(),
				'reason'   => $handoff['reason'],
				'label'    => $handoff['reason_label'],
				'email'    => $customer['email'],
				'user_id'  => $customer['user_id'],
				'page'     => $handoff['page'],
				'messages' => $handoff['conversation']['messages'],
			)
		);
		/**
		 * A customer asked Genie for the team's contact (#243); the team mail
		 * (linker-commerce, Genie\ContactEmail) listens.
		 *
		 * @param array<string, mixed> $handoff See handoff().
		 * @since 0.1.0
		 */
		do_action( self::ACTION, $handoff ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- self::ACTION is linker_genie_contact_requested.
		return $this->reply( $customer['email'] );
	}

	/**
	 * The hand-off the team mail is written from.
	 *
	 * @param int                                              $conversation Conversation post ID.
	 * @param array{user_id: int, email: string, name: string} $customer     Who asks.
	 * @param WP_REST_Request                                  $request      The card's request.
	 * @return array{conversation: array{id: int, url: string, messages: int}, reason: string, reason_label: string, locale: string, customer: array{user_id: int, email: string, name: string}, summary: list<string>, page: array{type: string, url: string, title: string}, draft: list<array{product_id: int, name: string, sku: string, quantity: int}>}
	 */
	public function handoff( int $conversation, array $customer, WP_REST_Request $request ): array {
		$messages = $this->thread->read( $conversation )['messages'];
		$asked    = array();
		foreach ( array_reverse( $messages ) as $message ) {
			if ( 'user' === ( $message['role'] ?? '' ) && '' !== trim( (string) ( $message['content'] ?? '' ) ) ) {
				$asked[] = trim( (string) $message['content'] );
			}
		}
		$reason = (string) $request->get_param( 'reason' );
		$reason = in_array( $reason, self::REASONS, true ) ? $reason : 'asked';
		$page   = $this->pages->sanitize( $request->get_param( 'page' ) );
		return array(
			'conversation' => array(
				'id'       => $conversation,
				'url'      => add_query_arg( 'conversation', $conversation, admin_url( 'admin.php?page=' . QualityPage::SLUG ) ),
				'messages' => count( $messages ),
			),
			'reason'       => $reason,
			// The staff's words for it, in the site's language: the team
			// mail and the admin's conversation view show this label.
			'reason_label' => self::in_site_language( static fn (): string => self::reason_label( $reason ) ),
			'locale'       => 'de' === $request->get_param( 'locale' ) ? 'de' : 'en',
			'customer'     => $customer,
			'summary'      => array_slice( $asked, 0, self::SUMMARY_MESSAGES ),
			'page'         => array(
				'type'  => $page['type'],
				'url'   => $this->own_url( $page['url'] ?? '' ),
				'title' => $page['title'] ?? '',
			),
			'draft'        => $this->draft(),
		);
	}

	/**
	 * A text in the site's own language (the staff's): the team mail and the
	 * admin are written in it, whatever page the customer asked from.
	 *
	 * @param callable(): string $text Makes the text.
	 */
	private static function in_site_language( callable $text ): string {
		$site     = get_option( 'WPLANG' );
		$switched = switch_to_locale( is_string( $site ) && '' !== $site ? $site : 'en_US' );
		try {
			return $text();
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
		}
	}

	/**
	 * The sent contact cards of a conversation, for its history: each after
	 * the message it followed (the stored messages' count when it was sent,
	 * which is the index of the answer that showed the card).
	 *
	 * @param int $conversation Conversation post ID.
	 * @return list<array{after: int, email: string}>
	 */
	public static function cards( int $conversation ): array {
		$cards = array();
		foreach ( $conversation > 0 ? (array) get_post_meta( $conversation, self::NOTE, false ) : array() as $note ) {
			if ( is_array( $note ) && is_email( (string) ( $note['email'] ?? '' ) ) ) {
				$cards[] = array(
					'after' => (int) ( $note['messages'] ?? 0 ),
					'email' => (string) $note['email'],
				);
			}
		}
		return $cards;
	}

	/**
	 * The lines of the visitor's solution draft.
	 *
	 * REST requests start without WooCommerce's session; `wc_load_cart()`
	 * loads it from the visitor's cookie (PageContext::draft_ids()).
	 *
	 * @return list<array{product_id: int, name: string, sku: string, quantity: int}>
	 */
	protected function draft(): array {
		if ( ! function_exists( 'wc_load_cart' ) || ! function_exists( 'WC' ) ) {
			return array();
		}
		wc_load_cart();
		$lines = array();
		foreach ( WC()->cart->get_cart() as $line ) {
			$product = $line['data'] ?? null;
			if ( ! $product instanceof \WC_Product ) {
				continue;
			}
			$lines[] = array(
				'product_id' => (int) $product->get_id(),
				'name'       => $product->get_name(),
				'sku'        => (string) $product->get_sku(),
				'quantity'   => (int) ( $line['quantity'] ?? 0 ),
			);
		}
		return $lines;
	}

	/**
	 * The team mailbox customers see, '' when no plugin names it.
	 */
	private function mailbox(): string {
		/**
		 * The team mailbox customers see (linker-commerce answers).
		 *
		 * @param string $mailbox '' until a plugin names it.
		 * @since 0.1.0
		 */
		$mailbox = apply_filters( self::MAILBOX_FILTER, '' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- self::MAILBOX_FILTER is linker_genie_team_mailbox.
		return false !== is_email( $mailbox ) ? $mailbox : '';
	}

	/**
	 * The signed-in customer: address and name from the account; null for a guest.
	 *
	 * @return array{user_id: int, email: string, name: string}|null
	 */
	private function customer(): ?array {
		if ( ! is_user_logged_in() ) {
			return null;
		}
		$user = wp_get_current_user();
		$id   = (int) $user->ID;
		// The account's billing address is where the inquiries go; the login's when it has none.
		$billing = (string) get_user_meta( $id, 'billing_email', true );
		$name    = trim( get_user_meta( $id, 'billing_first_name', true ) . ' ' . get_user_meta( $id, 'billing_last_name', true ) );
		return array(
			'user_id' => $id,
			'email'   => is_email( $billing ) ? $billing : (string) $user->user_email,
			'name'    => '' !== $name ? $name : (string) $user->display_name,
		);
	}

	/**
	 * This conversation's request, when nothing was said since it went out.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return array{email: string}|null
	 */
	private function sent( int $conversation ): ?array {
		$notes = get_post_meta( $conversation, self::NOTE, false );
		$last  = is_array( $notes ) && array() !== $notes ? end( $notes ) : null;
		if ( ! is_array( $last ) ) {
			return null;
		}
		$count = count( $this->thread->read( $conversation )['messages'] );
		if ( (int) ( $last['messages'] ?? -1 ) !== $count ) {
			return null;
		}
		return array( 'email' => (string) ( $last['email'] ?? '' ) );
	}

	/**
	 * A page address of this site, '' for any other: the team clicks it.
	 *
	 * @param string $url The address the card sent, escaped.
	 */
	private function own_url( string $url ): string {
		$home = wp_parse_url( (string) get_option( 'home' ), PHP_URL_HOST );
		$host = wp_parse_url( $url, PHP_URL_HOST );
		return is_string( $home ) && is_string( $host ) && strtolower( $home ) === strtolower( $host ) ? $url : '';
	}

	/**
	 * The card's answer to a request that is with the team.
	 *
	 * @param string $email Where the team replies.
	 */
	private function reply( string $email ): WP_REST_Response {
		$reply = new WP_REST_Response(
			array(
				'sent'  => true,
				'email' => $email,
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
