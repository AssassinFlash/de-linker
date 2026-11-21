<?php
/**
 * Native account form recovery uses the current authenticated submission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\PendingProfileCapacity;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/** Woo account fields shown after a validation error. */
final class AccountFormValuesTest extends TestCase {

	/** Form values belong to the customer who submitted the Woo nonce. */
	public function test_owner_can_correct_a_name_and_an_empty_email_without_recovering_credentials(): void {
		// phpcs:disable WordPress.Security.NonceVerification -- Snapshot and restore the unit fixture's synthetic request.
		$post    = $_POST;
		$request = $_REQUEST;
		// phpcs:enable WordPress.Security.NonceVerification
		$owner = 27;
		WP_Mock::userFunction( 'get_current_user_id' )->andReturnUsing(
			static function () use ( &$owner ): int {
				return $owner;
			}
		);
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wp_unslash' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wp_verify_nonce' )->with( 'native-form', 'save_account_details' )->andReturn( 1 );
		try {
			$_REQUEST['save-account-details-nonce'] = 'native-form';
			$_POST                                  = array(
				'action'             => 'save_account_details',
				'account_first_name' => 'New name',
				'account_email'      => '',
				'password_current'   => 'fixture-password',
			);
			PendingProfileCapacity::account_errors( new \WP_Error(), (object) array( 'ID' => $owner ) );
			$this->assertSame( 'New name', PendingProfileCapacity::account_value( 'account_first_name', 'Current name' ) );
			$this->assertSame( '', PendingProfileCapacity::account_value( 'account_email', 'original@example.test' ) );
			$this->assertSame( '', PendingProfileCapacity::account_value( 'password_current', '' ) );
			$owner = 28;
			$this->assertSame( 'Current name', PendingProfileCapacity::account_value( 'account_first_name', 'Current name' ) );
		} finally {
			$_POST    = $post;
			$_REQUEST = $request;
		}
	}
}
