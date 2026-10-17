<?php
/**
 * Sending a conversation to the visitor's own mailbox.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * A visitor can have any of their conversations emailed to themselves
 * (docs/specs/13-genie.md, goal 7; acceptance A12).
 *
 * - A signed-in customer's goes to the account's address at once.
 * - A guest's address is confirmed first (review round 1 of #235): the guest
 *   gets a short email with a one-time link and no conversation content;
 *   the conversation goes out only when that link is opened, so the
 *   transcript only ever reaches a mailbox that asked for it. The request
 *   carries a honeypot and a signed start time, the inquiry and contact
 *   doors' guard; a request that fails it is answered like a success and
 *   sends nothing.
 * - Every email of this kind counts against a site-wide daily cap and, per
 *   connection, an hourly limit (RateLimit, one statement each). Over either,
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
		self::INVALID     => 400,
		self::UNKNOWN     => 404,
		self::EMPTY       => 409,
		self::THROTTLED   => 429,
		self::CAPPED      => 429,
		self::UNAVAILABLE => 503,
	);

	/**
	 * The filter linker-commerce answers with the conversation email:
	 * `( false, array{to, locale, messages} ) → bool`.
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
	public const PENDING = 'linker_genie_email_pending';

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
	 * Seconds a guest's request must come after the page that carries the
	 * form: the inquiry doors' fill-time floor (#246, 3 seconds).
	 */
	public const MIN_SECONDS = 3;

	/**
	 * How long a page's start time stays good: a WordPress nonce's
	 * lifetime (DAY_IN_SECONDS, `nonce_life`), which this stamp stands in for.
	 */
	public const STAMP_LIFETIME = DAY_IN_SECONDS;

	/**
	 * Per-connection hourly limit.
	 *
	 * @var RateLimit
	 */
	private readonly RateLimit $connection;

	/**
	 * Site-wide daily cap.
	 *
	 * @var RateLimit
	 */
	private readonly RateLimit $site;

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
		$this->connection = $connection ?? new RateLimit( 'genie_mail', self::LIMIT, HOUR_IN_SECONDS );
		$this->site       = $site ?? new RateLimit( 'genie_mail_day', self::DAILY_CAP, DAY_IN_SECONDS );
	}

	/**
	 * Adds the confirmation link's handler (guests and signed-in alike:
	 * the link may be opened in any browser).
	 */
	public function register(): void {
		add_action( 'admin_post_nopriv_' . self::CONFIRM_ACTION, array( $this, 'handle_link' ) );
		add_action( 'admin_post_' . self::CONFIRM_ACTION, array( $this, 'handle_link' ) );
	}

	/**
	 * The signed start time a guest's request carries back: when the page
	 * with the form was made, and a signature over it.
	 *
	 * The signature is an HMAC with the site's nonce salt, not a WordPress
	 * nonce: a guest's nonce follows WooCommerce's session cookie
	 * (`nonce_user_logged_out`), which the page may not have had yet when
	 * it was made and has by the time the guest sends (seen on g235: every
	 * guest request failed the nonce).
	 *
	 * @param int|null $at Unix time of the stamp; now when omitted.
	 * @return array{started: string, nonce: string}
	 */
	public static function stamp( ?int $at = null ): array {
		$started = (string) ( $at ?? time() );
		return array(
			'started' => $started,
			'nonce'   => self::signature( $started ),
		);
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
		if ( ! self::passes( $guard ) ) {
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
		$id      = (int) $parts[1];
		$pending = Conversations::POST_TYPE === get_post_type( $id ) ? get_post_meta( $id, self::PENDING, true ) : '';
		if ( ! is_array( $pending ) || ! is_string( $pending['hash'] ?? null ) || ! hash_equals( $pending['hash'], hash( 'sha256', $parts[2] ) ) ) {
			return self::result( self::EXPIRED, 'en' );
		}
		$locale = 'de' === ( $pending['locale'] ?? '' ) ? 'de' : 'en';
		if ( (int) ( $pending['expires'] ?? 0 ) < time() ) {
			delete_post_meta( $id, self::PENDING );
			return self::result( self::EXPIRED, $locale );
		}
		// Over today's cap the link stays good until it expires.
		if ( ! $this->site->take( '' ) ) {
			return self::result( self::CAPPED, $locale );
		}
		delete_post_meta( $id, self::PENDING );
		return self::result( $this->deliver( $id, (string) ( $pending['to'] ?? '' ), $locale )['status'], $locale );
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
		if ( ! $this->connection->take( self::connection() ) ) {
			return self::THROTTLED;
		}
		return $this->site->take( '' ) ? '' : self::CAPPED;
	}

	/**
	 * Hands the conversation to linker-commerce's email.
	 *
	 * @param int    $id     Conversation post ID.
	 * @param string $to     The address.
	 * @param string $locale `en` or `de`.
	 * @return array{status: string, to: string}
	 */
	private function deliver( int $id, string $to, string $locale ): array {
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
		 * @param bool                 $sent  False until an email took it.
		 * @param array<string, mixed> $email to, locale (a WordPress locale), messages.
		 * @since 0.2.0
		 */
		$sent = apply_filters(
			'linker_tools_genie_send_conversation',
			false,
			array(
				'to'       => $to,
				'locale'   => self::wp_locale( $locale ),
				'messages' => $messages,
			)
		);
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
	 * Whether a guest's request passes the bot guard: the honeypot empty,
	 * the start time signed by this site, at least MIN_SECONDS and at most
	 * STAMP_LIFETIME old.
	 *
	 * @param array<string, mixed> $guard `website`, `started`, `started_nonce`.
	 */
	private static function passes( array $guard ): bool {
		$started = $guard['started'] ?? '';
		$nonce   = $guard['started_nonce'] ?? '';
		$trap    = $guard['website'] ?? '';
		return '' === $trap
			&& is_string( $started ) && ctype_digit( $started )
			&& is_string( $nonce )
			&& time() - (int) $started >= self::MIN_SECONDS
			&& time() - (int) $started <= self::STAMP_LIFETIME
			&& hash_equals( self::signature( $started ), $nonce );
	}

	/**
	 * The signature of one start time.
	 *
	 * @param string $started Unix time, as sent.
	 */
	private static function signature( string $started ): string {
		return hash_hmac( 'sha256', 'linker_tools_genie_mail|' . $started, wp_salt( 'nonce' ) );
	}

	/**
	 * The address this connection came from, never a forwarded header a
	 * sender sets freely.
	 */
	private static function connection(): string {
		return isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
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
