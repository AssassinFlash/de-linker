<?php
/**
 * Tests for the contact form's submission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Tests for Submission: what the posted values must hold (ticket #68).
 *
 * @covers \Linker\Commerce\Contact\Submission
 */
final class SubmissionTest extends TestCase {


	/**
	 * The WordPress sanitizers the submission reads: text fields pass through,
	 * an email is validated like WordPress does.
	 */
	private function sanitizers(): void {
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( preg_replace( '/[^a-z0-9_-]/i', '', $key ) ?? '' ) ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
	}

	/**
	 * A complete form makes a submission in the language the form posted, and
	 * the topic the card's select carried travels with it.
	 */
	public function test_complete_form_makes_a_submission(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		$this->sanitizers();
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );

		$submission = Submission::from_post(
			array(
				'name'    => '  Maria Weber ',
				'email'   => 'Maria@Example.Test',
				'company' => 'Weber Solar',
				'message' => "Do you ship the GW5.1 battery?\nThanks.",
				'intent'  => 'offer',
				'consent' => '1',
			)
		);

		$this->assertInstanceOf( Submission::class, $submission );
		$this->assertSame( 'Maria Weber', $submission->name );
		$this->assertSame( 'maria@example.test', $submission->email );
		$this->assertSame( 'Weber Solar', $submission->company );
		$this->assertSame( "Do you ship the GW5.1 battery?\nThanks.", $submission->message );
		$this->assertSame( 'offer', $submission->intent );
		$this->assertTrue( $submission->is_german() );
	}

	/**
	 * The topic is one of the card's; a request without it, or with a value the
	 * card does not offer, is the general question — the mail never repeats an
	 * arbitrary string back.
	 */
	public function test_topic_falls_back_to_the_general_question(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		$this->sanitizers();
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );

		$complete = array(
			'name'    => 'Maria',
			'email'   => 'maria@example.test',
			'message' => 'A question.',
			'consent' => '1',
		);

		$missing = Submission::from_post( $complete );
		$this->assertInstanceOf( Submission::class, $missing );
		$this->assertSame( Submission::INTENT_DEFAULT, $missing->intent );

		$unknown = Submission::from_post( array_merge( $complete, array( 'intent' => 'something else' ) ) );
		$this->assertInstanceOf( Submission::class, $unknown );
		$this->assertSame( Submission::INTENT_DEFAULT, $unknown->intent );

		$known = Submission::from_post( array_merge( $complete, array( 'intent' => 'support' ) ) );
		$this->assertInstanceOf( Submission::class, $known );
		$this->assertSame( 'support', $known->intent );
	}

	/**
	 * Company is optional; name, a valid email, a message and the consent are not.
	 */
	public function test_refuses_incomplete_forms(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		$this->sanitizers();
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );

		$complete = array(
			'name'    => 'Maria',
			'email'   => 'maria@example.test',
			'message' => 'A question.',
			'consent' => '1',
		);

		$no_name = Submission::from_post( array_merge( $complete, array( 'name' => '  ' ) ) );
		$this->assertInstanceOf( WP_Error::class, $no_name );
		$this->assertSame( 'linker_contact_name', $no_name->get_error_code() );

		$bad_email = Submission::from_post( array_merge( $complete, array( 'email' => 'not-an-address' ) ) );
		$this->assertInstanceOf( WP_Error::class, $bad_email );
		$this->assertSame( 'linker_contact_email', $bad_email->get_error_code() );

		$no_message = Submission::from_post( array_merge( $complete, array( 'message' => '' ) ) );
		$this->assertInstanceOf( WP_Error::class, $no_message );
		$this->assertSame( 'linker_contact_message', $no_message->get_error_code() );

		$no_consent = Submission::from_post( array_merge( $complete, array( 'consent' => '' ) ) );
		$this->assertInstanceOf( WP_Error::class, $no_consent );
		$this->assertSame( 'linker_contact_consent', $no_consent->get_error_code() );

		$ok = Submission::from_post( $complete );
		$this->assertInstanceOf( Submission::class, $ok );
		$this->assertSame( '', $ok->company );
		$this->assertFalse( $ok->is_german() );
	}

	/**
	 * The message is capped at the form's own limit.
	 */
	public function test_message_length_is_capped(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		$this->sanitizers();
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );

		$submission = Submission::from_post(
			array(
				'name'    => 'Maria',
				'email'   => 'maria@example.test',
				'message' => str_repeat( 'a', Submission::MAX_MESSAGE + 100 ),
				'consent' => '1',
			)
		);

		$this->assertInstanceOf( Submission::class, $submission );
		$this->assertSame( Submission::MAX_MESSAGE, mb_strlen( $submission->message ) );
	}
}
