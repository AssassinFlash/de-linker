<?php
/**
 * Tests for the VAT-check notification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Emails\VatReviewEmail;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * Tests for VatReviewEmail.
 *
 * @covers \Linker\Commerce\Registration\Emails\VatReviewEmail
 */
final class VatReviewEmailTest extends TestCase {

	/**
	 * The plugin's text domain may reload while an email renders (LocaleSwitch).
	 */
	public function setUp(): void {
		parent::setUp();
		$this->reload_plugin_textdomain();
	}

	/**
	 * A changed verdict is sent to the team with the verdict before and after.
	 */
	public function test_notifies_the_team_of_the_change(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		$this->options( array( 'WPLANG' => '' ) );
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => 'Solarbau GmbH' ) );
		$user     = new WP_User();
		$user->ID = 5;
		WP_Mock::userFunction( 'get_userdata', array( 'return' => $user ) );
		$this->expect_action_on_any( VatProfile::CHANGED_ACTION . '_notification', VatReviewEmail::class, 'trigger', 10, 3 );
		$this->allow_locale_switch( 'en_US' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_vat_review', 'sales@sunriverinverter.com' );

		WP_Mock::expectFilterAdded( 'pre_wp_mail', \Mockery::type( \Closure::class ), 9, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_email_log_enabled', \Mockery::type( \Closure::class ) );
		$email = new VatReviewEmail( '/plugin/linker-commerce.php', new Options(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() );
		$email->trigger( 5, VatProfile::INVALID, VatProfile::VALID );

		$this->assertSame( 'Solarbau GmbH', $email->placeholders['{company}'] );
		$this->assertSame( 'VAT check changed: {company}', $email->get_default_subject() );
		$this->assertConditionsMet();
	}
}
