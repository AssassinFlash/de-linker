<?php
/**
 * The contact form, as the instance's own front end renders it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Form;

/**
 * The deployed contact pages store the old fallback mount. The front end
 * replaces it: the response contains the form, not the shortcode text and not
 * the fallback line. This is an HTTP read of the instance, the same path a
 * browser uses. It does not write page content.
 *
 * PHPUnit's process is not that path. Its global backup restores
 * `$shortcode_tags` to the empty array it had before WordPress loaded, so an
 * in-process `apply_filters( 'the_content' )` cannot see the shortcode the
 * front end expands. Measured on the contactform instance, 2026-10-14.
 *
 * @covers \Linker\Commerce\Contact\Module
 */
final class ContactFormMountTest extends IntegrationTestCase {

	/**
	 * The instance's front end. The integration bootstrap does not name a
	 * port; the test reads it from the instance WordPress serves.
	 */
	private function front(): string {
		$home = home_url( '/' );
		$this->assertNotSame( '', $home );
		return rtrim( $home, '/' );
	}

	/**
	 * The id of a snapshot page, or a skip: an instance the live snapshot was
	 * not loaded onto has no such page, and a red 404 would say nothing about
	 * this module.
	 *
	 * @param string $path The page path, e.g. `contact`.
	 */
	private function page_id_or_skip( string $path ): int {
		$page = get_page_by_path( $path );
		if ( ! $page instanceof \WP_Post ) {
			self::markTestSkipped( "the instance has no page at {$path}; load the live snapshot first (just pull load)" );
		}
		return (int) $page->ID;
	}

	/**
	 * The German twin of the contact page — the page `/de/kontakt/` serves.
	 * Resolved the way the module resolves it (Polylang), with the slug as
	 * the fallback for instances that pair pages differently.
	 */
	private function german_twin_id_or_skip(): int {
		$english = $this->page_id_or_skip( 'contact' );
		$twin    = function_exists( 'pll_get_post' ) ? (int) pll_get_post( $english, 'de' ) : 0;
		if ( $twin > 0 ) {
			return $twin;
		}
		$fallback = get_page_by_path( 'kontakt' );
		if ( $fallback instanceof \WP_Post ) {
			return (int) $fallback->ID;
		}
		self::markTestSkipped( 'the instance has no German twin of the contact page; load the live snapshot first (just pull load)' );
	}

	/**
	 * /contact/ renders the form. The stored page still has the old mount;
	 * the response does not.
	 */
	public function test_the_english_page_renders_the_form(): void {
		$this->page_id_or_skip( 'contact' );
		$html = $this->get( '/contact/' );

		$this->assertStringContainsString( '<form class="linker-contact-form', $html );
		$this->assertStringContainsString( 'name="message"', $html );
		$this->assertStringContainsString( 'type="submit"', $html );
		$this->assertStringNotContainsString( '[' . Form::SHORTCODE . ']', $html, 'the shortcode is expanded, not left as text' );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
		$this->assertStringNotContainsString( 'If the form is unavailable', $html );
	}

	/**
	 * The German twin renders the same form, in German.
	 */
	public function test_the_german_page_renders_the_form_in_german(): void {
		$this->german_twin_id_or_skip();
		$html = $this->get( '/de/kontakt/' );

		$this->assertStringContainsString( '<form class="linker-contact-form', $html );
		$this->assertStringContainsString( 'name="lang" value="de"', $html );
		$this->assertStringContainsString( 'Ihre Frage', $html );
		$this->assertStringContainsString( 'Nachricht senden', $html );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
	}

	/**
	 * The sent state is the form's own redirect state, rendered in place of
	 * the fields.
	 */
	public function test_the_sent_state_renders_instead_of_the_fields(): void {
		$this->page_id_or_skip( 'contact' );
		$html = $this->get( '/contact/?contact=sent' );

		$this->assertStringContainsString( 'linker-form-success', $html );
		$this->assertStringContainsString( 'Thank you. Your message is with the Linker team.', $html );
		$this->assertStringNotContainsString( 'name="message"', $html );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
	}

	/**
	 * One front-end GET. A non-200 is a failed test, not a skip: the instance
	 * this suite runs against is supposed to be serving.
	 *
	 * @param string $path Path on the instance.
	 */
	private function get( string $path ): string {
		$response = wp_remote_get( $this->front() . $path );
		$this->assertIsArray( $response, $response instanceof \WP_Error ? $response->get_error_message() : 'the request did not return a response' );
		$this->assertSame( 200, (int) wp_remote_retrieve_response_code( $response ) );
		return (string) wp_remote_retrieve_body( $response );
	}
}
