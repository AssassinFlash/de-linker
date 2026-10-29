<?php
/**
 * Recovery data remains specific to each native form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\FormRecovery;
use Linker\Commerce\Mail\ResetNotice;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

// phpcs:disable WordPress.Security.NonceVerification -- Synthetic native form values are restored after the test.

/**
 * Password recovery carries only the editable login.
 *
 * @covers \Linker\Commerce\Protection\FormRecovery
 * @covers \Linker\Commerce\Mail\ResetNotice
 */
final class FormRecoveryTest extends TestCase {
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
			$this->assertSame( array( 'user_login' => 'installer@example.test' ), $saved['fields'] );
			$this->assertGreaterThanOrEqual( time(), $saved['until'] );
			$this->assertLessThanOrEqual( time() + 300, $saved['until'] );
			$this->assertSame( array(), FormRecovery::consume( 'password_reset' ), 'Without the native session cookie, no input is recovered.' );
			$this->assertSame( array( 'user_login' => 'installer@example.test' ), FormRecovery::consume( 'password_reset', true ), 'The current request can consume a session it just created, before its cookie returns.' );
			FormRecovery::save( 'password_reset', array( 'user_login' => 'installer@example.test' ) );
			$_COOKIE['wp_woocommerce_session_fixture'] = 'native-presence';
			$this->assertSame( array( 'user_login' => 'installer@example.test' ), FormRecovery::consume( 'password_reset' ) );
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
			$this->assertSame( array( 'user_login' => 'installer@example.test' ), FormRecovery::consume( 'password_reset' ) );
			ResetNotice::capture_submission( new \WP_Error(), false );
			$this->assertSame( array( 'user_login' => 'installer@example.test' ), FormRecovery::consume( 'password_reset' ), 'A native unknown-user refusal keeps the entered text.' );
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
