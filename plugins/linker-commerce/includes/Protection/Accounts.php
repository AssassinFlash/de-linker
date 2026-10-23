<?php
/**
 * Native account boundaries run before account creation, VAT and reset mail.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;
use WP_User;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\Website;

/** Core authentication, password checks and customer approval stay unchanged. */
final class Accounts {
	/**
	 * Current native registration dispatch.
	 *
	 * @var array<string,mixed>|null
	 */
	private ?array $registration = null;
	/**
	 * Current native reset dispatch.
	 *
	 * @var array<string,mixed>|null
	 */
	private ?array $reset = null;
	/**
	 * Native reset subject; no reset key is stored here.
	 *
	 * @var int
	 */
	private int $reset_user = 0;

	/** Native form hooks preserve their own nonce and permission mechanisms. */
	public function register(): void {
		add_action( 'woocommerce_register_form', array( $this, 'registration_fields' ) );
		add_filter( 'woocommerce_process_registration_errors', array( $this, 'woocommerce_registration' ), 30, 4 );
		add_action( 'woocommerce_created_customer', array( $this, 'created' ), 1 );
		add_action( 'register_form', array( $this, 'registration_fields' ) );
		add_filter( 'registration_errors', array( $this, 'native_registration' ), 30, 3 );
		add_action( 'user_register', array( $this, 'created' ), 1 );
		add_action( 'woocommerce_lostpassword_form', array( $this, 'reset_fields' ) );
		add_action( 'lostpassword_form', array( $this, 'reset_fields' ) );
		add_action( 'lostpassword_post', array( $this, 'password_reset' ), 30, 2 );
		add_action( 'profile_update', array( $this, 'reset_created' ) );
	}

	/** Registration fields are appended within the existing native form. */
	public function registration_fields(): void {
		if ( Business::enabled() ) {
			wp_nonce_field( 'linker_native_registration', 'linker_native_registration_nonce' );
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- FormFields escapes every variable.
			echo FormFields::render( 'registration' );
		}
	}

	/** Reset verification does not alter password or reset token semantics. */
	public function reset_fields(): void {
		if ( Business::enabled() ) {
			wp_nonce_field( 'linker_password_reset', 'linker_password_reset_nonce' );
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- FormFields escapes every variable.
			echo FormFields::render( 'password_reset' );
		}
	}

	/**
	 * Woo already checked its own form nonce; this filter precedes customer save/VAT.
	 *
	 * @param WP_Error $errors Existing native validation errors.
	 * @param string   $username Native username.
	 * @param mixed    $password Native password, deliberately ignored.
	 * @param mixed    $email Native email, validated before admission.
	 */
	public function woocommerce_registration( WP_Error $errors, string $username = '', #[\SensitiveParameter] mixed $password = '', mixed $email = '' ): WP_Error {
		unset( $password );
		if ( ! is_string( $email ) ) {
			// phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Preserve Woo's native validated-email error and existing translations.
			$errors->add( 'registration-error-invalid-email', __( 'Please provide a valid email address.', 'woocommerce' ) );
			return $errors;
		}
		return $this->registration( $errors, $username, $email, false );
	}

	/**
	 * Core register_new_user has no built-in CSRF nonce: require our own in its form.
	 *
	 * @param WP_Error $errors Existing validation errors.
	 * @param string   $username Native username.
	 * @param string   $email Validated native email.
	 */
	public function native_registration( WP_Error $errors, string $username, string $email ): WP_Error {
		return $this->registration( $errors, $username, $email, true );
	}

