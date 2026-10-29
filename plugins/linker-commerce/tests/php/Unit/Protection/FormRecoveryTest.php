<?php
/**
 * Recovery data remains specific to each native form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\FormRecovery;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Password recovery carries only the editable login.
 *
 * @covers \Linker\Commerce\Protection\FormRecovery
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
		$this->options( array() );
		$old_cookies = $_COOKIE;
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
		} finally {
			$_COOKIE = $old_cookies;
		}
	}
}
