<?php
/**
 * Tests for the language of an order and of its emails.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Woo;

use Linker\I18n\Languages;
use Linker\I18n\Tests\Unit\PolylangDouble;
use Linker\I18n\Woo\Orders;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Orders.
 *
 * @covers \Linker\I18n\Woo\Orders
 */
final class OrdersTest extends TestCase {

	/**
	 * The order mock, with the meta it answers.
	 *
	 * @param array<string, string> $meta Meta key => value.
	 * @return \WC_Order&Mockery\MockInterface
	 */
	private function order( array $meta = array() ): \WC_Order {
		$order = Mockery::mock( \WC_Order::class );
		$order->shouldReceive( 'get_meta' )->andReturnUsing(
			static fn ( string $key ): string => $meta[ $key ] ?? ''
		)->byDefault();
		return $order;
	}

	/**
	 * The checkout POST's lang field is the recorded language even when
	 * Polylang's answer for the request is the default one: the checkout
	 * submits by AJAX to an address without the language's URL prefix, where
	 * the German inquiry was recorded as English (#9, #11's replay).
	 */
	public function test_record_takes_the_posted_language(): void {
		PolylangDouble::mock( current: 'en' );
		$_POST['lang'] = 'de';
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => $key ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( mixed $value ): mixed => $value ) );

		$order = $this->order();
		$order->shouldReceive( 'update_meta_data' )->once()->with( Orders::LANGUAGE, 'de' );

		( new Orders( new Languages() ) )->record( $order );

		unset( $_POST['lang'] );
		$this->assertConditionsMet();
	}

	/**
	 * Without a posted language the request's own language is recorded — the
	 * Store API path, which names the language in its URL.
	 */
	public function test_record_falls_back_to_the_current_language(): void {
		PolylangDouble::mock( current: 'de' );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => $key ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( mixed $value ): mixed => $value ) );

		$order = $this->order();
		$order->shouldReceive( 'update_meta_data' )->once()->with( Orders::LANGUAGE, 'de' );

		( new Orders( new Languages() ) )->record( $order );

		$this->assertConditionsMet();
	}

	/**
	 * A posted value that names no language of the site is not recorded: the
	 * request's language answers instead.
	 */
	public function test_record_ignores_an_unknown_posted_language(): void {
		PolylangDouble::mock( current: 'en' );
		$_POST['lang'] = 'fr';
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => $key ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( mixed $value ): mixed => $value ) );

		$order = $this->order();
		$order->shouldReceive( 'update_meta_data' )->once()->with( Orders::LANGUAGE, 'en' );

		( new Orders( new Languages() ) )->record( $order );

		unset( $_POST['lang'] );
		$this->assertConditionsMet();
	}

	/**
	 * The slug meta is the authority when it carries a language of the site.
	 */
	public function test_language_of_reads_the_authority_meta(): void {
		PolylangDouble::mock();

		$this->assertSame( 'de', ( new Orders( new Languages() ) )->language_of( $this->order( array( Orders::LANGUAGE => 'de' ) ) ) );
	}

	/**
	 * An order from before the authority meta existed carries linker-commerce's
	 * locale (#11); its language is read from there.
	 */
	public function test_language_of_falls_back_to_the_legacy_locale(): void {
		PolylangDouble::mock();

		$this->assertSame( 'de', ( new Orders( new Languages() ) )->language_of( $this->order( array( Orders::LEGACY_LOCALE => 'de_DE_formal' ) ) ) );
	}

	/**
	 * An order with neither meta was placed in the site's source language.
	 */
	public function test_language_of_defaults_to_english(): void {
		PolylangDouble::mock();

		$this->assertSame( 'en', ( new Orders( new Languages() ) )->language_of( $this->order() ) );
	}
}
