<?php
/**
 * Tests for the approval rule.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;
use WP_Session_Tokens;
use WP_User;

/**
 * Tests for Approval: the default states, the three reversible actions with
 * their audit row and reason rule, the session sign-out on reject and the
 * login gate.
 *
 * @covers \Linker\Commerce\Registration\Approval
 */
final class ApprovalTest extends TestCase {

	/**
	 * The meta of user 5, written by update_user_meta() and read by it.
	 *
	 * @var array<string, mixed>
	 */
	private array $store = array();


	/**
	 * A user in the store: 5 is a plain customer, 6 staff.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $id ): ?WP_User {
					if ( 5 === $id || 6 === $id ) {
						$user        = new WP_User();
						$user->ID    = $id;
						$user->roles = 6 === $id ? array( 'shop_manager' ) : array( 'customer' );
						return $user;
					}
					return null;
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
		WP_Session_Tokens::$destroyed_all = array(); // @phpstan-ignore staticProperty.notFound (the test double lives in tests/php/Doubles, excluded from analysis)
	}

	/**
	 * Without a recorded decision a plain customer waits (pending) and staff
	 * does not (approved); a recorded state is read as it is.
	 */
	public function test_status_defaults(): void {
		$approval = new Approval();

		$this->assertSame( Approval::PENDING, $approval->status( 5 ), 'Customer without a decision' );
		$this->assertSame( Approval::APPROVED, $approval->status( 6 ), 'Staff without a decision' );

		$this->store[ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->assertSame( Approval::RESTRICTED, $approval->status( 5 ) );
	}

	/**
	 * Only an approved account sees prices; a guest sees none.
	 */
	public function test_sees_prices_by_state(): void {
		$approval = new Approval();

		$this->assertFalse( $approval->sees_prices( 0 ), 'Guest' );
		$this->assertFalse( $approval->sees_prices( 5 ), 'Pending customer' );

		$this->store[ Approval::STATUS_META ] = Approval::APPROVED;
		$this->assertTrue( $approval->sees_prices( 5 ), 'Approved customer' );

		$this->store[ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->assertFalse( $approval->sees_prices( 5 ), 'Restricted customer' );

		$this->store[ Approval::STATUS_META ] = Approval::REJECTED;
		$this->assertFalse( $approval->sees_prices( 5 ), 'Rejected customer' );
	}

	/**
	 * The three actions write the state, the reason and the audit row, and a
	 * change announces itself with both states and the reason.
	 */
	public function test_set_announces_a_change_with_the_audit_row(): void {
		$before = time();
		WP_Mock::expectAction( Approval::CHANGED_ACTION, 5, Approval::PENDING, Approval::RESTRICTED, 'Net prices are for businesses.' );

		$this->assertTrue( ( new Approval() )->set( 5, Approval::RESTRICTED, 'Net prices are for businesses.' ) );

		$this->assertSame( Approval::RESTRICTED, $this->store[ Approval::STATUS_META ] );
		$this->assertSame( 'Net prices are for businesses.', $this->store[ Approval::REASON_META ] );
		$this->assertSame( 7, $this->store[ Approval::CHANGED_BY_META ] );
		$this->assertGreaterThanOrEqual( $before, $this->store[ Approval::CHANGED_AT_META ] );
	}

	/**
	 * An approval clears the reason; a rejection ends the sessions; an
	 * approval signs nobody out.
	 */
	public function test_approve_clears_the_reason_and_reject_ends_sessions(): void {
		$this->store[ Approval::STATUS_META ] = Approval::REJECTED;
		$this->store[ Approval::REASON_META ] = 'Not a business.';
		WP_Mock::expectAction( Approval::CHANGED_ACTION, 5, Approval::REJECTED, Approval::APPROVED, '' );
		( new Approval() )->set( 5, Approval::APPROVED );

		$this->assertSame( '', $this->store[ Approval::REASON_META ], 'The approval carries no reason.' );
		$this->assertNotContains( 5, WP_Session_Tokens::$destroyed_all, 'An approval signs nobody out.' ); // @phpstan-ignore staticProperty.notFound (the test double lives in tests/php/Doubles)

		WP_Mock::expectAction( Approval::CHANGED_ACTION, 5, Approval::APPROVED, Approval::REJECTED, 'Not a business.' );
		( new Approval() )->set( 5, Approval::REJECTED, 'Not a business.' );
		$this->assertContains( 5, WP_Session_Tokens::$destroyed_all, 'A rejection ends the sessions.' ); // @phpstan-ignore staticProperty.notFound (the test double lives in tests/php/Doubles)
	}

	/**
	 * Setting the same state again only refreshes the reason and the stamps;
	 * no email is queued twice.
	 */
	public function test_the_same_state_refreshes_without_announcing(): void {
		$this->store[ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->store[ Approval::REASON_META ] = 'Old reason.';

		$this->assertTrue( ( new Approval() )->set( 5, Approval::RESTRICTED, 'Updated reason.' ) );

		$this->assertSame( 'Updated reason.', $this->store[ Approval::REASON_META ] );
		$this->assertSame( 7, $this->store[ Approval::CHANGED_BY_META ] );
	}

	/**
	 * A restriction or rejection without a reason is refused, as is an unknown
	 * state: the reason is the customer's explanation by email.
	 */
	public function test_a_reason_is_required_and_states_are_validated(): void {
		$approval = new Approval();

		$this->assertFalse( $approval->set( 5, Approval::RESTRICTED, '' ) );
		$this->assertFalse( $approval->set( 5, Approval::REJECTED, '   ' ) );
		$this->assertFalse( $approval->set( 5, 'banned', 'No such state.' ) );
		$this->assertSame( array(), $this->store, 'Nothing was written.' );
	}

	/**
	 * The login gate: a rejected account cannot sign in, everyone else passes
	 * through untouched.
	 */
	public function test_the_login_gate_keeps_rejected_accounts_out(): void {
		$approval     = new Approval();
		$customer     = new WP_User();
		$customer->ID = 5;

		$this->store[ Approval::STATUS_META ] = Approval::REJECTED;
		$kept_out                             = $approval->gate_login( $customer );
		$this->assertInstanceOf( WP_Error::class, $kept_out );
		$this->assertSame( 'linker_approval_rejected', $kept_out->get_error_code() );

		$this->store[ Approval::STATUS_META ] = Approval::APPROVED;
		$this->assertSame( $customer, $approval->gate_login( $customer ) );

		$error = new WP_Error( 'incorrect_password' );
		$this->assertSame( $error, $approval->gate_login( $error ) );
	}
}
