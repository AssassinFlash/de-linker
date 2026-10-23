<?php
/**
 * Sending a conversation to the visitor's own mailbox.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Tools\Protection\Resources;

/**
 * A visitor can have any of their conversations emailed to themselves
 * (docs/specs/13-genie.md, goal 7; acceptance A12).
 *
 * - A signed-in customer's goes to the account's address at once.
 * - A guest's address is confirmed first (review round 1 of #235): the guest
 *   gets a short email with a one-time link and no conversation content;
 *   the conversation goes out only when that link is opened, so the
 *   transcript only ever reaches a mailbox that asked for it. The request
 *   carries a honeypot and a signed start time (FormGuard, shared with
 *   "Let Linker contact me"); a request that fails it is answered like a
 *   success and sends nothing.
 * - Every email of this kind counts against a site-wide daily cap and, per
 *   connection, an hourly limit (FormGuard's two RateLimits). Over either,
 *   the request is refused; nothing is queued for later.
 *
 * This class decides whether an email may go and to whom; the emails
 * themselves are the site's mail chain, owned by linker-commerce (every site
 * email is a WooCommerce email of that plugin, sent through its Outbox). The
 * two meet on SEND_FILTER and CONFIRM_FILTER, which answer true once the
 * email was handed to wp_mail().
 */
class ConversationMail {

	/**
	 * The outcomes, one definition (Proxy maps them to HTTP, the shell's
	 * `EmailOutcome` in src/genie/api/turn.ts names the same words).
	 */
	public const SENT        = 'sent';
	public const CONFIRM     = 'confirm';
	public const AWAITING    = 'pending';
	public const INVALID     = 'invalid';
	public const UNKNOWN     = 'unknown';
	public const EMPTY       = 'empty';
	public const THROTTLED   = 'throttled';
	public const CAPPED      = 'capped';
	public const EXPIRED     = 'expired';
	public const UNAVAILABLE = 'unavailable';

	/**
	 * The HTTP status of each outcome of a request.
	 */
	public const HTTP = array(
		self::SENT        => 200,
		self::CONFIRM     => 202,
		self::AWAITING    => 202,
		self::INVALID     => 400,
		self::UNKNOWN     => 404,
		self::EMPTY       => 409,
		self::THROTTLED   => 429,
		self::CAPPED      => 429,
		self::UNAVAILABLE => 503,
	);

	/**
	 * The filter linker-commerce answers with the conversation email:
	 * `( false, array{conversation_id, to, locale, messages} ) → bool|array{status: string}`.
	 */
	public const SEND_FILTER = 'linker_tools_genie_send_conversation';

	/**
	 * The filter linker-commerce answers with the address confirmation:
	 * `( false, array{to, locale, link, hours} ) → bool`.
	 */
	public const CONFIRM_FILTER = 'linker_tools_genie_confirm_address';

	/**
	 * The admin-post action the confirmation link opens.
	 */
	public const CONFIRM_ACTION = 'linker_tools_genie_email';

	/**
	 * The query argument the workspace is opened with after the link: the
	 * outcome, which the shell shows.
	 */
	public const RESULT_ARG = 'genie_email';

	/**
	 * Post meta: the pending confirmation of a guest's address.
	 */
	public const PENDING  = 'linker_genie_email_pending';
	public const ACCEPTED = 'linker_genie_email_accepted';

	/**
	 * Emails one connection may ask for per hour: the contact form's
	 * allowance (Linker\Commerce\Contact\Handler::LIMIT, 3 per hour).
	 */
	public const LIMIT = 3;

	/**
	 * Emails of this kind the whole site sends per day: a tenth of the
	 * host's 100 emails in 24 hours (AGENTS.md §4, mail), which four sites
	 * share. Inquiry, approval and contact mail keep the rest.
	 */
	public const DAILY_CAP = 10;

	/**
	 * How long a confirmation link works: WordPress's own lifetime of an
	 * emailed one-time link, the password reset key (DAY_IN_SECONDS,
	 * `password_reset_expiration`, wp-includes/user.php).
	 */
	public const LINK_LIFETIME = DAY_IN_SECONDS;

	/**
	 * The bot guard and the limits of this door (FormGuard).
	 *
	 * @var FormGuard
	 */
	private readonly FormGuard $guard;

	/**
	 * Sets up the sender.
	 *
	 * @param Conversations  $conversations Who may use which conversation.
	 * @param Thread         $thread        The stored conversation.
	 * @param RateLimit|null $connection    Per-connection hourly limit; the default when omitted.
	 * @param RateLimit|null $site          Site-wide daily cap; the default when omitted.
	 */
	public function __construct(
		private readonly Conversations $conversations,
		private readonly Thread $thread,
		?RateLimit $connection = null,
		?RateLimit $site = null
	) {
		$this->guard = self::guard( $connection, $site );
	}

