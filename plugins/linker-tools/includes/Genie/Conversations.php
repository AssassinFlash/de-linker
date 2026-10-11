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
	 */
	public const COOKIE = 'linker_conversation';

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
	 * A new conversation post, cookie set.
	 */
	public function open(): int {
		$author = is_user_logged_in() ? get_current_user_id() : 0;
		$id     = wp_insert_post(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => 'Genie',
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
	 * @param int $id Conversation post ID.
	 */
	public function may_use( int $id ): bool {
		if ( ! $this->exists( $id ) ) {
			return false;
		}
		$author = (int) get_post_field( 'post_author', $id );
		if ( is_user_logged_in() ) {
			return 0 === $author || get_current_user_id() === $author;
		}
		return 0 === $author && $id === $this->from_cookie();
	}

	/**
	 * Cookie value as a post ID, 0 if missing.
	 */
	private function from_cookie(): int {
		if ( ! isset( $_COOKIE[ self::COOKIE ] ) ) {
			return 0;
		}
		return absint( wp_unslash( $_COOKIE[ self::COOKIE ] ) );
	}

	/**
	 * Sets the guest cookie.
	 *
	 * @param int $id Conversation post ID.
	 */
	private function set_cookie( int $id ): void {
		if ( $id < 1 ) {
			return;
		}
		/**
		 * Fires the guest-cookie write; the listener sends the header.
		 *
		 * @param string $value  Conversation post ID.
		 * @param int    $expire Expiry timestamp.
		 * @param string $path   Cookie path.
		 * @param string $domain Cookie domain.
		 * @param bool   $secure HTTPS only.
		 * @since 0.1.0
		 */
		do_action(
			'linker_tools_set_conversation_cookie',
			(string) $id,
			$this->cookie_expire(),
			defined( 'COOKIEPATH' ) ? COOKIEPATH : '/',
			defined( 'COOKIE_DOMAIN' ) ? COOKIE_DOMAIN : '',
			is_ssl()
		);
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
