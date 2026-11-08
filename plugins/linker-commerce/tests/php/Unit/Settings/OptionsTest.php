<?php
/**
 * Tests for the plugin settings.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Settings;

use Linker\Commerce\Mail\Identity;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Options.
 *
 * @covers \Linker\Commerce\Mail\Identity
 * @covers \Linker\Commerce\Settings\Options
 */
final class OptionsTest extends TestCase {

	/**
	 * Email sanitizing as WordPress does it for the values used here.
	 */
	public function setUp(): void {
		parent::setUp();
		$countries = \Mockery::mock();
		$countries->allows( 'get_countries' )->andReturn( array( 'DE' => 'Germany' ) );
		$woocommerce            = new \stdClass();
		$woocommerce->countries = $countries;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => trim( $email ) ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
	}

	/**
	 * Without settings, customers see sales@de-linker.com, internal notifications go to
	 * sales@sunriverinverter.com (AGENTS.md §2, 2026-10-17) and numbers start with DLK-PF.
	 */
	public function test_defaults(): void {
		$this->options( array() );
		$options = new Options();

		$this->assertSame( 'sales@de-linker.com', $options->team_mailbox() );
		$this->assertSame( 'sales@sunriverinverter.com', $options->notify_to() );
		$this->assertSame( 'sales@sunriverinverter.com', $options->notify_sender()->email );
		$this->assertSame( array(), $options->notify_bcc() );
		$this->assertSame(
			array(
				'name'  => '',
				'email' => 'sales@de-linker.com',
				'phone' => '',
			),
			$options->contact()
		);
	}

	/**
	 * The internal sender is independent of the recipient and public mailbox.
	 *
	 * @testWith ["alerts@example.test", "alerts@example.test"]
	 *           ["", "sales@sunriverinverter.com"]
	 *           ["not-an-address", "sales@sunriverinverter.com"]
	 *           [["alerts@example.test"], "sales@sunriverinverter.com"]
	 *
	 * @param mixed  $saved    Saved option.
	 * @param string $expected Effective sender.
	 */
	public function test_internal_sender( $saved, string $expected ): void {
		$this->options(
			array(
				'linker_commerce_notify_from' => $saved,
				Options::NOTIFY_TO            => 'recipient@example.test',
				Options::TEAM_TO              => 'public@example.test',
			)
		);
		$sender = ( new Options() )->notify_sender();
		$this->assertInstanceOf( Identity::class, $sender );
		$this->assertSame( 'Linker', $sender->name );
		$this->assertSame( $expected, $sender->email );
	}

	/**
	 * Blind copies: one per line or separated by commas; invalid, duplicate and the notification recipient itself are left out.
	 */
	public function test_blind_copies_are_cleaned(): void {
		$this->options(
			array(
				Options::NOTIFY_TO  => 'alerts@example.test',
				Options::NOTIFY_BCC => "one@example.test\nnot-an-address, two@example.test;one@example.test\nalerts@example.test",
			)
		);

		$this->assertSame( array( 'one@example.test', 'two@example.test' ), ( new Options() )->notify_bcc() );
	}

	/**
	 * The two addresses are separate settings: pointing internal notifications elsewhere leaves every
	 * address customers see — the team mailbox, the Proforma seller, the contact fallback — on the
	 * team mailbox (owner ruling 2026-10-17), and the other way round.
	 */
	public function test_internal_and_customer_addresses_are_independent(): void {
		$this->options(
			array(
				Options::NOTIFY_TO            => 'sales@sunriverinverter.com',
				Options::NOTIFY_BCC           => 'chester@de-linker.com',
				'woocommerce_default_country' => 'DE',
			)
		);
		$options = new Options();

		$this->assertSame( 'sales@de-linker.com', $options->team_mailbox() );
		$this->assertSame( 'sales@de-linker.com', $options->contact()['email'] );
		$this->assertSame( 'sales@sunriverinverter.com', $options->notify_to() );
		$this->assertSame( array( 'chester@de-linker.com' ), $options->notify_bcc() );
	}

	/**
	 * A changed team mailbox moves what customers see and never the notification recipient.
	 */
	public function test_team_mailbox_is_not_the_notification_recipient(): void {
		$this->options(
			array(
				Options::TEAM_TO              => 'team@example.test',
				'woocommerce_default_country' => 'DE',
			)
		);
		$this->assertSame( 'sales@sunriverinverter.com', ( new Options() )->notify_to(), 'The team mailbox never becomes the notification recipient.' );
	}
}
