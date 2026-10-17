<?php
/**
 * Every conversation of a browser, on the real instance.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Thread;
use PHPUnit\Framework\TestCase;

/**
 * A guest keeps every conversation this browser opened, can switch between
 * them and clear one; signing in moves all of them into the account, where
 * any other device of the same customer lists them (ticket #235,
 * docs/specs/13-genie.md, goal 7 and acceptance A9).
 *
 * A "browser" here is the cookie jar: Conversations reads and writes
 * `$_COOKIE` in the request, so a test switches browsers by swapping that
 * array and the signed-in user. Real `linker_conversation` posts and real
 * users are written and removed again.
 *
 * @coversNothing
 */
final class ConversationListTest extends TestCase {

	/**
	 * The cookie writers, held while a test runs. A CLI run has already
	 * printed, so a real Set-Cookie header would be a PHP warning; the
	 * header is the browser's business, the value in `$_COOKIE` is the
	 * part these tests read.
	 *
	 * @var array<string, mixed>
	 */
	private array $listeners = array();

	/**
	 * Conversations the tests created.
	 *
	 * @var list<int>
	 */
	private array $posts = array();

	/**
	 * Users the tests created.
	 *
	 * @var list<int>
	 */
	private array $users = array();

	/**
	 * Skips unless the integration configuration ran the bootstrap.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Holds the cookie writers and starts as a fresh guest browser.
	 */
	protected function setUp(): void {
		parent::setUp();
		global $wp_filter;
		foreach ( array( 'linker_tools_set_conversation_cookie', 'linker_tools_set_genie_browser_cookie' ) as $hook ) {
			$this->listeners[ $hook ] = $wp_filter[ $hook ] ?? null;
			remove_all_actions( $hook );
		}
		// The sign-in actions keep only this plugin's listener: other plugins
		// of the snapshot (User Switching) send their own cookies on them.
		foreach ( array( 'wp_login', 'set_logged_in_cookie', 'wp_logout', 'set_olduser_cookie', 'clear_olduser_cookie' ) as $hook ) {
			$this->listeners[ $hook ] = isset( $wp_filter[ $hook ] ) ? clone $wp_filter[ $hook ] : null;
			foreach ( $wp_filter[ $hook ]->callbacks ?? array() as $priority => $callbacks ) {
				foreach ( $callbacks as $callback ) {
					$function = $callback['function'];
					if ( ! ( is_array( $function ) && $function[0] instanceof Conversations ) ) {
						remove_action( $hook, $function, $priority );
					}
				}
			}
		}
		$this->browser( array() );
	}

	/**
	 * Removes the fixture conversations and users, gives the cookie writers back.
	 */
	protected function tearDown(): void {
		global $wp_filter;
		foreach ( $this->listeners as $hook => $listener ) {
			if ( null === $listener ) {
				unset( $wp_filter[ $hook ] );
			} else {
				$wp_filter[ $hook ] = $listener; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- restores the hook this test held.
			}
		}
		$this->listeners = array();
		wp_set_current_user( 0 );
		$_COOKIE = array();
		foreach ( $this->posts as $id ) {
			wp_delete_post( $id, true );
		}
		$this->posts = array();
		require_once ABSPATH . 'wp-admin/includes/user.php';
		foreach ( $this->users as $user ) {
			wp_delete_user( $user );
		}
		$this->users = array();
		parent::tearDown();
	}

	/**
	 * A guest who opens three conversations finds all three in the list and
	 * can go back to the first. Another browser sees none of them.
	 */
	public function test_a_guest_keeps_every_conversation_of_this_browser(): void {
		$conversations = new Conversations();
		$opened        = $this->open_three( $conversations );

		$this->assertSame( array_reverse( $opened ), self::ids( $conversations->list_for_visitor() ), 'All three, newest first.' );
		$this->assertSame( $opened[2], $conversations->existing_id(), 'The newest is the current one.' );

		$this->assertTrue( $conversations->activate( $opened[0] ), 'The first can be continued.' );
		$this->assertSame( $opened[0], $conversations->existing_id() );
		$this->assertSame( array_reverse( $opened ), self::ids( $conversations->list_for_visitor() ), 'Switching keeps the other two.' );

		$this->browser( array() );
		$this->assertSame( array(), $conversations->list_for_visitor(), 'Another browser lists nothing.' );
		$this->assertFalse( $conversations->activate( $opened[0] ), 'Nor can it continue one of them.' );
		$this->assertFalse( $conversations->may_use( $opened[1] ) );
	}

