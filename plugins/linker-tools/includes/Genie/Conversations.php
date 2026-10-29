<?php
/**
 * Conversation posts for Genie (anonymous cookie, then the logged-in user).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Stores threads as `linker_conversation` posts. No custom table
 * (docs/specs/13-genie.md). A guest's conversations belong to the browser
 * that opened them: a random browser key in a cookie, whose hash every guest
 * conversation of that browser carries. Signing in assigns all of them to
 * the user, so they follow the account to any device (ticket #235).
 */
class Conversations {

	/**
	 * Custom post type.
	 */
	public const POST_TYPE = 'linker_conversation';

	/**
	 * Cookie that names the guest's conversation post.
	 *
	 * The value is `id.signature`, not the id. A number alone is not a
	 * credential: anyone who can set a cookie could name another guest's post.
	 */
	public const COOKIE = 'linker_conversation';

	/**
	 * Cookie that holds this browser's key: 32 hex characters, random.
	 *
	 * The key itself is the secret: only its hash is stored on the
	 * conversations (BROWSER_META), so reading the database does not hand
	 * out a cookie that opens them.
	 */
	public const BROWSER_COOKIE = 'linker_genie_browser';

	/**
	 * The actions the two cookie writes fire (dispatch()); register() hangs
	 * the header writers on them.
	 */
	public const COOKIE_ACTION  = 'linker_tools_set_conversation_cookie';
	public const BROWSER_ACTION = 'linker_tools_set_genie_browser_cookie';

	/**
	 * Post meta: the sha256 of the key of the browser that opened a guest
	 * conversation. Removed when the conversation is claimed by an account.
	 */
	public const BROWSER_META = 'linker_genie_browser';

	/**
	 * Option-name prefix for a cold tab's browser-key claim.
	 *
	 * Not autoloaded and not the durable browser secret on a conversation.
	 * Tests delete rows with this prefix.
	 */
	public const BROWSER_CLAIM_PREFIX = 'linker_genie_browser_claim_';

	/**
	 * Seconds a cookieless sibling may adopt the key minted for this tab.
	 *
	 * The client can send the second entry-context before it has stored
	 * this response's Set-Cookie. Five seconds is that client's auxiliary
	 * identity budget (nativeScope.ts CONTEXT_BUDGET_MS). The window also
	 * ends when any request presents the browser cookie: that epoch is
	 * established, and a later cookieless request on this tab is a new
	 * guest. A request that already has a browser cookie never reads this
	 * claim.
	 */
	private const BROWSER_CLAIM_SECONDS = 5;

	/**
	 * Title of a conversation that has not been named by its first message.
	 */
	public const UNTITLED = 'Genie';

	/**
	 * How many conversations the history rail lists. A customer who scrolls
	 * further than this is browsing, not continuing a job; the current
	 * conversation is always included even when it is older than the cut.
	 */
	public const LIST_LIMIT = 40;

	/**
	 * Whether this request is a User Switching switch (switching()).
	 *
	 * @var bool
	 */
	private bool $switching = false;

	/**
	 * Registers the post type; runs on init.
	 */
	public function register(): void {
		register_post_type(
			self::POST_TYPE,
			array(
				'label'        => 'Genie conversations',
				'public'       => false,
				'show_ui'      => false,
				'supports'     => array( 'title' ),
				'can_export'   => false,
				'rewrite'      => false,
				'query_var'    => false,
				'capabilities' => array(
					'create_posts' => 'read',
				),
			)
		);
		// The writer of the guest cookie: set_cookie() fires the action, this
		// listener sends the header. Without it every turn would open a new
		// conversation post, because the next request would find no cookie.
		add_action( self::COOKIE_ACTION, array( $this, 'send_cookie' ), 10, 5 );
		add_action( self::BROWSER_ACTION, array( $this, 'send_browser_cookie' ), 10, 5 );
		add_action( 'wp_login', array( $this, 'claim' ), 10, 2 );
		// WooCommerce signs a new account in through wp_set_auth_cookie(),
		// which does not fire wp_login; the cookie it sets is the one moment
		// both paths share.
		add_action( 'set_logged_in_cookie', array( $this, 'claim_on_sign_in' ), 10, 4 );
		// User Switching (installed on live for staff) sets or clears its
		// old-user cookie right before it sets the auth cookie of the user
		// it switches to (user-switching.php, switch_to_user()). That auth
		// cookie is no sign-in of this browser's guest.
		add_action( 'set_olduser_cookie', array( $this, 'switching' ) );
		add_action( 'clear_olduser_cookie', array( $this, 'switching' ) );
		add_action( 'wp_logout', array( $this, 'signed_out' ) );
	}

