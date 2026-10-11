<?php
/**
 * One message from the contact form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Inquiry\OrderLocale;
use WP_Error;

/**
 * What the visitor sent through the contact form, validated: the one shape
 * the receipt, the team letter and the page's state read (ticket #68, GAP-8).
 */
final class Submission {


	/**
	 * Longest name, company and email the form accepts (the plugin's other
	 * fields carry 190 too).
	 */
	public const MAX_TEXT = 190;

	/**
	 * Longest message the form accepts (the site's previous contact form).
	 */
	public const MAX_MESSAGE = 5000;

	/**
	 * Sets up the submission.
	 *
	 * @param string $name    The visitor's name.
	 * @param string $email   Where the reply goes.
	 * @param string $company The visitor's company, '' when not given.
	 * @param string $message The question.
	 * @param string $locale  The language the visitor wrote in.
	 */
	private function __construct(
		public readonly string $name,
		public readonly string $email,
		public readonly string $company,
		public readonly string $message,
		public readonly string $locale
	) {
	}

	/**
	 * The submission the posted values make, or the reason they do not.
	 *
	 * The language is the language the form posted — the same reader the
	 * inquiry chain uses (OrderLocale::current()), so a message from the
	 * German page is answered in German.
	 *
	 * @param  array<string, mixed> $post The posted values, unslashed.
	 * @return self|WP_Error
	 */
	public static function from_post( array $post ): self|WP_Error {
		$name    = self::text( $post['name'] ?? '' );
		$email   = self::text( $post['email'] ?? '' );
		$company = self::text( $post['company'] ?? '' );
		$message = self::long_text( $post['message'] ?? '' );
		$consent = isset( $post['consent'] ) && '1' === (string) $post['consent'];

		if ( '' === $name ) {
			return new WP_Error( 'linker_contact_name', __( 'Please add your name.', 'linker-commerce' ) );
		}
		if ( ! is_email( $email ) ) {
			return new WP_Error( 'linker_contact_email', __( 'Please add an email address we can reply to.', 'linker-commerce' ) );
		}
		if ( '' === $message ) {
			return new WP_Error( 'linker_contact_message', __( 'Please write your message.', 'linker-commerce' ) );
		}
		if ( ! $consent ) {
			return new WP_Error( 'linker_contact_consent', __( 'Please agree to the use of your details for the reply.', 'linker-commerce' ) );
		}

		return new self( $name, strtolower( $email ), $company, $message, OrderLocale::current() );
	}

	/**
	 * Whether the visitor wrote in German.
	 */
	public function is_german(): bool {
		return str_starts_with( strtolower( $this->locale ), 'de' );
	}

	/**
	 * One line of text, trimmed to the field's length.
	 *
	 * @param mixed $value Posted value.
	 */
	private static function text( $value ): string {
		return mb_substr( trim( sanitize_text_field( is_scalar( $value ) ? (string) $value : '' ) ), 0, self::MAX_TEXT );
	}

	/**
	 * The message, trimmed to its length.
	 *
	 * @param mixed $value Posted value.
	 */
	private static function long_text( $value ): string {
		return mb_substr( trim( sanitize_textarea_field( is_scalar( $value ) ? (string) $value : '' ) ), 0, self::MAX_MESSAGE );
	}
}