	/**
	 * Use only business fields, never password or reset tokens in a fingerprint.
	 *
	 * @param WP_Error $errors Native errors.
	 * @param string   $username Native login.
	 * @param string   $email Validated address.
	 * @param bool     $core Core registration requires an additional CSRF nonce.
	 */
	private function registration( WP_Error $errors, string $username, string $email, bool $core ): WP_Error {
		if ( ! Business::enabled() || $errors->has_errors() ) {
			return $errors;
		}
		$post = self::post();
		if ( ! is_email( $email ) ) {
			// phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Preserve Woo's native validated-email error and existing translations.
			$errors->add( 'registration-error-invalid-email', __( 'Please provide a valid email address.', 'woocommerce' ) );
			return $errors;
		}
		if ( 'enforce' === Configuration::current()->mode && $core && ! wp_verify_nonce( self::text( $post, 'linker_native_registration_nonce' ), 'linker_native_registration' ) ) {
			$errors->add( 'linker_registration_verification', __( 'Please verify your registration and try again.', 'linker-commerce' ) );
			return $errors;
		}
		$payload = array(
			'email'    => strtolower( $email ),
			'username' => $username,
		);
		foreach ( array( 'billing_company', 'billing_first_name', 'billing_last_name', 'billing_country', VatProfile::VAT_META, CustomerRole::META, Website::META ) as $key ) {
			$payload[ $key ] = self::text( $post, $key );
		}
		$result = Operation::begin( 'registration', $post, $payload );
		if ( is_wp_error( $result ) ) {
			$errors->add( $result->get_error_code(), $result->get_error_message() );
		} else {
			$this->registration = $result;
		}
		return $errors;
	}

	/**
	 * Earliest native created hook precedes VIES and registration mail.
	 *
	 * @param int $id Native user id.
	 */
	public function created( int $id ): void {
		if ( null !== $this->registration ) {
			Operation::finish( $this->registration, $id );
			$this->registration = null;
		}
	}

	/**
	 * Core calls this before generating a reset key or dispatching reset mail.
	 *
	 * @param WP_Error      $errors Native errors.
	 * @param WP_User|false $user Resolved native user, never exposed in public output.
	 */
	public function password_reset( WP_Error $errors, WP_User|false $user ): void {
		if ( ! Business::enabled() || $errors->has_errors() || ! $user instanceof WP_User ) {
			return;
		}
		$post = self::post();
		\Linker\Commerce\Mail\ResetNotice::remember( isset( $post['user_login'] ) && is_string( $post['user_login'] ) ? $post['user_login'] : '' );
		if ( 'enforce' === Configuration::current()->mode && ! wp_verify_nonce( self::text( $post, 'linker_password_reset_nonce' ), 'linker_password_reset' ) ) {
			$errors->add( 'linker_reset_verification', __( 'Please verify your request and try again.', 'linker-commerce' ) );
			return;
		}
		$result = Operation::begin( 'password_reset', $post, array( 'email' => strtolower( $user->user_email ) ) );
		if ( is_wp_error( $result ) ) {
			$errors->add( $result->get_error_code(), $result->get_error_message() );
		} else {
			$reserved = \Linker\Commerce\Mail\ResetNotice::reserve( $user, (string) ( $result['id'] ?? wp_generate_uuid4() ) );
			if ( is_wp_error( $reserved ) ) {
				$errors->add( 'linker_reset_capacity', __( 'Password reset is temporarily unavailable. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
				return;
			}
			$this->reset      = $result;
			$this->reset_user = $user->ID;
		}
	}

	/**
	 * The reset key was saved; delivered mail is still owned by the native mail pipeline.
	 *
	 * @param int $id Native updated user id.
	 */
	public function reset_created( int $id ): void {
		if ( null !== $this->reset && $id === $this->reset_user ) {
			Operation::finish( $this->reset );
			$this->reset = null;
		}
	}

	/**
	 * Current native form fields, unslashed.
	 *
	 * @return array<string,mixed>
	 */
	private static function post(): array {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Native handler checked its nonce, or the extra nonce is checked by the caller.
		return wp_unslash( $_POST );
	}

	/**
	 * One allowlisted field, with the registration's existing 190-character ceiling.
	 *
	 * @param array<string,mixed> $post Native transport.
	 * @param string              $key Field name.
	 */
	private static function text( array $post, string $key ): string {
		return isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? mb_substr( sanitize_text_field( $post[ $key ] ), 0, 190 ) : '';
	}
}