	/**
	 * Sends the browser-key header (the `linker_tools_set_genie_browser_cookie`
	 * listener).
	 *
	 * @param string $value  Browser key.
	 * @param int    $expire Expiry timestamp.
	 * @param string $path   Cookie path.
	 * @param string $domain Cookie domain.
	 * @param bool   $secure HTTPS only.
	 */
	public function send_browser_cookie( string $value, int $expire, string $path, string $domain, bool $secure ): void {
		$this->send_header(
			self::BROWSER_COOKIE,
			$value,
			array(
				'expires'  => $expire,
				'path'     => $path,
				'domain'   => $domain,
				'secure'   => $secure,
				'httponly' => true,
				'samesite' => 'Lax',
			)
		);
	}

	/**
	 * Sends the guest-cookie header (the `linker_tools_set_conversation_cookie`
	 * listener).
	 *
	 * @param string $value  Conversation post ID.
	 * @param int    $expire Expiry timestamp.
	 * @param string $path   Cookie path.
	 * @param string $domain Cookie domain.
	 * @param bool   $secure HTTPS only.
	 */
	public function send_cookie( string $value, int $expire, string $path, string $domain, bool $secure ): void {
		$this->send_header(
			self::COOKIE,
			$value,
			array(
				'expires'  => $expire,
				'path'     => $path,
				'domain'   => $domain,
				'secure'   => $secure,
				'httponly' => true,
				'samesite' => 'Lax',
			)
		);
	}

	/**
	 * The header write, on one seam for the tests.
	 *
	 * @param string               $name    Cookie name.
	 * @param string               $value   Cookie value.
	 * @param array<string, mixed> $options setcookie() options.
	 */
	protected function send_header( string $name, string $value, array $options ): bool {
		return setcookie( $name, $value, $options );
	}

	/**
	 * The conversation ID for this request: existing cookie or post, else a new one.
	 */
	public function current_id(): int {
		$id = $this->from_cookie();
		if ( $id > 0 && $this->may_use( $id ) ) {
			return $id;
		}
		if ( is_user_logged_in() ) {
			$owned = get_posts(
				array(
					'post_type'      => self::POST_TYPE,
					'post_status'    => 'private',
					'author'         => get_current_user_id(),
					'posts_per_page' => 1,
					'orderby'        => 'date',
					'order'          => 'DESC',
					'fields'         => 'ids',
				)
			);
			if ( array() !== $owned ) {
				$id = (int) $owned[0];
				$this->set_cookie( $id );
				return $id;
			}
		}
		return $this->open();
	}

	/**
	 * The conversation this request already has, 0 when it has none.
	 *
	 * `current_id()` opens one when there is none, which is what a turn needs
	 * and a page view must not do: reading the thread back must never mint a
	 * conversation post.
	 */
	public function existing_id(): int {
		$id = $this->selected_id();
		if ( $id > 0 ) {
			return $id;
		}
		if ( ! is_user_logged_in() ) {
			return 0;
		}
		$owned = get_posts(
			array(
				'post_type'      => self::POST_TYPE,
				'post_status'    => 'private',
				'author'         => get_current_user_id(),
				'posts_per_page' => 1,
				'orderby'        => 'date',
				'order'          => 'DESC',
				'fields'         => 'ids',
			)
		);
		return array() === $owned ? 0 : (int) $owned[0];
	}

