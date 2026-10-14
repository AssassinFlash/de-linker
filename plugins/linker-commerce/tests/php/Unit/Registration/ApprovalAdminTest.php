<?php
/**
 * Tests for the approval surfaces in WordPress's screens.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\ApprovalAdmin;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * Tests for ApprovalAdmin: the list column, the one-click approve, the profile
 * block and the admin-post handler with its nonce and reason rule.
 *
 * @covers \Linker\Commerce\Registration\ApprovalAdmin
 */
final class ApprovalAdminTest extends TestCase {

	/**
	 * The meta of user 5 (a plain customer).
	 *
	 * @var array<string, mixed>
	 */
	private array $store = array();

	/**
	 * Whether the nonce check passes in the current step.
	 *
	 * @var bool
	 */
	private bool $nonce_ok = true;

	/**
	 * Translation and escaping pass through; the request functions too.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$capabilities = array( 'edit_users' => true );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => static fn ( string $cap ): bool => $capabilities[ $cap ] ?? false ) );
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $id ): ?WP_User {
					if ( ! in_array( $id, array( 5, 7 ), true ) ) {
						return null;
					}
					$user               = new WP_User();
					$user->ID           = $id;
					$user->roles        = 7 === $id ? array( 'administrator' ) : array( 'customer' );
					$user->display_name = 7 === $id ? 'Admin' : 'Maria';
					return $user;
				},
			)
		);
		WP_Mock::userFunction(
			'get_user_meta',
			array(
				'return' => fn ( int $user_id, string $key ): string => 5 === $user_id ? ( isset( $this->store[ $key ] ) ? (string) $this->store[ $key ] : '' ) : '',
			)
		);
		WP_Mock::userFunction(
			'update_user_meta',
			array(
				'return' => function ( int $user_id, string $key, $value ): bool {
					if ( 5 !== $user_id ) {
						return false;
					}
					$this->store[ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => static fn ( string $path ): string => 'https://example.test/wp-admin/' . $path ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'F j, Y' ) );
		WP_Mock::userFunction( 'date_i18n', array( 'return' => static fn ( string $format, int $time ): string => gmdate( $format, $time ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'absint', array( 'return' => static fn ( $value ): int => abs( (int) $value ) ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( $key ) ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction(
			'check_admin_referer',
			array(
				// WordPress's check dies the request itself when the nonce fails.
				'return' => function (): bool {
					if ( ! $this->nonce_ok ) {
						throw new \RuntimeException( 'die 0' );
					}
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'get_edit_user_link', array( 'return' => static fn ( int $user_id ): string => 'https://example.test/wp-admin/user-edit.php?user_id=' . $user_id ) );
		WP_Mock::userFunction( 'wp_get_referer', array( 'return' => 'https://example.test/wp-admin/users.php' ) );
		WP_Mock::userFunction(
			'wp_safe_redirect',
			array(
				'return' => static function (): void {
					throw new \RuntimeException( 'redirect' );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_die',
			array(
				'return' => static function ( $message = '', $title = '', array $args = array() ): void {
					throw new \RuntimeException( 'die ' . ( $args['response'] ?? 0 ) );
				},
			)
		);
	}

	/**
	 * The column stands first after the username.
	 */
	public function test_the_column_stands_after_the_username(): void {
		$admin = new ApprovalAdmin( new Approval() );
		$this->assertSame(
			array(
				'cb'                  => '<input/>',
				'username'            => 'Username',
				Approval::STATUS_META => 'Approval',
				'email'               => 'Email',
			),
			$admin->column_header(
				array(
					'cb'       => '<input/>',
					'username' => 'Username',
					'email'    => 'Email',
				)
			)
		);
	}