	/**
	 * Adds the confirmation link's handler (guests and signed-in alike:
	 * the link may be opened in any browser).
	 */
	public function register(): void {
		add_action( 'admin_post_nopriv_' . self::CONFIRM_ACTION, array( $this, 'handle_link' ) );
		add_action( 'admin_post_' . self::CONFIRM_ACTION, array( $this, 'handle_link' ) );
		add_filter( 'linker_commerce_conversation_mail_source_current', array( $this, 'source_current' ), 10, 3 );
	}

	/**
	 * Rechecks a queued copy against the native stored source, without a browser session.
	 *
	 * This is source continuity only: Commerce separately owns recipient, immutable
	 * Message and classification authorization. A guest confirmation token can be
	 * opened from a different browser and is not replaced by session ownership.
	 *
	 * @param mixed                      $current Earlier result, not an authorization.
	 * @param int                        $id Native conversation post ID.
	 * @param list<array<string, mixed>> $messages Frozen complete transcript.
	 */
	public function source_current( mixed $current, int $id, array $messages ): bool {
		unset( $current );
		$post = get_post( $id );
		return $post instanceof \WP_Post && Conversations::POST_TYPE === $post->post_type &&
			'private' === $post->post_status && ! ( new Retention( dirname( __DIR__, 2 ) . '/linker-tools.php' ) )->is_deletable( $id ) &&
			array() !== $messages && $messages === $this->thread->transcript( $id );
	}

	/**
	 * The signed start time a guest's request carries back: when the page
	 * with the form was made, and a signature over it (FormGuard::stamp()).
	 *
	 * @param int|null $at Unix time of the stamp; now when omitted.
	 * @return array{started: string, nonce: string}
	 */
	public static function stamp( ?int $at = null ): array {
		return self::guard()->stamp( $at );
	}

	/**
	 * This door's guard: its name and its sourced caps (LIMIT, DAILY_CAP).
	 *
	 * @param RateLimit|null $connection The hourly limit; the default when omitted.
	 * @param RateLimit|null $site       The daily cap; the default when omitted.
	 */
	private static function guard( ?RateLimit $connection = null, ?RateLimit $site = null ): FormGuard {
		return new FormGuard( 'genie_mail', self::LIMIT, self::DAILY_CAP, $connection, $site );
	}

	/**
	 * Sends one conversation to the visitor, or asks a guest to confirm the
	 * address first.
	 *
	 * @param int                  $id      Conversation post ID.
	 * @param string               $address The address a guest typed; a signed-in customer's is the account's.
	 * @param string               $locale  `en` or `de`, the page's language.
	 * @param array<string, mixed> $guard   A guest's `website`, `started` and `started_nonce`.
	 * @return array{status: string, to: string} The outcome, and the address it concerns.
	 */
	public function send( int $id, string $address, string $locale, array $guard = array() ): array {
		if ( ! $this->conversations->may_use( $id ) ) {
			return self::outcome( self::UNKNOWN );
		}
		if ( array() === $this->thread->transcript( $id ) ) {
			return self::outcome( self::EMPTY );
		}
		if ( is_user_logged_in() ) {
			$user = wp_get_current_user();
			$to   = is_email( $user->user_email ) ? (string) $user->user_email : '';
			if ( '' === $to ) {
				return self::outcome( self::INVALID );
			}
			$refused = $this->take();
			return '' !== $refused ? self::outcome( $refused ) : $this->deliver( $id, $to, $locale );
		}
		$to = strtolower( trim( $address ) );
		if ( ! is_email( $to ) ) {
			return self::outcome( self::INVALID );
		}
		if ( ! $this->guard->passes( $guard ) ) {
			// Answered like a real request, so a bot learns nothing.
			return self::outcome( self::CONFIRM, $to );
		}
		$refused = $this->take();
		if ( '' !== $refused ) {
			return self::outcome( $refused );
		}
		return $this->ask_to_confirm( $id, $to, $locale );
	}

