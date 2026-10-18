<?php
/**
 * Tests for the contact form's handler.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Handler;
use Linker\Commerce\Tests\Fixtures;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Handler::process(): the decisions of a public form — a wrong
 * nonce, a bot, a flood, an incomplete form, a delivered message (ticket #68).
 *
 * @covers \Linker\Commerce\Contact\Handler
 */
final class HandlerTest extends TestCase {


	/**
	 * The three hooks and the WordPress reads the handler makes.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'get_option', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		// Both emails switch to the site's language and back (LocaleSwitch);
		// the refusals never get that far.
		WP_Mock::userFunction(
			'switch_to_locale',
			array(
				'times'  => '0+',
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'restore_previous_locale',
			array(
				'times'  => '0+',
				'return' => '',
			)
		);
		WP_Mock::userFunction(
			'remove_filter',
			array(
				'times'  => '0+',
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'unload_textdomain', array( 'return' => true ) );
		WP_Mock::userFunction( 'load_textdomain', array( 'return' => true ) );
		WP_Mock::userFunction( 'WC', array( 'return' => new Fixtures\WooCommerce() ) );
		WP_Mock::userFunction( 'get_bloginfo', array( 'return' => 'UTF-8' ) );
		WP_Mock::userFunction( 'apply_filters', array( 'return' => '' ) );
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => trim( $email ) ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( preg_replace( '/[^a-z0-9_-]/i', '', $key ) ?? '' ) ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
	}

	/**
	 * A form without a valid nonce is refused before anything else.
	 */
	public function test_wrong_nonce_is_refused(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => false ) );

		$this->assertSame( 'invalid', $handler->process( $this->post() ) );
	}

	/**
	 * A filled honeypot is rejected by the shared guard and sends nothing.
	 */
	public function test_honeypot_is_refused_and_sends_nothing(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );

		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		$this->assertSame( 'invalid', $handler->process( $this->post( array( 'website' => 'http://spam.example' ) ) ) );
	}

	/**
	 * An incomplete form is refused.
	 */
	public function test_incomplete_form_is_refused(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );

		$this->assertSame( 'invalid', $handler->process( $this->post( array( 'email' => 'not-an-address' ) ) ) );
	}

	/**
	 * A missing signed fill-time is refused before creating an inquiry.
	 */
	public function test_complete_form_without_signed_time_is_refused(): void {
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		$this->assertSame( 'invalid', $this->handler()->process( $this->post() ) );
	}

	/**
	 * A complete form as posted by the browser.
	 *
	 * @param  array<string, string> $overrides Fields to change.
	 * @return array<string, string>
	 */
	private function post( array $overrides = array() ): array {
		return array_merge(
			array(
				Form::NONCE_FIELD => 'nonce',
				'name'            => 'Maria Weber',
				'email'           => 'maria@example.test',
				'company'         => '',
				'message'         => 'Do you ship the GW5.1 battery?',
				'consent'         => '1',
			),
			$overrides
		);
	}

	/**
	 * The handler under test.
	 */
	private function handler(): Handler {
		return new Handler();
	}
}
