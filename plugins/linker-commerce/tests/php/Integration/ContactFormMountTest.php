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
 * The instance this suite runs against is supposed to be the live snapshot:
 * a missing page is a non-200 here, and a non-200 is a failed test, never a
 * skip — a serving instance without the snapshot says something is wrong.
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
	/**
	 * /contact/ renders the card. The stored page still has the old mount;
	 * the response does not. The card's own words are the ones the copy
	 * review settled (docs/acceptance/2026-10-15/contact-card/copy-review.md).
	 */
	public function test_the_english_page_renders_the_form(): void {
		$html = $this->get( '/contact/' );

		$this->assertStringContainsString( '<form class="linker-contact-form', $html );
		$this->assertStringContainsString( 'name="message"', $html );
		$this->assertStringContainsString( 'type="submit"', $html );
		$this->assertStringContainsString( 'linker-contact-head', $html );
		$this->assertStringContainsString( 'What can we help with?', $html );
		$this->assertStringContainsString( 'linker-contact-rail', $html );
		$this->assertStringContainsString( 'Prefer email?', $html );
		$this->assertStringContainsString( 'Send message', $html );
		$this->assertStringNotContainsString( '[' . Form::SHORTCODE . ']', $html, 'the shortcode is expanded, not left as text' );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
		$this->assertStringNotContainsString( 'If the form is unavailable', $html );
	}

	/**
	 * The German twin renders the same card, in German.
	 */
	public function test_the_german_page_renders_the_form_in_german(): void {
		$html = $this->get( '/de/kontakt/' );

		$this->assertStringContainsString( '<form class="linker-contact-form', $html );
		$this->assertStringContainsString( 'name="lang" value="de"', $html );
		$this->assertStringContainsString( 'Ihre Frage', $html );
		$this->assertStringContainsString( 'Wie können wir helfen?', $html );
		$this->assertStringContainsString( 'Wohin dürfen wir antworten?', $html );
		$this->assertStringContainsString( 'Nachricht senden', $html );
		$this->assertStringContainsString( 'Lieber per E-Mail?', $html );
		$this->assertStringContainsString( 'Noch in der Orientierung?', $html );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
	}

	/**
	 * The sent state is the form's own redirect state, rendered in place of
	 * the fields.
	 */
	public function test_the_sent_state_renders_instead_of_the_fields(): void {
		$html = $this->get( '/contact/?contact=sent' );

		$this->assertStringContainsString( 'linker-form-success', $html );
		$this->assertStringContainsString( 'Thank you. Your message is with the Linker team.', $html );
		$this->assertStringNotContainsString( 'name="message"', $html );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
	}

	/**
	 * One front-end GET. A non-200 is a failed test, not a skip: the instance
	 * this suite runs against is supposed to be serving the live snapshot.
	 *
	 * @param string $path Path on the instance.
	 */
	private function get( string $path ): string {
		$response = wp_remote_get( $this->front() . $path );
		$this->assertIsArray( $response, $response instanceof \WP_Error ? $response->get_error_message() : 'the request did not return a response' );
		$this->assertSame( 200, (int) wp_remote_retrieve_response_code( $response ), "{$path} answers non-200: the instance is not serving the live snapshot pages (just pull load)." );
		return (string) wp_remote_retrieve_body( $response );
	}
}
