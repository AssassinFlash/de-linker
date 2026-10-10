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
	 * Without settings, notifications go to sales@de-linker.com (AGENTS.md §2) and numbers start with PI.
	 */
	public function test_defaults(): void {
		$this->options( array() );
		$options = new Options();

		$this->assertSame( 'sales@de-linker.com', $options->team_to() );
		$this->assertSame( array(), $options->team_bcc() );
		$this->assertSame( 'PI', $options->proforma_prefix() );
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
	 * Blind copies: one per line or separated by commas; invalid, duplicate and the team mailbox itself are left out.
	 */
	public function test_blind_copies_are_cleaned(): void {
		$this->options(
			array(
				Options::TEAM_TO  => 'sales@de-linker.com',
				Options::TEAM_BCC => "one@example.test\nnot-an-address, two@example.test;one@example.test\nsales@de-linker.com",
			)
		);

		$this->assertSame( array( 'one@example.test', 'two@example.test' ), ( new Options() )->team_bcc() );
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

		$this->assertSame( 'PI', $options->proforma_prefix() );
		$this->assertSame( '', $options->bank()['iban'] );
	}
}