	/**
	 * Opens a confirmation link: sends the conversation to the confirmed
	 * address once, then the link is spent.
	 *
	 * @param string $token The link's `id.secret`.
	 * @return array{status: string, locale: string}
	 */
	public function confirm( string $token ): array {
		if ( 1 !== preg_match( '/^(\d+)\.([0-9a-f]{64})$/', $token, $parts ) ) {
			return self::result( self::EXPIRED, 'en' );
		}
		$id     = (int) $parts[1];
		$result = self::result( self::UNAVAILABLE, 'en' );
		$this->confirmation_lock(
			$id,
			function () use ( $id, $parts, &$result ): void {
				clean_post_cache( $id );
				$pending = Conversations::POST_TYPE === get_post_type( $id ) ? get_post_meta( $id, self::PENDING, true ) : '';
				if ( ! is_array( $pending ) || ! is_string( $pending['hash'] ?? null ) || ! hash_equals( $pending['hash'], hash( 'sha256', $parts[2] ) ) ) {
					$result = self::result( self::EXPIRED, 'en' );
					return;
				}
				$locale = 'de' === ( $pending['locale'] ?? '' ) ? 'de' : 'en';
				if ( (int) ( $pending['expires'] ?? 0 ) < time() ) {
					delete_post_meta( $id, self::PENDING, $pending );
					$result = self::result( self::EXPIRED, $locale );
					return;
				}
				if ( ! $this->guard->take_site() ) {
					$result = self::result( self::CAPPED, $locale );
					return;
				}
				// This native closure is never populated from an HTTP request. The
				// commerce bridge executes it in the original job's transaction.
				$accepted = static function ( int $job ) use ( $id, $pending ): void {
					global $wpdb;
					// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Final original-source row lock inside the native JobStore transaction.
					$row = $wpdb->get_var( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE ID=%d AND post_type=%s FOR UPDATE NOWAIT", $id, Conversations::POST_TYPE ) );
					$wpdb->get_col( $wpdb->prepare( "SELECT meta_id FROM {$wpdb->postmeta} WHERE post_id=%d AND meta_key=%s FOR UPDATE NOWAIT", $id, self::PENDING ) );
					// phpcs:enable
					clean_post_cache( $id );
					if ( (int) $row !== $id || get_post_meta( $id, self::PENDING, true ) !== $pending || ! delete_post_meta( $id, self::PENDING, $pending ) ) {
						throw new \RuntimeException( 'conversation_confirmation_source_changed' );
					}
					$receipt = array(
						'hash' => $pending['hash'],
						'job'  => $job,
					);
					update_post_meta( $id, self::ACCEPTED, $receipt );
					wp_cache_delete( $id, 'post_meta' );
					if ( metadata_exists( 'post', $id, self::PENDING ) || get_post_meta( $id, self::ACCEPTED, true ) !== $receipt ) {
						throw new \RuntimeException( 'conversation_confirmation_ack_failed' );
					}
				};
				$status   = $this->deliver( $id, (string) ( $pending['to'] ?? '' ), $locale, $accepted )['status'];
				$result   = self::result( $status, $locale );
			}
		);
		return $result;
	}

	/**
	 * Independent connection-owned confirmation mutex; no model, SMTP or outer commit.
	 *
	 * @param int      $id Native conversation.
	 * @param callable $work Source validation and original-job handoff only.
	 */
	private function confirmation_lock( int $id, callable $work ): void {
		global $wpdb;
		$database = is_string( $wpdb->dbname ?? null ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		$name     = 'linker-conversation-mail-' . md5( $database . '/' . $wpdb->prefix . '/' . $id );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Connection-owned bounded mutex, following Thread's native DB namespace.
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 1)', $name ) ) ) {
			return;
		}
		try {
			$work();
		} finally {
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
		}
		// phpcs:enable
	}

	/**
	 * The confirmation link's handler: confirms, then opens Genie's page in
	 * the email's language with the outcome. Runs on admin-post.
	 */
	public function handle_link(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the token is the credential; a nonce cannot travel in an email to another browser.
		$token  = isset( $_GET['token'] ) ? sanitize_text_field( wp_unslash( (string) $_GET['token'] ) ) : '';
		$result = $this->confirm( $token );
		wp_safe_redirect( add_query_arg( self::RESULT_ARG, $result['status'], Entries::workspace_url_for( $result['locale'] ) ) );
		exit;
	}

	/**
	 * The per-connection limit and the site's daily cap, taken together.
	 *
	 * @return string '' when both allow, else the refusal.
	 */
	private function take(): string {
		return match ( $this->guard->take() ) {
			'connection' => self::THROTTLED,
			'site'       => self::CAPPED,
			default      => '',
		};
	}