	/**
	 * A customer's cell names the state and carries the reason; staff rows stay empty.
	 */
	public function test_the_column_cell_names_the_state_and_reason(): void {
		$admin = new ApprovalAdmin( new Approval() );

		$this->assertSame( '', $admin->column_cell( '', Approval::STATUS_META, 9 ), 'A user that is not in the store is no customer' );

		$this->store[ Approval::STATUS_META ] = Approval::PENDING;
		$this->assertSame( 'Pending review', $admin->column_cell( '', Approval::STATUS_META, 5 ) );

		$this->store[ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->store[ Approval::REASON_META ] = 'Not a business.';
		$this->assertSame( 'Restricted<br /><span class="description">Not a business.</span>', $admin->column_cell( '', Approval::STATUS_META, 5 ) );

		$this->assertSame( '', $admin->column_cell( '', 'name', 5 ), 'Another column' );
	}

	/**
	 * The one-click approve appears for an account without prices, and not for
	 * an approved one.
	 */
	public function test_the_row_action_is_the_one_click_approve(): void {
		$admin        = new ApprovalAdmin( new Approval() );
		$customer     = new WP_User();
		$customer->ID = 5;

		$this->store[ Approval::STATUS_META ] = Approval::PENDING;
		WP_Mock::userFunction( 'wp_nonce_url', array( 'return' => static fn ( string $url ): string => $url . '&_wpnonce=t' ) );
		$actions = $admin->row_action( array( 'edit' => '<a>Edit</a>' ), $customer );
		$this->assertArrayHasKey( Approval::STATUS_META, $actions );
		$this->assertStringContainsString( 'admin-post.php?action=linker_approval&user=5&linker_approval_action=approve', $actions[ Approval::STATUS_META ] );
		$this->assertArrayHasKey( 'edit', $actions, 'The other actions stay.' );

		$this->store[ Approval::STATUS_META ] = Approval::APPROVED;
		$this->assertSame( array( 'edit' => '<a>Edit</a>' ), $admin->row_action( array( 'edit' => '<a>Edit</a>' ), $customer ) );
	}

	/**
	 * The profile block: the state with its audit row, the reason field and
	 * the three actions, posting to admin-post with a per-user nonce.
	 */
	public function test_the_profile_block_renders_the_three_actions(): void {
		$admin               = new ApprovalAdmin( new Approval() );
		$staff               = new WP_User();
		$staff->ID           = 7;
		$staff->display_name = 'Admin';

		$this->store[ Approval::STATUS_META ]     = Approval::RESTRICTED;
		$this->store[ Approval::REASON_META ]     = 'Not a business.';
		$this->store[ Approval::CHANGED_BY_META ] = 7;
		$this->store[ Approval::CHANGED_AT_META ] = 1791700000;

		WP_Mock::userFunction(
			'wp_nonce_field',
			array(
				// WordPress echoes the field by default; the block relies on it.
				'return' => static function ( string $action, string $field ): void {
					echo '<input type="hidden" name="' . $field . '" data-action="' . $action . '"/>';
				},
			)
		);
		ob_start();
		$admin->profile_block( $this->customer( 5 ) );
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'Restricted', $html );
		$this->assertStringContainsString( 'Not a business.', $html );
		$this->assertStringContainsString( 'Admin', $html, 'The audit row names who set the state.' );
		$this->assertStringContainsString( 'name="linker_approval_action"', $html );
		$this->assertStringContainsString( 'value="approve"', $html );
		$this->assertStringContainsString( 'value="restrict"', $html );
		$this->assertStringContainsString( 'value="reject"', $html );
		$this->assertStringContainsString( 'formaction="https://example.test/wp-admin/admin-post.php"', $html );
		$this->assertStringContainsString( 'name="user" value="5"', $html );
		$this->assertStringContainsString( 'name="linker_approval_nonce" data-action="linker_approval-5"', $html, 'The per-user nonce rides along.' );

		ob_start();
		$admin->profile_block( $this->customer( 9 ) );
		$this->assertSame( '', ob_get_clean(), 'Staff profiles carry no block.' );
	}

