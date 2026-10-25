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
 * Tests for ApprovalAdmin: status visibility and read-only links to the
 * shared account-review card.
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

	/** Supplies the read-only WordPress user/capability helpers. */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $id ): ?WP_User {
					if ( ! in_array( $id, array( 5, 7 ), true ) ) {
						return null; }
					$user = new WP_User();
					$user->ID = $id;
					$user->roles = 7 === $id ? array( 'administrator' ) : array( 'customer' );
					return $user;
				},
			)
		);
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => fn ( int $user_id, string $key ): string => 5 === $user_id ? (string) ( $this->store[ $key ] ?? '' ) : '' ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => static fn ( string $path ): string => 'https://example.test/wp-admin/' . $path ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( string $key, int $id, string $url ): string => $url . '&' . $key . '=' . $id ) );
		WP_Mock::userFunction( 'wp_kses_post', array( 'return' => static fn ( string $html ): string => $html ) );
	}

	/**
	 * The column stands first after the username.
	 */
	public function test_the_column_stands_after_the_username(): void {
		$admin = new ApprovalAdmin( new Approval( static fn ( callable $work ): mixed => $work() ) );
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
		$admin = new ApprovalAdmin( new Approval( static fn ( callable $work ): mixed => $work() ) );

		$this->assertSame( '', $admin->column_cell( '', Approval::STATUS_META, 9 ), 'A user that is not in the store is no customer' );

		$this->store[ Approval::STATUS_META ] = Approval::PENDING;
		$this->assertSame( 'Pending review', $admin->column_cell( '', Approval::STATUS_META, 5 ) );

		$this->store[ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->store[ Approval::REASON_META ] = 'Not a business.';
		$this->assertSame( 'Restricted<br /><span class="description">Not a business.</span>', $admin->column_cell( '', Approval::STATUS_META, 5 ) );

		$this->assertSame( '', $admin->column_cell( '', 'name', 5 ), 'Another column' );
	}

	/** All states link to review, never to a state-changing URL. */
	public function test_all_customer_states_link_to_the_review_card(): void {
		$admin = new ApprovalAdmin( new Approval( static fn ( callable $work ): mixed => $work() ) );
		foreach ( Approval::states() as $status ) {
			$this->store[ Approval::STATUS_META ] = $status;
			$user                                 = new WP_User();
			$user->ID                             = 5;
			$actions                              = $admin->row_action( array( 'edit' => 'Edit' ), $user );
			$this->assertStringContainsString( 'page=linker-accounts&focus=5', $actions[ Approval::STATUS_META ] );
			$this->assertStringNotContainsString( 'linker_approval_action', $actions[ Approval::STATUS_META ] );
			$this->assertSame( 'Edit', $actions['edit'] );
		}
	}

	/** Profile status remains visible, with no second form or action buttons. */
	public function test_profile_keeps_status_and_opens_the_shared_review_card(): void {
		$this->store[ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->store[ Approval::REASON_META ] = 'Please provide the company website.';
		$user                                 = new WP_User();
		$user->ID                             = 5;
		ob_start();
		( new ApprovalAdmin( new Approval( static fn ( callable $work ): mixed => $work() ) ) )->profile_block( $user );
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'Restricted', $html );
		$this->assertStringContainsString( 'Please provide the company website.', $html );
		$this->assertStringContainsString( 'page=linker-accounts&focus=5', $html );
		$this->assertStringNotContainsString( '<button', $html );
		$this->assertStringNotContainsString( '<input', $html );
	}
}