	/**
	 * Hands the conversation to linker-commerce's email.
	 *
	 * @param int           $id     Conversation post ID.
	 * @param string        $to     The address.
	 * @param string        $locale `en` or `de`.
	 * @param callable|null $accepted Trusted native confirmation ACK in the same publication transaction.
	 * @return array{status: string, to: string}
	 */
	private function deliver( int $id, string $to, string $locale, ?callable $accepted = null ): array {
		$messages = $this->thread->transcript( $id );
		if ( '' === $to || array() === $messages ) {
			return self::outcome( self::UNAVAILABLE );
		}
		/**
		 * Sends a Genie conversation to the visitor's own address.
		 *
		 * The commerce plugin answers with its customer email; without it
		 * nothing answers and the conversation is not sent.
		 *
			 * @param bool|array<string, string> $sent False until accepted; pending means saved for automatic checks.
			 * @param array<string, mixed>       $email Native conversation ID, to, locale and messages.
		 * @since 0.2.0
		 */
		$sent = apply_filters(
			'linker_tools_genie_send_conversation',
			false,
			array(
				'conversation_id' => $id,
				'accepted'        => $accepted,
				'to'              => $to,
				'locale'          => self::wp_locale( $locale ),
				'messages'        => $messages,
			)
		);
		if ( null !== $accepted && metadata_exists( 'post', $id, self::PENDING ) ) {
			return self::outcome( self::UNAVAILABLE ); }
		if ( is_array( $sent ) && self::AWAITING === ( $sent['status'] ?? '' ) ) {
			return self::outcome( self::AWAITING, $to );
		}
		return true === $sent ? self::outcome( self::SENT, $to ) : self::outcome( self::UNAVAILABLE );
	}

	/**
	 * Stores a pending confirmation and sends its link.
	 *
	 * @param int    $id     Conversation post ID.
	 * @param string $to     The guest's address.
	 * @param string $locale `en` or `de`.
	 * @return array{status: string, to: string}
	 */
	private function ask_to_confirm( int $id, string $to, string $locale ): array {
		if ( Resources::verified() ) {
			/**
			 * Native server-only admission context.
			 *
			 * @since 0.2.0
			 */
			$context = apply_filters( 'linker_commerce_public_business_context', null ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Commerce owns the shared trusted callback seam.

			$reference = is_array( $context ) ? (string) ( $context['id'] ?? '' ) : '';
			/**
			 * The shared Commerce optional-receipt budget owns recipient/site limits.
			 * A missing dependency fails closed before any secret or email is made.
			 *
			 * @since 0.2.0
			 */
			$reason = '' === $reference ? null : apply_filters( 'linker_commerce_receipt_budget_reason', null, $to, $reference, 'conversation_confirmation' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Commerce owns the optional receipt policy.
			if ( '' !== $reason ) {
				return self::outcome( self::UNAVAILABLE );
			}
		}
		$secret = bin2hex( random_bytes( 32 ) );
		update_post_meta(
			$id,
			self::PENDING,
			array(
				'hash'    => hash( 'sha256', $secret ),
				'to'      => $to,
				'locale'  => $locale,
				'expires' => time() + self::LINK_LIFETIME,
			)
		);
		$link = add_query_arg(
			array(
				'action' => self::CONFIRM_ACTION,
				'token'  => $id . '.' . $secret,
			),
			admin_url( 'admin-post.php' )
		);
		/**
		 * Asks a guest to confirm the address a conversation goes to.
		 *
		 * The commerce plugin answers with a short fixed email carrying the
		 * link; it holds nothing of the conversation.
		 *
		 * @param bool                 $sent  False until an email took it.
		 * @param array<string, mixed> $email to, locale (a WordPress locale), link, hours (the link's lifetime).
		 * @since 0.2.0
		 */
		$sent = apply_filters(
			'linker_tools_genie_confirm_address',
			false,
			array(
				'to'     => $to,
				'locale' => self::wp_locale( $locale ),
				'link'   => $link,
				'hours'  => intdiv( self::LINK_LIFETIME, HOUR_IN_SECONDS ),
			)
		);
		if ( true !== $sent ) {
			delete_post_meta( $id, self::PENDING );
			return self::outcome( self::UNAVAILABLE );
		}
		return self::outcome( self::CONFIRM, $to );
	}

	/**
	 * The WordPress locale of an email.
	 *
	 * @param string $locale `en` or `de`.
	 */
	private static function wp_locale( string $locale ): string {
		return 'de' === $locale ? 'de_DE_formal' : 'en_US';
	}

	/**
	 * One outcome of send().
	 *
	 * @param string $status One of the outcome constants.
	 * @param string $to     The address it concerns, when there is one.
	 * @return array{status: string, to: string}
	 */
	private static function outcome( string $status, string $to = '' ): array {
		return array(
			'status' => $status,
			'to'     => $to,
		);
	}

	/**
	 * One outcome of confirm().
	 *
	 * @param string $status One of the outcome constants.
	 * @param string $locale `en` or `de`, the email's language.
	 * @return array{status: string, locale: string}
	 */
	private static function result( string $status, string $locale ): array {
		return array(
			'status' => $status,
			'locale' => $locale,
		);
	}
}
