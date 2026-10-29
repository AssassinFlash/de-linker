<?php
/**
 * Only a native refusal that provably wrote nothing may ask for a new proof.
 * Recovery data remains specific to each native form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Mail\ResetNotice;
use Linker\Commerce\Protection\FormRecovery;
use Linker\Commerce\Protection\Outcome;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Error;
use WP_Mock;

// phpcs:disable WordPress.Security.NonceVerification -- Synthetic native form values are restored after the test.

/**
 * The recovery hint follows the native outcome, never a client flag.
 * Password recovery carries only the editable login.
 *
 * @covers \Linker\Commerce\Protection\FormRecovery
 * @covers \Linker\Commerce\Mail\ResetNotice
 */
final class FormRecoveryTest extends TestCase {
	/**
	 * Every partition the outcome table knows, so this test cannot fall behind a
	 * new native refusal: the table is the only list.
	 *
	 * @return array<string, array{string,string}>
	 */
	public function partitions(): array {
		$cases = array();
		foreach ( Outcome::table() as $code => $row ) {
			$cases[ $code ] = array( $code, $row[0] );
		}
		return $cases;
	}

	/**
	 * A definite refusal asks for a fresh check; every other outcome keeps the
	 * original UUID recoverable without a new proof.
	 *
	 * @dataProvider partitions
	 * @param string $code      Native error code.
	 * @param string $partition Outcome partition.
	 */
	public function test_the_recovery_hint_follows_the_partition( string $code, string $partition ): void {
		$this->assertSame( Outcome::REFUSED !== $partition, FormRecovery::after_error( new WP_Error( $code, 'fixture' ) ), $code );
	}

	/** A code the table has never seen is not evidence of a pre-write refusal. */
	public function test_an_unrecognized_code_preserves_recovery(): void {
		$this->assertTrue( FormRecovery::after_error( new WP_Error( 'linker_unrecognized_fixture', 'fixture' ) ) );
	}

	/** Only the journal's changed-input refusal makes the stored UUID unusable. */
	public function test_only_changed_input_supersedes_the_recovered_uuid(): void {
		$this->assertTrue( FormRecovery::superseded( new WP_Error( 'linker_admission_payload_changed', 'fixture' ) ) );
		$this->assertFalse( FormRecovery::superseded( null ) );
		$this->assertFalse( FormRecovery::superseded( new WP_Error( 'linker_inquiry_pending', 'fixture' ) ) );
		$this->assertFalse( FormRecovery::superseded( new WP_Error( 'linker_admission_proof', 'fixture' ) ) );
	}

