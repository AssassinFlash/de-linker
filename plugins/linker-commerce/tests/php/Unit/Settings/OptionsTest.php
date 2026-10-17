<?php
/**
 * Tests for the plugin settings.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Settings;

use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Options.
 *
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
		$this->assertSame( 'sales@sunriverinverter.com', $options->notify_from() );
		$this->assertSame( array(), $options->notify_bcc() );
		$this->assertSame( 'DLK-PF', $options->proforma_prefix() );
		$this->assertSame(
			array(
				'name'  => '',
				'email' => 'sales@de-linker.com',
				'phone' => '',
			),
			$options->contact()
		);
		$this->assertSame( 'Linker Technology GmbH', $options->seller()['name'] );
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
		$this->assertSame( $expected, ( new Options() )->notify_from() );
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
		$this->assertSame( 'sales@de-linker.com', $options->seller()['email'] );
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
		$this->assertSame( 'team@example.test', ( new Options() )->seller()['email'] );
		$this->assertSame( 'sales@sunriverinverter.com', ( new Options() )->notify_to(), 'The team mailbox never becomes the notification recipient.' );
	}

	/**
	 * The seller block reads the store address of WooCommerce's general settings.
	 */
	public function test_seller_uses_the_store_address(): void {
		$this->options(
			array(
				Options::SELLER_NAME          => '',
				Options::SELLER_VAT_ID        => 'DE123456789',
				'woocommerce_store_address'   => 'Steinfeldstraße 3',
				'woocommerce_store_address_2' => '',
				'woocommerce_store_postcode'  => '39179',
				'woocommerce_store_city'      => 'Barleben',
				'woocommerce_default_country' => 'DE:DE-ST',
			)
		);

		$this->assertSame(
			array(
				'name'    => 'Linker Technology GmbH',
				'vat_id'  => 'DE123456789',
				'address' => array( 'Steinfeldstraße 3', '39179 Barleben', 'Germany' ),
				'email'   => 'sales@de-linker.com',
			),
			( new Options() )->seller()
		);
	}

	/**
	 * Values that are not strings read as empty.
	 */
	public function test_non_string_values_read_as_empty(): void {
		$this->options(
			array(
				Options::PROFORMA_PREFIX => array( 'PF' ),
				Options::BANK_IBAN       => 42,
			)
		);
		$options = new Options();

		$this->assertSame( 'DLK-PF', $options->proforma_prefix() );
		$this->assertSame( '', $options->bank()['iban'] );
	}
}
