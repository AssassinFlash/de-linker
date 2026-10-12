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
 * (docs/specs/13-genie.md). Guests are bound by a cookie; logging in
 * assigns the post to the user.
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
		add_action( 'linker_tools_set_conversation_cookie', array( $this, 'send_cookie' ), 10, 5 );
		add_action( 'wp_login', array( $this, 'claim' ), 10, 2 );
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
		$id = $this->from_cookie();
		if ( $id > 0 && $this->may_use( $id ) ) {
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

	/**
	 * The conversations this visitor may continue, newest first.
	 *
	 * A guest has one conversation: the cookie's. A signed-in customer has
	 * every conversation post they own, which is what the history rail
	 * lists. The current one is always present, so switching away and back
	 * never drops the thread the cookie names. Reading the list never
	 * opens a conversation.
	 *
	 * @return list<array{id: int, title: string, updated: string}>
	 */
	public function list_for_visitor(): array {
		$current = $this->from_cookie();
		if ( $current > 0 && ! $this->may_use( $current ) ) {
			$current = 0;
		}
		$ids = array();
		if ( is_user_logged_in() ) {
			$owned = get_posts(
				array(
					'post_type'      => self::POST_TYPE,
					'post_status'    => 'private',
					'author'         => get_current_user_id(),
					'posts_per_page' => self::LIST_LIMIT,
					'orderby'        => 'modified',
					'order'          => 'DESC',
					'fields'         => 'ids',
				)
			);
			foreach ( $owned as $id ) {
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
	 */
	public function open(): int {
		$author = is_user_logged_in() ? get_current_user_id() : 0;
		$id     = wp_insert_post(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => self::UNTITLED,
				'post_author' => $author,
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			return 0;
		}
		$this->set_cookie( (int) $id );
		return (int) $id;
	}

	/**
	 * On login, the guest conversation becomes the user's.
	 *
	 * @param string   $login User login.
	 * @param \WP_User $user  User.
	 */
	public function claim( string $login, $user ): void {
		unset( $login );
		$id = $this->from_cookie();
		if ( $id < 1 || ! $this->exists( $id ) ) {
			return;
		}
		$author = (int) get_post_field( 'post_author', $id );
		if ( 0 === $author && 0 < (int) $user->ID ) {
			wp_update_post(
				array(
					'ID'          => $id,
					'post_author' => (int) $user->ID,
				)
			);
		}
	}

	/**
	 * Whether this request may use the conversation.
	 *
	 * A signed-in visitor may use a conversation they own. A still-unowned
	 * conversation is usable only when this request's cookie names it with
	 * a signature this site made. A numeric cookie is not that signature.
	 * A guest may use only the unowned conversation their signed cookie names.
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
		return 0 === $author && $id === $this->from_cookie();
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
		/**
		 * Fires the guest-cookie write; the listener sends the header.
		 *
		 * The value is `id.signature`, not the id. The signature is what
		 * the next request checks.
		 *
		 * @param string $value  Signed conversation cookie.
		 * @param int    $expire Expiry timestamp.
		 * @param string $path   Cookie path.
		 * @param string $domain Cookie domain.
		 * @param bool   $secure HTTPS only.
		 * @since 0.1.0
		 */
		do_action(
			'linker_tools_set_conversation_cookie',
			$value,
			$this->cookie_expire(),
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
	 * When the guest cookie expires.
	 */
	protected function cookie_expire(): int {
		return time() + MONTH_IN_SECONDS;
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
