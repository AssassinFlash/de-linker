<?php
/**
 * Tests for the mail module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\EmailLocale;
use Linker\Commerce\Mail\EmailPolicy;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Module;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Mail\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * Every wp_mail() call goes through the outbox; retries, the queue type and the email language are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$this->expect_action_on_any( 'rest_api_init', \Linker\Commerce\Mail\SmtpHealth::class, 'register_routes' );
			$jobs   = new JobStore();
			$outbox = new Outbox( $jobs, new Throttle() );
			$locale = new EmailLocale();
			$policy = new EmailPolicy();

			WP_Mock::expectActionAdded( 'init', array( $jobs, 'register_post_type' ) );
			WP_Mock::expectFilterAdded( 'pre_wp_mail', array( $outbox, 'intercept' ), 10, 2 );
			WP_Mock::expectActionAdded( 'wp_mail_failed', array( $outbox, 'remember_error' ) );
		WP_Mock::expectActionAdded( 'phpmailer_init', array( $outbox, 'configure_mailer' ) );
		WP_Mock::expectActionAdded( Outbox::HOOK, array( $outbox, 'retry' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_allow_switching_email_locale', array( $locale, 'allow' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_allow_restoring_email_locale', array( $locale, 'allow' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_email_classes', array( $policy, 'switch_off_others' ), 1000 );

			( new Module( $outbox, $jobs, $locale, $policy ) )->register();

		$this->assertConditionsMet();
	}
}