	/**
	 * The handler applies the posted action (the profile block's buttons) and
	 * leads back to the list.
	 */
	public function test_the_handler_applies_the_action(): void {
		$admin = new ApprovalAdmin( new Approval() );
		WP_Mock::expectAction( Approval::CHANGED_ACTION, 5, Approval::PENDING, Approval::APPROVED, '' );
		$this->request(
			array(
				'user'                     => '5',
				'linker_approval_action'   => 'approve',
				ApprovalAdmin::NONCE_FIELD => 't',
			)
		);

		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'redirect' );
		try {
			$admin->handle();
		} finally {
			$this->assertSame( Approval::APPROVED, $this->store[ Approval::STATUS_META ] ?? '' );
		}
	}

	/**
	 * The users list's one-click approve is a link, so the handler reads the
	 * action out of a GET request: the test walks the URL row_action() renders
	 * into the handler, exactly as the staff member's click does.
	 */
	public function test_the_inline_link_approves_through_the_get_path(): void {
		$admin                                = new ApprovalAdmin( new Approval() );
		$customer                             = new WP_User();
		$customer->ID                         = 5;
		$this->store[ Approval::STATUS_META ] = Approval::PENDING;
		WP_Mock::userFunction( 'wp_nonce_url', array( 'return' => static fn ( string $url ): string => $url . '&_wpnonce=t' ) );

		$link    = $admin->row_action( array(), $customer )[ Approval::STATUS_META ];
		$matches = array();
		$this->assertSame( 1, preg_match( '/href="([^"]+)"/', $link, $matches ), 'The row action is a link.' );
		parse_str( (string) parse_url( html_entity_decode( (string) ( $matches[1] ?? '' ) ), PHP_URL_QUERY ), $query );
		$this->assertSame( 'linker_approval', $query['action'] ?? '' );
		$this->assertSame( 'approve', $query['linker_approval_action'] ?? '' );

		// The link's own fields arrive as a GET request; $_POST stays empty.
		$fields = array();
		foreach ( array( 'action', 'user', 'linker_approval_action', ApprovalAdmin::NONCE_FIELD ) as $field ) {
			$value            = $query[ $field ] ?? '';
			$fields[ $field ] = is_string( $value ) ? $value : '';
		}
		$this->request( $fields, 'get' );
		WP_Mock::expectAction( Approval::CHANGED_ACTION, 5, Approval::PENDING, Approval::APPROVED, '' );
		try {
			$admin->handle();
			$this->fail( 'The handler ends in a redirect.' );
		} catch ( \RuntimeException $exception ) {
			$this->assertSame( 'redirect', $exception->getMessage() );
		}
		$this->assertSame( Approval::APPROVED, $this->store[ Approval::STATUS_META ] ?? '', 'The click approved the account.' );
	}

	/**
	 * The profile screen's buttons post WordPress's own form, whose trailing
	 * hidden `action=update` is the value PHP keeps: the request arrives on
	 * admin_post_update, and the door for it runs the very same handler
	 * (measured 2026-10-15; before this, no button of the profile block did
	 * anything and the request ended in WordPress's error page).
	 */
	public function test_the_profile_forms_buttons_arrive_under_wordpresss_own_action(): void {
		$admin = new ApprovalAdmin( new Approval() );
		WP_Mock::expectAction( Approval::CHANGED_ACTION, 5, Approval::PENDING, Approval::RESTRICTED, 'No fit yet.' );
		$this->request(
			array(
				'action'                   => 'update',
				'user'                     => '5',
				'linker_approval_action'   => 'restrict',
				'linker_approval_reason'   => 'No fit yet.',
				ApprovalAdmin::NONCE_FIELD => 't',
			)
		);

		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'redirect' );
		try {
			$admin->handle_profile_form();
		} finally {
			$this->assertSame( Approval::RESTRICTED, $this->store[ Approval::STATUS_META ] ?? '' );
			$this->assertSame( 'No fit yet.', $this->store[ Approval::REASON_META ] ?? '' );
		}
	}

	/**
	 * WordPress's own profile save (or any other "update" request) is not this
	 * plugin's: nothing is read, nothing dies, no state changes.
	 */
	public function test_the_update_door_stands_down_for_wordpresss_own_request(): void {
		$admin                                = new ApprovalAdmin( new Approval() );
		$this->store[ Approval::STATUS_META ] = Approval::PENDING;
		WP_Mock::userFunction( 'check_admin_referer', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_die', array( 'times' => 0 ) );
		$this->request(
			array(
				'action'  => 'update',
				'user_id' => '5',
			)
		);

		$admin->handle_profile_form();

		$this->assertSame( Approval::PENDING, $this->store[ Approval::STATUS_META ] ?? '' );
		$this->assertConditionsMet();
	}

	/**
	 * The handler refuses an unknown action and a reason-less restriction; the
	 * nonce comes first.
	 */
	public function test_the_handler_refuses_bad_actions(): void {
		$admin = new ApprovalAdmin( new Approval() );
		$this->request(
			array(
				'user'                     => '5',
				'linker_approval_action'   => 'ban',
				ApprovalAdmin::NONCE_FIELD => 't',
			)
		);
		try {
			$admin->handle();
			$this->fail( 'An unknown action dies.' );
		} catch ( \RuntimeException $exception ) {
			$this->assertSame( 'die 400', $exception->getMessage() );
		}

		$this->request(
			array(
				'user'                     => '5',
				'linker_approval_action'   => 'restrict',
				'linker_approval_reason'   => '',
				ApprovalAdmin::NONCE_FIELD => 't',
			)
		);
		try {
			$admin->handle();
			$this->fail( 'A restriction without a reason dies.' );
		} catch ( \RuntimeException $exception ) {
			$this->assertSame( 'die 400', $exception->getMessage() );
		}
		$this->assertSame( array(), $this->store, 'Nothing was written.' );

		$this->nonce_ok = false;
		$this->request(
			array(
				'user'                     => '5',
				'linker_approval_action'   => 'approve',
				ApprovalAdmin::NONCE_FIELD => 't',
			)
		);
		try {
			$admin->handle();
			$this->fail( 'A failed nonce dies first.' );
		} catch ( \RuntimeException $exception ) {
			$this->assertSame( 'die 0', $exception->getMessage() );
		}
	}

	/**
	 * A request as PHP hands it to WordPress: a submitted form carries its
	 * fields in $_POST and $_REQUEST, a clicked link in $_GET and $_REQUEST.
	 *
	 * @param array<string, string> $fields Request fields.
	 * @param string                $method 'post' for the profile block's buttons, 'get' for the list's link.
	 */
	private function request( array $fields, string $method = 'post' ): void {
		$_GET     = 'get' === $method ? $fields : array();
		$_POST    = 'post' === $method ? $fields : array();
		$_REQUEST = $fields;
	}

	/**
	 * A customer user with the given id.
	 *
	 * @param int $id User id.
	 */
	private function customer( int $id ): WP_User {
		$user        = new WP_User();
		$user->ID    = $id;
		$user->roles = array( 'customer' );
		return $user;
	}
}
