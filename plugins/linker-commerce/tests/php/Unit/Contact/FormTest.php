<?php
/**
 * Tests for the contact form's markup.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Form: the fields the mail pipeline needs, the protections of a
 * public form, and the states the redirect leaves (ticket #68).
 *
 * @covers \Linker\Commerce\Contact\Form
 */
final class FormTest extends TestCase {


	/**
	 * The form posts to admin-post with a nonce, the page's language and where
	 * to come back to, and carries the fields — a honeypot hidden from people.
	 */
	public function test_renders_the_form(): void {
		$this->plain_text();
		$this->form_environment();
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://site/wp-admin/admin-post.php' ) );
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '<input type="hidden" name="linker_contact_nonce" value="nonce" />' ) );
		WP_Mock::userFunction( 'get_privacy_policy_url', array( 'return' => 'http://site/privacy-policy/' ) );

		$html = ( new Form() )->render();

		$this->assertStringContainsString( '<form class="linker-contact-form', $html );
		$this->assertStringContainsString( 'action="http://site/wp-admin/admin-post.php"', $html );
		$this->assertStringContainsString( 'name="action" value="linker_contact"', $html );
		$this->assertStringContainsString( 'name="lang" value="en"', $html );
		$this->assertStringContainsString( 'name="linker_contact_back" value="http://site/contact/"', $html );
		$this->assertStringContainsString( 'name="linker_contact_nonce"', $html );
		foreach ( array( 'name="message"', 'name="name"', 'name="email"', 'name="company"', 'name="consent"' ) as $field ) {
			$this->assertStringContainsString( $field, $html );
		}
		$this->assertStringContainsString( 'maxlength="' . Submission::MAX_MESSAGE . '"', $html );
		$this->assertStringContainsString( '<div hidden aria-hidden="true">', $html, 'The honeypot is hidden from people.' );
		$this->assertStringContainsString( 'name="website"', $html );
		$this->assertStringContainsString( 'href="http://site/privacy-policy/"', $html );
		$this->assertStringContainsString( 'type="submit"', $html );
	}

	/**
	 * The German page renders German labels.
	 */
	public function test_renders_in_the_page_language(): void {
		$this->plain_text();
		$this->form_environment( 'de_DE_formal' );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://site/wp-admin/admin-post.php' ) );
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_privacy_policy_url', array( 'return' => '' ) );

		$html = ( new Form() )->render();
		$this->assertStringContainsString( 'name="lang" value="de"', $html );
	}

	/**
	 * The redirect's state shows above the form; a fresh visit shows nothing.
	 */
	public function test_state_messages(): void {
		$this->plain_text();
		$this->form_environment();
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://site/wp-admin/admin-post.php' ) );
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_privacy_policy_url', array( 'return' => '' ) );

		$_GET = array();
		$this->assertStringNotContainsString( 'role="status"', ( new Form() )->render() );

		$_GET = array( Form::STATE_PARAM => 'sent' );
		$sent = ( new Form() )->render();
		$this->assertStringContainsString( 'role="status"', $sent );
		$this->assertStringContainsString( 'linker-form-success woocommerce-message', $sent );
		$this->assertStringContainsString( 'Send another message', $sent );
		$this->assertStringNotContainsString( 'type="submit"', $sent, 'A sent message has one follow-up action, not another form.' );

		$_GET    = array( Form::STATE_PARAM => 'invalid' );
		$invalid = ( new Form() )->render();
		$this->assertStringContainsString( 'linker-form-error woocommerce-error', $invalid );
		$this->assertStringContainsString( 'role="alert"', $invalid );
		$this->assertStringContainsString( 'type="submit"', $invalid, 'An invalid submission keeps the form available.' );

		$_GET = array( Form::STATE_PARAM => 'throttled' );
		$this->assertStringContainsString( 'Please try again later', ( new Form() )->render() );

		$_GET = array( Form::STATE_PARAM => 'something-else' );
		$this->assertStringNotContainsString( 'role="status"', ( new Form() )->render() );
		$_GET = array();
	}

	/**
	 * The WordPress reads every render makes. The locale is registered first:
	 * WP_Mock answers with the first matching registration.
	 *
	 * @param string $locale The locale the page is rendered in.
	 */
	private function form_environment( string $locale = 'en_US' ): void {
		WP_Mock::userFunction( 'determine_locale', array( 'return' => $locale ) );
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'         => 28,
						'post_type'  => 'page',
						'post_title' => 'Contact',
					)
				),
			)
		);
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'http://site/contact/' ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( preg_replace( '/[^a-z0-9_-]/i', '', $key ) ?? '' ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
	}
}
