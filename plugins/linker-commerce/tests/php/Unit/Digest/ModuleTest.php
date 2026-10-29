<?php
/**
 * Tests for the digest module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\DigestEmail;
use Linker\Commerce\Digest\Module;
use Linker\Commerce\Digest\Delivery;
use Linker\Commerce\Digest\Scheduler;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Mock\Matcher\AnyInstance;

/**
 * Tests for Module: the cron hook, the schedule on init, the email class, and
 * the run that sends the digest and schedules the next one.
 *
 * @covers \Linker\Commerce\Digest\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The module hooks the cron action, the init schedule and the email class.
	 */
	public function test_register_adds_the_hooks(): void {
		$module = new Module( '/plugin/linker-commerce.php', new JobStore() );

		WP_Mock::expectActionAdded( Scheduler::HOOK, array( $module, 'run' ) );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectActionAdded( 'init', array( new AnyInstance( Scheduler::class ), 'ensure' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_classes', array( $module, 'add_email' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_styles', array( $module, 'email_styles' ), 10, 2 );

		$module->register();

		$this->assertConditionsMet();
	}

	/**
	 * The digest email joins WooCommerce's email list.
	 */
	public function test_add_email(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->options(
			array(
				Options::TEAM_TO => 'sales@de-linker.com',
				'WPLANG'         => '',
			)
		);
		$module = new Module( '/plugin/linker-commerce.php', new JobStore() );

		$emails = $module->add_email( array() );

		$this->assertSame( array( DigestEmail::class ), array_keys( $emails ) );
		$this->assertInstanceOf( DigestEmail::class, $emails[ DigestEmail::class ] );
	}

	/**
	 * The scheduled task sends one digest — with an empty queue and no
	 * inquiries, still one — and schedules the next 09:00.
	 */
	public function test_run_sends_and_reschedules(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->filter_returns( 'linker_commerce_digest_blocks', null );
		$this->filter_returns(
			'linker_commerce_pending_review_summary',
			array(
				'count'  => 0,
				'oldest' => 0,
				'url'    => 'https://example.test/wp-admin/',
			)
		);
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'https://example.test/wp-admin/' ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof \WP_Error ) );
		WP_Mock::userFunction( 'wc_get_orders', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'wp_clear_scheduled_hook',
			array(
				'times' => 1,
				'args'  => array( Scheduler::HOOK ),
			)
		);
		WP_Mock::userFunction(
			'wp_schedule_single_event',
			array(
				'times' => 1,
				'args'  => array( WP_Mock\Functions::type( 'int' ), Scheduler::HOOK ),
			)
		);

		$delivery = new class() implements Delivery {
			/**
			 * Whether the scheduled run asked for delivery.
			 *
			 * @var bool
			 */
			public bool $sent = false;

			/**
			 * Records the scheduled delivery without rendering mail.
			 *
			 * @param DigestEmail      $email Complete native email producer.
			 * @param array<int,mixed> $blocks Frozen business blocks.
			 */
			public function send( DigestEmail $email, array $blocks ): void {
				$this->sent = true;
			}
		};
		$module   = new Module( '/plugin/linker-commerce.php', new JobStore(), $delivery );
		$module->run();

		$this->assertConditionsMet();
		$this->assertTrue( $delivery->sent );
	}
}