	/**
	 * A superseded UUID is dropped, so the native form can mint the new one the
	 * refusal asks for instead of resubmitting it forever.
	 */
	public function test_a_changed_input_refusal_clears_the_stored_uuid(): void {
		$store   = array();
		$session = Mockery::mock( \WC_Session_Handler::class );
		$session->shouldReceive( 'set' )->andReturnUsing(
			static function ( string $key, $value ) use ( &$store ): void {
				$store[ $key ] = $value;
			}
		);
		$session->shouldReceive( 'set_customer_session_cookie' )->times( 3 )->with( true );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'session' => $session ) ) );
		WP_Mock::userFunction( 'wc_load_cart' );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => $value ) );
		$post = array(
			'name'              => 'Fixture Customer',
			'email'             => 'fixture@example.test',
			'message'           => 'Unchanged question.',
			'linker_request_id' => '01234567-0123-4123-8123-0123456789ab',
		);

		FormRecovery::save( 'contact', $post, new WP_Error( 'linker_admission_payload_changed', 'fixture' ) );
		$superseded = $store['linker_form_recovery_contact']['fields'];
		$this->assertSame( '', $superseded['linker_request_id'] );
		$this->assertSame( '0', $superseded['linker_recovery_available'] );
		$this->assertSame( 'Unchanged question.', $superseded['message'] );

		FormRecovery::save( 'contact', $post, new WP_Error( 'linker_inquiry_pending', 'fixture' ) );
		$pending = $store['linker_form_recovery_contact']['fields'];
		$this->assertSame( '01234567-0123-4123-8123-0123456789ab', $pending['linker_request_id'] );
		$this->assertSame( '1', $pending['linker_recovery_available'] );

		FormRecovery::save( 'contact', $post, new WP_Error( 'linker_admission_proof', 'fixture' ) );
		$refused = $store['linker_form_recovery_contact']['fields'];
		$this->assertSame( '01234567-0123-4123-8123-0123456789ab', $refused['linker_request_id'], 'A definite proof refusal keeps the original logical request.' );
		$this->assertSame( '0', $refused['linker_recovery_available'] );
	}

	/** Password recovery retains only a bounded, sanitized login, once. */
	public function test_password_reset_recovery_keeps_only_the_login(): void {
		$store   = array();
		$session = Mockery::mock( \WC_Session_Handler::class );
		$session->shouldReceive( 'set' )->andReturnUsing(
			static function ( string $key, $value ) use ( &$store ): void {
				$store[ $key ] = $value;
			}
		);
		$session->shouldReceive( 'get' )->andReturnUsing(
			static function ( string $key ) use ( &$store ) {
				return $store[ $key ] ?? null;
			}
		);
		$session->shouldReceive( 'set_customer_session_cookie' )->with( true );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'session' => $session ) ) );
		WP_Mock::userFunction( 'wc_load_cart' );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => strip_tags( $value ) ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => strip_tags( $value ) ) );
		WP_Mock::passthruFunction( 'wp_unslash' );
		$this->options( array() );
		$old_cookies = $_COOKIE;
		$old_post    = $_POST;
		$_COOKIE     = array();
		try {
			FormRecovery::save(
				'password_reset',
				array(
					'user_login'   => '<b>installer@example.test</b>',
					'password_1'   => 'never-store-password',
					'reset_key'    => 'never-store-key',
					'linker_proof' => 'never-store-proof',
					'message'      => 'contact-only-field',
				)
			);
			$saved = $store['linker_form_recovery_password_reset'];
			$this->assertSame(
				array(
					'user_login'                => 'installer@example.test',
					'linker_recovery_available' => '1',
				),
				$saved['fields']
			);
			$this->assertGreaterThanOrEqual( time(), $saved['until'] );
			$this->assertLessThanOrEqual( time() + 300, $saved['until'] );
			$this->assertSame( array(), FormRecovery::consume( 'password_reset' ), 'Without the native session cookie, no input is recovered.' );
			$this->assertSame(
				array(
					'user_login'                => 'installer@example.test',
					'linker_recovery_available' => '1',
				),
				FormRecovery::consume( 'password_reset', true ),
				'The current request can consume a session it just created, before its cookie returns.'
			);
			FormRecovery::save( 'password_reset', array( 'user_login' => 'installer@example.test' ) );
			$_COOKIE['wp_woocommerce_session_fixture'] = 'native-presence';
			$this->assertSame(
				array(
					'user_login'                => 'installer@example.test',
					'linker_recovery_available' => '1',
				),
				FormRecovery::consume( 'password_reset' )
			);
			$this->assertSame( array(), FormRecovery::consume( 'password_reset' ), 'Recovery is consumed only once.' );

			FormRecovery::save( 'password_reset', array( 'user_login' => str_repeat( 'x', 5001 ) ) );
			$this->assertSame( str_repeat( 'x', 5000 ), FormRecovery::consume( 'password_reset' )['user_login'] );
			$store['linker_form_recovery_password_reset'] = array(
				'until'  => time() - 1,
				'fields' => array( 'user_login' => 'expired@example.test' ),
			);
			$this->assertSame( array(), FormRecovery::consume( 'password_reset' ), 'An expired recovery is not returned.' );

			FormRecovery::save( 'password_reset', array( 'user_login' => 'previous@example.test' ) );
			$_POST = array(
				'wc_reset_password' => 'true',
				'user_login'        => 'installer@example.test',
			);
			ResetNotice::capture_submission( new \WP_Error(), new \WP_User() );
			$this->assertNull( $store['linker_form_recovery_password_reset'], 'A valid attempt clears old input and does not persist the new login.' );
			$errors = new \WP_Error();
			$errors->add( 'fixture', 'Synthetic failure' );
			ResetNotice::capture_submission( $errors, new \WP_User() );
			$this->assertSame(
				array(
					'user_login'                => 'installer@example.test',
					'linker_recovery_available' => '1',
				),
				FormRecovery::consume( 'password_reset' )
			);
			ResetNotice::capture_submission( new \WP_Error(), false );
			$this->assertSame(
				array(
					'user_login'                => 'installer@example.test',
					'linker_recovery_available' => '1',
				),
				FormRecovery::consume( 'password_reset' ),
				'A native unknown-user refusal keeps the entered text.'
			);
			$_POST = array( 'user_login' => 'other@example.test' );
			ResetNotice::capture_submission( $errors, false );
			$this->assertSame( array(), FormRecovery::consume( 'password_reset' ), 'Non-Woo submissions do not enter Woo retry storage.' );
			$_POST = array(
				'wc_reset_password' => 'true',
				'user_login'        => '',
			);
			ResetNotice::capture_submission( new \WP_Error(), new \WP_User() );
		} finally {
			$_COOKIE = $old_cookies;
			$_POST   = $old_post;
		}
	}
}
