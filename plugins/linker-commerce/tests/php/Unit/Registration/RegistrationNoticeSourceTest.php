<?php
/**
 * The native account records who should receive each registration notice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\RegistrationMessage;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/** Native user metadata owns pending registration notices. */
final class RegistrationNoticeSourceTest extends TestCase {

	/** Saving a native account does not call Woo's mailer or render a template. */
	public function test_new_account_records_original_recipients_and_purpose_before_mail_is_available(): void {
		WP_Mock::userFunction( 'WC' )->never();
		WP_Mock::userFunction( 'wp_salt' )->with( 'auth' )->andReturn( 'test-auth-salt' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		$user                  = new \WP_User();
		$user->ID              = 27;
		$user->user_email      = 'owner@example.test';
		$user->user_login      = 'original-login';
		$user->display_name    = 'Original Name';
		$user->user_registered = '2026-11-21 00:00:00';
		$values                = array( 'billing_company' => 'Original Company' );
		$plans                 = RegistrationMessage::pending( $user, $values, 'de_DE_formal', '651d7ba9-4520-488c-b69c-10cbd6551bb0', str_repeat( 'c', 64 ) );
		foreach ( array( 'team', 'received' ) as $kind ) {
			$this->assertSame( 'pending', $plans[ $kind ]['state'] );
			$this->assertSame( $kind, $plans[ $kind ]['binding']['kind'] );
			$this->assertSame( 27, $plans[ $kind ]['binding']['account'] );
			$this->assertSame( 'owner@example.test', $plans[ $kind ]['source']['user']['user_email'] );
			$this->assertSame( 'de_DE_formal', $plans[ $kind ]['source']['locale'] );
		}
		$this->assertSame( $values, $plans['team']['source']['values'] );
		$this->assertSame( array(), $plans['received']['source']['values'] );
	}
}