	/**
	 * Signing in puts every conversation of the browser under the account,
	 * and a second device signed in as the same customer lists all three.
	 */
	public function test_signing_in_moves_every_conversation_into_the_account(): void {
		$conversations = new Conversations();
		$opened        = $this->open_three( $conversations );
		$jar           = $_COOKIE;
		$user          = $this->customer();
		$activity      = array_map( static fn( int $id ): int => (int) get_post_meta( $id, Thread::ACTIVITY, true ), $opened );

		/** WordPress's own login action, as wp_signon() fires it.
		 *
		 * @since 2.5.0
		 */
		do_action( 'wp_login', 'linker-it-customer', get_userdata( $user ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own action, fired as core fires it.
		wp_set_current_user( $user );

		foreach ( $opened as $id ) {
			$this->assertSame( $user, (int) get_post_field( 'post_author', $id ), 'Each conversation now belongs to the account.' );
		}
		$this->assertSame( array_reverse( $opened ), self::ids( $conversations->list_for_visitor() ), 'This browser, signed in, lists all three, in the same order.' );
		$this->assertSame( $activity, array_map( static fn( int $id ): int => (int) get_post_meta( $id, Thread::ACTIVITY, true ), $opened ), 'The claim leaves the last-turn times alone.' );
		$this->assertNotSame( $jar[ Conversations::BROWSER_COOKIE ] ?? '', self::key(), 'The claim gives the browser a new key.' );

		$this->browser( array(), $user );
		$this->assertSame( array_reverse( $opened ), self::ids( $conversations->list_for_visitor() ), 'Another device, signed in, lists all three.' );
		$this->assertTrue( $conversations->activate( $opened[0] ) );

		$this->browser( $jar );
		$this->assertSame( array(), $conversations->list_for_visitor(), 'Signed out, the same browser no longer shows the account’s conversations.' );
	}

	/**
	 * A new account is signed in without wp_login (WooCommerce sets the
	 * auth cookie itself); its browser's conversations move all the same.
	 */
	public function test_a_new_account_takes_the_browsers_conversations(): void {
		$conversations = new Conversations();
		$opened        = $this->open_three( $conversations );
		$user          = $this->customer();

		/** WordPress's own action, fired by wp_set_auth_cookie().
		 *
		 * @since 2.6.0
		 */
		do_action( 'set_logged_in_cookie', 'cookie', time() + DAY_IN_SECONDS, time() + DAY_IN_SECONDS, $user, 'logged_in', 'token' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own action, fired as core fires it.

		foreach ( $opened as $id ) {
			$this->assertSame( $user, (int) get_post_field( 'post_author', $id ) );
		}
	}

	/**
	 * Continuing an old conversation puts it at the top: the list follows
	 * the last turn, not the start or the title.
	 */
	public function test_continuing_an_old_conversation_moves_it_to_the_top(): void {
		$conversations = new Conversations();
		$opened        = $this->open_three( $conversations );

		( new Thread() )->record(
			$opened[0],
			array(
				array(
					'role'    => 'user',
					'content' => 'linker-it-again',
				),
			),
			''
		);

		$this->assertSame( array( $opened[0], $opened[2], $opened[1] ), self::ids( $conversations->list_for_visitor() ) );
	}

	/**
	 * Signing out gives the browser a new guest key and forgets the current
	 * conversation: the next person on the browser starts afresh.
	 */
	public function test_signing_out_starts_a_new_guest_key(): void {
		$conversations = new Conversations();
		$this->open_three( $conversations );
		$user = $this->customer();
		/** This action is documented in wp-includes/user.php (wp_signon()). */
		do_action( 'wp_login', 'linker-it-customer', get_userdata( $user ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own action, fired as core fires it.
		wp_set_current_user( $user );
		$signed_in_key = self::key();

		/** This action is documented in wp-includes/pluggable.php (wp_logout()). */
		do_action( 'wp_logout', $user ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own action, fired as core fires it.
		wp_set_current_user( 0 );

		$this->assertNotSame( '', self::key() );
		$this->assertNotSame( $signed_in_key, self::key(), 'A new guest key.' );
		$this->assertSame( 0, $conversations->existing_id(), 'No current conversation.' );
		$this->assertSame( array(), $conversations->list_for_visitor(), 'Nothing listed for the next guest.' );

		$next          = $conversations->open();
		$this->posts[] = $next;
		$this->assertSame( array( $next ), self::ids( $conversations->list_for_visitor() ) );
	}

	/**
	 * Staff switching into a customer with User Switching set that
	 * customer's auth cookie; the browser's guest conversations stay where
	 * they are.
	 */
	public function test_user_switching_claims_nothing(): void {
		$conversations = new Conversations();
		$opened        = $this->open_three( $conversations );
		$customer      = $this->customer();

		/**
		 * User Switching's own action, fired before it sets the new auth cookie (user-switching.php, switch_to_user()).
		 *
		 * @since 1.0.0
		 */
		do_action( 'set_olduser_cookie', 'cookie', time() + DAY_IN_SECONDS, 1, 'logged_in', 'token' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- User Switching's action, fired as it fires it.
		/** This action is documented in wp-includes/pluggable.php (wp_set_auth_cookie()). */
		do_action( 'set_logged_in_cookie', 'cookie', time() + DAY_IN_SECONDS, time() + DAY_IN_SECONDS, $customer, 'logged_in', 'token' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own action, fired as core fires it.

		foreach ( $opened as $id ) {
			$this->assertSame( 0, (int) get_post_field( 'post_author', $id ), 'Still the browser\'s guest conversation.' );
		}
	}

	/**
	 * Clearing a conversation deletes it: it leaves the list and is no
	 * context for anything after. Another browser cannot clear it.
	 */
	public function test_clearing_a_conversation_deletes_it(): void {
		$conversations = new Conversations();
		$opened        = $this->open_three( $conversations );
		$jar           = $_COOKIE;

		$this->browser( array() );
		$this->assertFalse( $conversations->delete( $opened[0] ), 'Another browser cannot clear it.' );
		$this->assertInstanceOf( \WP_Post::class, get_post( $opened[0] ) );

		$this->browser( $jar );
		$this->assertTrue( $conversations->delete( $opened[0] ) );
		$this->assertNull( get_post( $opened[0] ), 'The post is gone, thread and all.' );
		$this->assertSame( array( $opened[2], $opened[1] ), self::ids( $conversations->list_for_visitor() ) );

		$this->assertTrue( $conversations->delete( $opened[2] ), 'The current one can be cleared too.' );
		$this->assertSame( 0, $conversations->existing_id(), 'Then there is no current conversation.' );
		$this->assertSame( array( $opened[1] ), self::ids( $conversations->list_for_visitor() ) );
	}

	/**
	 * A guest whose conversation began before the browser key existed (only
	 * the signed conversation cookie) keeps it when opening the next one.
	 */
	public function test_an_earlier_single_conversation_stays_in_the_list(): void {
		$earlier = wp_insert_post(
			array(
				'post_type'   => Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => 'linker-it-earlier',
				'post_author' => 0,
			),
			true
		);
		$this->assertIsInt( $earlier );
		$this->posts[] = $earlier;
		// The cookie the site issued before this ticket: id.signature, HMAC of
		// the id with the auth salt (Conversations::from_cookie()).
		$this->browser( array( Conversations::COOKIE => $earlier . '.' . hash_hmac( 'sha256', Conversations::COOKIE . '|' . $earlier, wp_salt( 'auth' ) ) ) );

		$conversations = new Conversations();
		$this->assertSame( array( $earlier ), self::ids( $conversations->list_for_visitor() ) );
		$next          = $conversations->open();
		$this->posts[] = $next;
		$conversations->title_from_first_message( $next, 'linker-it-next' );

		$this->assertSame( array( $next, $earlier ), self::ids( $conversations->list_for_visitor() ) );
		$this->assertTrue( $conversations->activate( $earlier ), 'The earlier one can still be continued.' );
	}

	/**
	 * Opens three conversations in the current browser, each named by a
	 * first message, a second apart so "newest first" is a fact of the data.
	 *
	 * @param Conversations $conversations The conversation store.
	 * @return list<int> Oldest first.
	 */
	private function open_three( Conversations $conversations ): array {
		$opened = array();
		foreach ( array( 'first', 'second', 'third' ) as $index => $name ) {
			$id = $conversations->open();
			$this->assertGreaterThan( 0, $id );
			$this->posts[] = $id;
			$conversations->title_from_first_message( $id, 'linker-it-' . $name );
			( new Thread() )->record(
				$id,
				array(
					array(
						'role'    => 'user',
						'content' => 'linker-it-' . $name,
					),
				),
				''
			);
			// The last turns a minute apart, oldest first, the way time
			// would have set them; the list orders by this.
			update_post_meta( $id, Thread::ACTIVITY, time() - ( 3 - $index ) * MINUTE_IN_SECONDS );
			$opened[] = $id;
		}
		return $opened;
	}

	/**
	 * A customer account with an email address.
	 */
	private function customer(): int {
		$user = wp_insert_user(
			array(
				'user_login' => 'linker-it-' . wp_generate_password( 8, false ),
				'user_email' => 'linker-it-' . wp_generate_password( 8, false ) . '@example.test',
				'user_pass'  => wp_generate_password( 24 ),
				'role'       => 'customer',
			)
		);
		$this->assertIsInt( $user );
		$this->users[] = $user;
		return $user;
	}

	/**
	 * Switches to a browser: its cookies and who is signed in on it.
	 *
	 * @param array<string, string> $cookies The browser's cookies.
	 * @param int                   $user    Signed-in user, 0 for a guest.
	 */
	private function browser( array $cookies, int $user = 0 ): void {
		$_COOKIE = $cookies;
		wp_set_current_user( $user );
	}

	/**
	 * The ids of a list.
	 *
	 * @param list<array{id: int, title: string, updated: string}> $items Conversation list.
	 * @return list<int>
	 */
	private static function ids( array $items ): array {
		return array_map( static fn( array $item ): int => $item['id'], $items );
	}

	/**
	 * This browser's key, as the request now holds it.
	 */
	private static function key(): string {
		return (string) ( $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '' ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- the test's own cookie jar.
	}
}