	/** Only the authenticated browser-selected thread, without account-history fallback. */
	public function selected_id(): int {
		$id = $this->from_cookie();
		return $id > 0 && $this->may_use( $id ) ? $id : 0;
	}

	/**
	 * The conversations this visitor may continue, newest first.
	 *
	 * A guest has every conversation this browser opened (its browser key)
	 * and the one its conversation cookie names. A signed-in customer has
	 * every conversation post they own, on any device. The current one is
	 * always present, so switching away and back never drops the thread the
	 * cookie names. Reading the list never opens a conversation.
	 *
	 * @return list<array{id: int, title: string, updated: string}>
	 */
	public function list_for_visitor(): array {
		$current = $this->from_cookie();
		if ( $current > 0 && ! $this->may_use( $current ) ) {
			$current = 0;
		}
		// Most recent activity first (Thread::ACTIVITY: opened, or the last
		// answered turn). Naming a conversation and claiming it at sign-in
		// rewrite the post's modified date, never this. A conversation from
		// before the meta existed has none and sorts after, by start.
		$activity = array(
			'relation' => 'OR',
			'activity' => array(
				'key'     => Thread::ACTIVITY,
				'type'    => 'NUMERIC',
				'compare' => 'EXISTS',
			),
			array(
				'key'     => Thread::ACTIVITY,
				'compare' => 'NOT EXISTS',
			),
		);
		$query    = array(
			'post_type'      => self::POST_TYPE,
			'post_status'    => 'private',
			'posts_per_page' => self::LIST_LIMIT,
			'orderby'        => array(
				'activity' => 'DESC',
				'date'     => 'DESC',
				'ID'       => 'DESC',
			),
			'fields'         => 'ids',
			'meta_query'     => array( $activity ), // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- the list's order; LIST_LIMIT bounds it.
		);
		$ids      = array();
		if ( is_user_logged_in() ) {
			$query['author'] = get_current_user_id();
		} else {
			$browser = $this->browser_key();
			// A browser without a key has no conversation of its own; the
			// meta query must not run with an empty value, which would
			// match every guest conversation without one.
			if ( '' === $browser ) {
				$query = array();
			} else {
				$query['meta_query'] = array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- the browser's own conversations; LIST_LIMIT bounds it.
					'relation' => 'AND',
					$activity,
					array(
						'key'   => self::BROWSER_META,
						'value' => self::hash( $browser ),
					),
				);
			}
		}
		if ( array() !== $query ) {
			foreach ( get_posts( $query ) as $id ) {
				$ids[] = (int) $id;
			}
		}
		if ( $current > 0 && ! in_array( $current, $ids, true ) ) {
			array_unshift( $ids, $current );
		}
		$ids  = array_slice( $ids, 0, self::LIST_LIMIT );
		$list = array();
		foreach ( $ids as $id ) {
			if ( ! $this->may_use( $id ) ) {
				continue;
			}
			$post = get_post( $id );
			if ( ! $post instanceof \WP_Post ) {
				continue;
			}
			$list[] = array(
				'id'      => $id,
				'title'   => '' !== $post->post_title ? $post->post_title : self::UNTITLED,
				'updated' => (string) $post->post_modified_gmt,
			);
		}
		return $list;
	}

	/**
	 * Makes one of this visitor's conversations the current one.
	 *
	 * The cookie is the one place a request names its conversation
	 * (`current_id()`, `existing_id()`), so the dock and the workspace
	 * share a thread by writing that cookie. A conversation the visitor
	 * may not use is refused; nothing is opened in its place.
	 *
	 * @param int $id Conversation post ID.
	 */
	public function activate( int $id ): bool {
		if ( $id < 1 || ! $this->may_use( $id ) ) {
			return false;
		}
		$this->set_cookie( $id );
		return true;
	}

	/**
	 * Names a conversation after its first customer message.
	 *
	 * The history rail has nothing else to show: a conversation post is
	 * created as "Genie", and the first message is the title the customer
	 * will recognise. A later turn does not rename it.
	 *
	 * @param int    $id    Conversation post ID.
	 * @param string $title First message, already trimmed.
	 */
	public function title_from_first_message( int $id, string $title ): void {
		if ( $id < 1 || '' === $title ) {
			return;
		}
		$post = \get_post( $id );
		if ( ! $post instanceof \WP_Post || self::UNTITLED !== $post->post_title ) {
			return;
		}
		wp_update_post(
			array(
				'ID'         => $id,
				'post_title' => $title,
			)
		);
	}

	/**
	 * A new conversation post, cookie set.
	 *
	 * A guest's conversation is marked with this browser's key, minted on
	 * the first one, so the next new conversation does not push it out of
	 * the list. A conversation the cookie named before the browser had a
	 * key is marked the same way first, for the same reason.
	 */
	public function open(): int {
		$logged_in = is_user_logged_in();
		$browser   = $logged_in ? '' : $this->ensure_browser_key();
		if ( '' !== $browser ) {
			$this->adopt_cookie_conversation( $browser );
		}
		$id = wp_insert_post(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => self::UNTITLED,
				'post_author' => $logged_in ? get_current_user_id() : 0,
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			return 0;
		}
		if ( '' !== $browser ) {
			update_post_meta( (int) $id, self::BROWSER_META, self::hash( $browser ) );
		}
		// Opening is activity: the new conversation heads the list until
		// another one has a newer turn.
		update_post_meta( (int) $id, Thread::ACTIVITY, time() );
		$this->set_cookie( (int) $id );
		return (int) $id;
	}

	/**
	 * Clears one of this visitor's conversations: the post goes, with its
	 * thread, so nothing of it is context for a later turn.
	 *
	 * Clearing the current conversation leaves the visitor with none; the
	 * next turn opens a new one.
	 *
	 * @param int $id Conversation post ID.
	 */
	public function delete( int $id ): bool {
		if ( $id < 1 || ! $this->may_use( $id ) ) {
			return false;
		}
		$current = $this->from_cookie();
		if ( ! wp_delete_post( $id, true ) ) {
			return false;
		}
		if ( $current === $id ) {
			$this->clear_cookie();
		}
		return true;
	}

	/**
	 * On login, the browser's guest conversations become the user's.
	 *
	 * @param string   $login User login.
	 * @param \WP_User $user  User.
	 */
	public function claim( string $login, $user ): void {
		unset( $login );
		$this->claim_for( (int) $user->ID );
	}

	/**
	 * The same claim when the auth cookie is set without wp_login (a new
	 * WooCommerce account); runs on set_logged_in_cookie.
	 *
	 * @param string $cookie     Logged-in cookie value.
	 * @param int    $expire     Cookie expiry.
	 * @param int    $expiration Session expiry.
	 * @param int    $user_id    The user signed in.
	 */
	public function claim_on_sign_in( string $cookie, int $expire, int $expiration, int $user_id ): void {
		unset( $cookie, $expire, $expiration );
		if ( $this->switching ) {
			return;
		}
		$this->claim_for( $user_id );
	}

	/**
	 * Marks this request as a User Switching switch; runs on its
	 * set_olduser_cookie and clear_olduser_cookie actions.
	 */
	public function switching(): void {
		$this->switching = true;
	}

	/**
	 * After a sign-out the browser starts again as a new guest: a new key,
	 * and no current conversation. Runs on wp_logout.
	 */
	public function signed_out(): void {
		$this->clear_cookie();
		$this->write_browser_key( $this->new_browser_key() );
	}

	/**
	 * Gives the user every still-unowned conversation of this browser: the
	 * ones its browser key marks and the one its conversation cookie names.
	 * The browser mark goes with the claim; the account is what holds them
	 * from now on, on every device.
	 *
	 * @param int $user_id The user signed in.
	 */
	private function claim_for( int $user_id ): void {
		if ( $user_id < 1 ) {
			return;
		}
		$ids     = array();
		$browser = $this->browser_key();
		if ( '' !== $browser ) {
			foreach (
				get_posts(
					array(
						'post_type'      => self::POST_TYPE,
						'post_status'    => 'private',
						// Every one of them: a claim that stopped at a page
						// would leave the rest behind the browser.
						'posts_per_page' => -1,
						'fields'         => 'ids',
						'meta_key'       => self::BROWSER_META, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- the browser's own conversations, once per sign-in.
						'meta_value'     => self::hash( $browser ), // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- see meta_key.
					)
				) as $id
			) {
				$ids[] = (int) $id;
			}
		}
		$cookie = $this->from_cookie();
		if ( $cookie > 0 && $this->exists( $cookie ) ) {
			$ids[] = $cookie;
		}
		foreach ( array_unique( $ids ) as $id ) {
			if ( 0 !== (int) get_post_field( 'post_author', $id ) ) {
				continue;
			}
			wp_update_post(
				array(
					'ID'          => $id,
					'post_author' => $user_id,
				)
			);
			delete_post_meta( $id, self::BROWSER_META );
		}
		// The old key opened what the account now holds; the browser goes
		// on with a new one.
		if ( '' !== $browser ) {
			$this->write_browser_key( $this->new_browser_key() );
		}
	}

	/**
	 * Whether this request may use the conversation.
	 *
	 * A signed-in visitor may use a conversation they own. A still-unowned
	 * conversation is usable when this request's browser key opened it, or
	 * when the conversation cookie names it with a signature this site made.
	 * A numeric cookie is not that signature, and a key that opened nothing
	 * matches nothing.
	 *
	 * @param int $id Conversation post ID.
	 */
	public function may_use( int $id ): bool {
		if ( ! $this->exists( $id ) ) {
			return false;
		}
		$author = (int) get_post_field( 'post_author', $id );
		if ( is_user_logged_in() && get_current_user_id() === $author ) {
			return true;
		}
		if ( 0 !== $author ) {
			return false;
		}
		if ( $id === $this->from_cookie() ) {
			return true;
		}
		$browser = $this->browser_key();
		return '' !== $browser && hash_equals( (string) get_post_meta( $id, self::BROWSER_META, true ), self::hash( $browser ) );
	}

	/**
	 * Cookie value as a post ID, 0 when missing or unsigned.
	 *
	 * The cookie is `id.signature`. The signature is HMAC-SHA256 of the id
	 * with the site's auth salt, so a forged number does not name a post.
	 */
	private function from_cookie(): int {
		if ( ! isset( $_COOKIE[ self::COOKIE ] ) ) {
			return 0;
		}
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the signature check is the sanitizer; a value that does not verify is discarded.
		$raw = wp_unslash( $_COOKIE[ self::COOKIE ] );
		if ( ! is_string( $raw ) || ! str_contains( $raw, '.' ) ) {
			return 0;
		}
		[ $id, $signature ] = explode( '.', $raw, 2 );
		if ( ! ctype_digit( $id ) || '' === $signature ) {
			return 0;
		}
		$expected = $this->sign( $id );
		if ( ! hash_equals( $expected, $signature ) ) {
			return 0;
		}
		return (int) $id;
	}

	/**
	 * The cookie's signature for one conversation id.
	 *
	 * @param string $id Conversation post ID.
	 */
	private function sign( string $id ): string {
		return hash_hmac( 'sha256', self::COOKIE . '|' . $id, wp_salt( 'auth' ) );
	}

	/**
	 * Sets the guest cookie.
	 *
	 * The header is what the next request reads. PHP does not copy a
	 * Set-Cookie back into `$_COOKIE`, so a select or open in this request
	 * would still see the previous conversation (`existing_id()`,
	 * `current_id()`, `list_for_visitor()`). The same key is written here
	 * so those reads agree with the header for the rest of this request.
	 *
	 * @param int $id Conversation post ID.
	 */
	private function set_cookie( int $id ): void {
		if ( $id < 1 ) {
			return;
		}
		$value                   = $this->cookie_value( $id );
		$_COOKIE[ self::COOKIE ] = $value;
		$this->dispatch( self::COOKIE_ACTION, $value, $this->cookie_expire() );
	}

	/**
	 * Fires one cookie write; the listener registered on that action sends
	 * the header (send_cookie(), send_browser_cookie()).
	 *
	 * The two actions are `linker_tools_set_conversation_cookie` (the
	 * value is `id.signature`, the signature is what the next request
	 * checks) and `linker_tools_set_genie_browser_cookie` (the browser key).
	 * Both pass: value, expiry timestamp, cookie path, cookie domain, HTTPS
	 * only.
	 *
	 * @param non-empty-string $action COOKIE_ACTION or BROWSER_ACTION.
	 * @param string           $value  Cookie value; '' with a past expiry deletes it.
	 * @param int              $expire Expiry timestamp.
	 */
	private function dispatch( string $action, string $value, int $expire ): void {
		/**
		 * One of the two cookie writes documented above.
		 *
		 * @since 0.2.0
		 */
		do_action(
			$action, // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- one of the two linker_tools_set_* constants.
			$value,
			$expire,
			defined( 'COOKIEPATH' ) ? COOKIEPATH : '/',
			defined( 'COOKIE_DOMAIN' ) ? COOKIE_DOMAIN : '',
			is_ssl()
		);
	}

	/**
	 * The signed cookie value for one conversation.
	 *
	 * @param int $id Conversation post ID.
	 */
	private function cookie_value( int $id ): string {
		return $id . '.' . $this->sign( (string) $id );
	}

	/**
	 * When the guest cookies expire: as long as the site keeps a guest's
	 * conversation (Retention::RETENTION_DAYS), so the browser does not lose
	 * the way to a conversation the site still holds. Each write starts the
	 * count again.
	 */
	protected function cookie_expire(): int {
		return time() + Retention::RETENTION_DAYS * DAY_IN_SECONDS;
	}

	/**
	 * Forgets the current conversation: the cookie is expired, and this
	 * request reads no current conversation either.
	 */
	private function clear_cookie(): void {
		unset( $_COOKIE[ self::COOKIE ] );
		$this->dispatch( self::COOKIE_ACTION, '', time() - YEAR_IN_SECONDS );
	}

	/**
	 * An irreversible current-identity comparison for same-tab entry recovery.
	 * No conversation or account data is returned and this grants no authority.
	 *
	 * @param string $tab Random tab identity, not a credential.
	 */
	public function entry_scope( string $tab ): string {
		$user = get_current_user_id();
		if ( $user > 0 ) {
			$principal = 'user:' . $user . ':' . wp_get_session_token();
		} else {
			$browser = $this->browser_key();
			// A read of an existing epoch sends no renewed Set-Cookie: a
			// delayed auxiliary response must not replace a newer browser
			// identity. Presenting the cookie closes the cold claim, so a
			// later cookieless request on this tab is a new guest. Two
			// first requests that both arrive without the cookie still
			// share one claimed key.
			if ( '' === $browser ) {
				$browser = $this->write_browser_key( $this->claimed_browser_key( $tab ) );
			} else {
				$this->close_browser_claim( $tab );
			}
			$principal = 'guest:' . $browser;
		}
		return hash_hmac( 'sha256', $tab . '|' . $principal, wp_salt( 'auth' ) );
	}

	/**
	 * Drops this tab's cold claim once a request presents a browser cookie.
	 *
	 * The claim only joins cookieless first requests that have not stored
	 * Set-Cookie yet. A presented cookie means that epoch is established.
	 * A later cookieless request on the same tab is a new guest, not a
	 * sibling of the mint. Without an option store there is no row to close.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function close_browser_claim( string $tab ): void {
		if ( ! $this->claim_store_available() ) {
			return;
		}
		$this->forget_browser_claim_cache( $tab );
		if ( '' === $this->read_browser_claim( $tab ) ) {
			return;
		}
		if ( ! $this->lock_browser_claim( $tab ) ) {
			$this->delete_browser_claim( $tab );
			return;
		}
		try {
			$this->delete_browser_claim( $tab );
		} finally {
			$this->unlock_browser_claim( $tab );
		}
	}

	/**
	 * Whether this process can close a claim row.
	 */
	private function claim_store_available(): bool {
		global $wpdb;
		return function_exists( 'delete_option' ) && is_object( $wpdb );
	}

	/**
	 * Removes this tab's claim so the next cookieless read mints again.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function delete_browser_claim( string $tab ): void {
		$this->forget_browser_claim_cache( $tab );
		delete_option( $this->browser_claim_option( $tab ) );
		$this->forget_browser_claim_cache( $tab );
	}

	/**
	 * One browser key for every cookieless first request of this tab.
	 *
	 * The browser has not stored Set-Cookie yet, so the sibling request
	 * cannot present the key. The claim is the shared read. An existing
	 * cookie is never passed here.
	 *
	 * @param string $tab Client tab identity, the only correlator the two requests share.
	 */
	private function claimed_browser_key( string $tab ): string {
		$existing = $this->read_browser_claim( $tab );
		if ( '' !== $existing ) {
			return $existing;
		}
		if ( ! $this->lock_browser_claim( $tab ) ) {
			$this->forget_browser_claim_cache( $tab );
			$existing = $this->read_browser_claim( $tab );
			return '' !== $existing ? $existing : $this->publish_browser_claim( $tab, $this->new_browser_key() );
		}
		try {
			$this->forget_browser_claim_cache( $tab );
			$existing = $this->read_browser_claim( $tab );
			if ( '' !== $existing ) {
				return $existing;
			}
			return $this->publish_browser_claim( $tab, $this->new_browser_key() );
		} finally {
			$this->unlock_browser_claim( $tab );
		}
	}

	/**
	 * The unexpired key claimed for this tab, or '' when there is none.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function read_browser_claim( string $tab ): string {
		$stored = get_option( $this->browser_claim_option( $tab ), false );
		if ( ! is_array( $stored ) ) {
			return '';
		}
		$key   = $stored['key'] ?? '';
		$until = $stored['until'] ?? 0;
		if ( ! is_string( $key ) || 1 !== preg_match( '/^[0-9a-f]{32}$/', $key ) ) {
			return '';
		}
		if ( ! is_numeric( $until ) || (int) $until < time() ) {
			return '';
		}
		return $key;
	}

	/**
	 * Publishes one key for this tab. A lost insert reads the key that won.
	 *
	 * @param string $tab Client tab identity.
	 * @param string $key 32 hex characters.
	 */
	private function publish_browser_claim( string $tab, string $key ): string {
		$name  = $this->browser_claim_option( $tab );
		$value = array(
			'key'   => $key,
			'until' => time() + self::BROWSER_CLAIM_SECONDS,
		);
		$this->forget_browser_claim_cache( $tab );
		if ( add_option( $name, $value, '', false ) ) {
			return $key;
		}
		$this->forget_browser_claim_cache( $tab );
		$existing = $this->read_browser_claim( $tab );
		if ( '' !== $existing ) {
			return $existing;
		}
		update_option( $name, $value, false );
		return $key;
	}

	/**
	 * Drops a miss recorded before the sibling's insert committed.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function forget_browser_claim_cache( string $tab ): void {
		$name = $this->browser_claim_option( $tab );
		wp_cache_delete( $name, 'options' );
		wp_cache_delete( 'notoptions', 'options' );
	}

	/**
	 * Option name for this tab's claim. Not autoloaded.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function browser_claim_option( string $tab ): string {
		return self::BROWSER_CLAIM_PREFIX . substr( hash( 'sha256', $tab ), 0, 32 );
	}

	/**
	 * Serialises the cold mint. GET_LOCK is server-wide, so the name includes
	 * the database. Names are at most 64 characters (MySQL 8.0 reference
	 * manual, GET_LOCK); the sha256 is 64 hex characters.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function lock_browser_claim( string $tab ): bool {
		global $wpdb;
		$name = $this->browser_claim_lock_name( $tab );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- named lock, not table data.
		$got = $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $name, self::BROWSER_CLAIM_SECONDS ) );
		return '1' === (string) $got;
	}

	/**
	 * Releases the cold-mint lock acquired by this connection.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function unlock_browser_claim( string $tab ): void {
		global $wpdb;
		$name = $this->browser_claim_lock_name( $tab );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- releases the named lock lock_browser_claim() acquired.
		$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
	}

	/**
	 * The MySQL name of this tab's cold-mint lock.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function browser_claim_lock_name( string $tab ): string {
		global $wpdb;
		$database = '';
		if ( isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) && '' !== $wpdb->dbname ) {
			$database = $wpdb->dbname;
		} elseif ( defined( 'DB_NAME' ) ) {
			$database = (string) constant( 'DB_NAME' );
		}
		$prefix = isset( $wpdb->prefix ) && is_string( $wpdb->prefix ) ? $wpdb->prefix : '';
		return hash( 'sha256', $database . '/' . $prefix . self::BROWSER_CLAIM_PREFIX . $tab );
	}

	/**
	 * This browser's key, '' when it has none.
	 */
	private function browser_key(): string {
		if ( ! isset( $_COOKIE[ self::BROWSER_COOKIE ] ) ) {
			return '';
		}
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the format check is the sanitizer; anything else is no key.
		$raw = wp_unslash( $_COOKIE[ self::BROWSER_COOKIE ] );
		return is_string( $raw ) && 1 === preg_match( '/^[0-9a-f]{32}$/', $raw ) ? $raw : '';
	}

	/**
	 * This browser's key, minted and sent when it has none. Each call sends
	 * the cookie again, so its expiry runs from the newest conversation.
	 */
	private function ensure_browser_key(): string {
		$key = $this->browser_key();
		return $this->write_browser_key( '' === $key ? $this->new_browser_key() : $key );
	}

	/**
	 * Sets this browser's key, for the header and for the rest of this request.
	 *
	 * @param string $key Browser key.
	 */
	private function write_browser_key( string $key ): string {
		$_COOKIE[ self::BROWSER_COOKIE ] = $key;
		$this->dispatch( self::BROWSER_ACTION, $key, $this->cookie_expire() );
		return $key;
	}

	/**
	 * A fresh browser key: 128 random bits, as hex.
	 */
	protected function new_browser_key(): string {
		return bin2hex( random_bytes( 16 ) );
	}

	/**
	 * Marks the conversation the cookie names with this browser's key, when
	 * it is a guest conversation without a mark (opened before browsers had
	 * keys).
	 *
	 * @param string $browser This browser's key.
	 */
	private function adopt_cookie_conversation( string $browser ): void {
		$id = $this->from_cookie();
		if ( $id < 1 || ! $this->exists( $id ) || 0 !== (int) get_post_field( 'post_author', $id ) ) {
			return;
		}
		if ( '' === (string) get_post_meta( $id, self::BROWSER_META, true ) ) {
			update_post_meta( $id, self::BROWSER_META, self::hash( $browser ) );
		}
	}

	/**
	 * What a conversation stores of a browser key.
	 *
	 * @param string $browser Browser key.
	 */
	private static function hash( string $browser ): string {
		return hash( 'sha256', $browser );
	}

	/**
	 * Whether the ID is a conversation post.
	 *
	 * @param int $id Post ID.
	 */
	private function exists( int $id ): bool {
		return self::POST_TYPE === get_post_type( $id );
	}
}
