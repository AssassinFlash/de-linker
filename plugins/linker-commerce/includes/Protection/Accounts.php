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
use Linker\Commerce\Registration\RegistrationNotices;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Mail\Capacity;

/**
 * Core authentication, password checks and customer approval stay unchanged.
 */
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

	/**
	 * Native form hooks preserve their own nonce and permission mechanisms.
	 */
	public function register(): void {
		add_action( 'woocommerce_register_form', array( $this, 'registration_fields' ) );
		add_filter( 'woocommerce_process_registration_errors', array( $this, 'woocommerce_registration' ), 30, 4 );
		add_action( 'woocommerce_created_customer', array( $this, 'created' ), 1 );
		add_action( 'register_form', array( $this, 'registration_fields' ) );
		add_filter( 'registration_errors', array( $this, 'native_registration' ), 30, 3 );
		add_action( 'user_register', array( $this, 'created' ), 1 );
		add_filter( 'wp_pre_insert_user_data', array( $this, 'before_create' ), PHP_INT_MAX, 4 );
		add_filter( 'insert_custom_user_meta', array( $this, 'stamp' ), PHP_INT_MAX, 4 );
		add_action( 'user_register', array( $this, 'core_notices' ), 99 );
		add_filter( 'wp_send_new_user_notification_to_user', array( $this, 'core_notification' ), 10, 2 );
		add_filter( 'wp_send_new_user_notification_to_admin', array( $this, 'core_notification' ), 10, 2 );
		add_action( Module::MAINTENANCE, array( RegistrationNotices::class, 'maintain' ) );
		add_action( \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::HOOK, array( RegistrationNotices::class, 'maintain' ) );
		( new \Linker\Commerce\Registration\RegistrationCapacityAdmin() )->register();
		( new \Linker\Commerce\Registration\RegistrationPrivacy() )->register();
		( new \Linker\Commerce\Registration\PendingProfileCapacity() )->register();
		register_shutdown_function( array( $this, 'unfinished' ) );
		add_action( 'woocommerce_lostpassword_form', array( $this, 'reset_fields' ) );
		add_action( 'lostpassword_form', array( $this, 'reset_fields' ) );
		add_action( 'lostpassword_post', array( $this, 'password_reset' ), 30, 2 );
		add_action( 'profile_update', array( $this, 'reset_created' ) );
	}

	/**
	 * Registration fields are appended within the existing native form.
	 */
	public function registration_fields(): void {
		if ( Business::enabled() ) {
			wp_nonce_field( 'linker_native_registration', 'linker_native_registration_nonce' );
         // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- FormFields escapes every variable.
			echo FormFields::render( 'registration' );
		}
	}

	/**
	 * Reset verification does not alter password or reset token semantics.
	 */
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
	 * @param WP_Error $errors   Existing native validation errors.
	 * @param string   $username Native username.
	 * @param mixed    $password Native password, deliberately ignored.
	 * @param mixed    $email    Native email, validated before admission.
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
	 * @param WP_Error $errors   Existing validation errors.
	 * @param string   $username Native username.
	 * @param string   $email    Validated native email.
	 */
	public function native_registration( WP_Error $errors, string $username, string $email ): WP_Error {
		return $this->registration( $errors, $username, $email, true );
	}

	/**
	 * Use only business fields, never password or reset tokens in a fingerprint.
	 *
	 * @param WP_Error $errors   Native errors.
	 * @param string   $username Native login.
	 * @param string   $email    Validated address.
	 * @param bool     $core     Core registration requires an additional CSRF nonce.
	 */
	private function registration( WP_Error $errors, string $username, string $email, bool $core ): WP_Error {
		if ( ! Business::enabled() || $errors->has_errors() ) {
			return $this->registration_errors( $errors, $core );
		}
		$post = self::post();
		if ( ! is_email( $email ) ) {
         // phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Preserve Woo's native validated-email error and existing translations.
			$errors->add( 'registration-error-invalid-email', __( 'Please provide a valid email address.', 'woocommerce' ) );
			return $this->registration_errors( $errors, $core );
		}
		if ( 'enforce' === Configuration::current()->mode && $core && ! wp_verify_nonce( self::text( $post, 'linker_native_registration_nonce' ), 'linker_native_registration' ) ) {
			$errors->add( 'linker_registration_verification', __( 'Please verify your registration and try again.', 'linker-commerce' ) );
			return $this->registration_errors( $errors, $core );
		}
		$payload = array(
			'email'    => strtolower( $email ),
			'username' => $username,
			'locale'   => OrderLocale::current(),
		);
		foreach ( array( 'billing_company', 'billing_first_name', 'billing_last_name', 'billing_country', VatProfile::VAT_META, CustomerRole::META, Website::META ) as $key ) {
			$payload[ $key ] = self::text( $post, $key );
		}
		// WordPress's native display_name column is varchar(250); Fields saves
		// the complete joined personal name there after creation, without trimming.
		if ( 'enforce' === Configuration::active_mode() && mb_strlen( trim( $payload['billing_first_name'] . ' ' . $payload['billing_last_name'] ), 'UTF-8' ) > 250 ) {
			$errors->add( 'billing_first_name', __( 'Please use no more than 250 characters for your first and last name together. Your account has not been created; your entries are still here.', 'linker-commerce' ) );
			return $this->registration_errors( $errors, $core );
		}
		$result = Operation::begin( 'registration', $post, $payload );
		if ( is_wp_error( $result ) ) {
			$errors->add( $result->get_error_code(), $result->get_error_message() );
		} elseif ( ! empty( $result['enforced'] ) ) {
			$locale = OrderLocale::current();
			$values = $payload;
			unset( $values['email'], $values['username'], $values['locale'] );
			global $wpdb;
			try {
				$transaction = new \Linker\Commerce\Mail\NativeTransaction();
			} catch ( \Throwable $error ) {
				$errors->add( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
				return $this->registration_errors( $errors, $core );
			}
			$this->registration = array(
				'permit'      => $result,
				'slot'        => '',
				'notices'     => array(),
				'email'       => $email,
				'username'    => $username,
				'values'      => $values,
				'locale'      => $locale,
				'core'        => $core,
				'id'          => 0,
				'started'     => false,
				'transaction' => $transaction,
			);
			$slot               = RegistrationSlots::reserve( $result['id'], RegistrationSlots::profile_bytes( $values, $email, $locale ), Identity::recipient( $email ) );
			if ( is_wp_error( $slot ) ) {
				$this->unfinished();
				$errors->add( $slot->get_error_code(), $slot->get_error_message() );
				return $this->registration_errors( $errors, $core );
			}
			$this->registration['slot'] = $slot['key'];
			if ( ! RegistrationSlots::hold( $slot['key'] ) ) {
				$this->unfinished();
				$errors->add( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
				return $this->registration_errors( $errors, $core );
			}
			try {
				$notices = RegistrationNotices::prepare( $values, $email, $username, $locale, $result['id'] );
			} catch ( \Throwable $error ) {
				$notices = new WP_Error( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
			}
			if ( is_wp_error( $notices ) ) {
				$this->unfinished();
				$errors->add( $notices->get_error_code(), $notices->get_error_message() );
				return $this->registration_errors( $errors, $core );
			}
			$this->registration['notices'] = $notices;
		} else {
			$this->registration = array( 'permit' => $result );
		}
		return $this->registration_errors( $errors, $core );
	}

	/**
	 * Native forms retain business fields, while intentionally clearing passwords.
	 * Core's optional registration form has no password field to re-enter.
	 *
	 * @param WP_Error $errors Native errors.
	 * @param bool     $core   Native core registration entry.
	 */
	private function registration_errors( WP_Error $errors, bool $core ): WP_Error {
		if ( ! $core && $errors->has_errors() ) {
			$errors->add( 'linker_registration_password', __( 'Please re-enter your password.', 'linker-commerce' ) );
		}
		return $errors;
	}

	/**
	 * Earliest native created hook precedes VIES and registration mail.
	 *
	 * @param  int $id Native user id.
	 * @throws \RuntimeException The account completion cannot be proved.
	 */
	public function created( int $id ): void {
		if ( null === $this->registration ) {
			return;
		}
		if ( empty( $this->registration['permit']['enforced'] ) ) {
			Operation::finish( $this->registration['permit'], $id );
			$this->registration = null;
			return;
		}
		if ( $id !== $this->registration['id'] ) {
			return;
		}
		$active = $this->registration;
		try {
			$profile    = RegistrationSlots::native_profile( $id );
			$profile_ok = ! is_wp_error( $profile ) && $profile['bytes'] <= RegistrationSlots::profile_bytes( $active['values'], $active['email'], $active['locale'] );
			wp_cache_delete( $id, 'user_meta' );
			foreach ( RegistrationSlots::profile_fields( $active['values'], $active['email'], $active['locale'] ) as $key => $value ) {
				if ( get_user_meta( $id, $key, true ) !== $value ) {
					$profile_ok = false;
					break;
				}
			}
			if ( ! $profile_ok || get_user_meta( $id, RegistrationNotices::PENDING, true ) !== 'yes' || get_user_meta( $id, RegistrationSlots::META, true ) !== $active['slot'] || RegistrationNotices::read( $id ) !== $active['notices'] || is_wp_error( RegistrationSlots::bind( $active['slot'], $id ) ) ) {
				$this->unfinished();
				throw new \RuntimeException( esc_html__( 'The registration status could not be confirmed. Please try signing in before registering again, or email sales@de-linker.com. You can send inquiries without an account.', 'linker-commerce' ) );
			}
			Operation::finish( $active['permit'], $id );
			$active['transaction']->commit();
			RegistrationSlots::release( $active['slot'] );
			$this->registration = null;
		} catch ( \Throwable $error ) {
			$this->unfinished();
			throw new \RuntimeException( esc_html__( 'The registration status could not be confirmed. Please try signing in before registering again, or email sales@de-linker.com. You can send inquiries without an account.', 'linker-commerce' ) );
		}
	}

	/**
	 * Begin immediately before the actual native user row write, after validation.
	 *
	 * @param  array<string,mixed> $data     Native sanitized user columns.
	 * @param  bool                $update   Native update flag.
	 * @param  int|null            $id       Existing native ID.
	 * @param  array<string,mixed> $userdata Native caller; passwords are never copied.
	 * @return array<string,mixed> Unchanged native user columns.
	 */
	public function before_create( array $data, bool $update, ?int $id, array $userdata ): array {
		unset( $id, $userdata );
		if ( null === $this->registration || $update || ! $this->matches( $data ) || ! empty( $this->registration['started'] ) ) {
			return $data;
		}
		$data['display_name']          = trim( $this->registration['values']['billing_first_name'] . ' ' . $this->registration['values']['billing_last_name'] );
		$this->registration['started'] = true;
		return $data;
	}

	/**
	 * The earliest native metadata insertion binds only this expected new account.
	 *
	 * @param  array<string,mixed> $meta     Native custom metadata.
	 * @param  WP_User             $user     Actual new user.
	 * @param  bool                $update   Native update flag.
	 * @param  array<string,mixed> $userdata Native caller; no password retained.
	 * @return array<string,mixed> Native fields plus trusted association and notices.
	 */
	public function stamp( array $meta, WP_User $user, bool $update, array $userdata ): array {
		unset( $userdata );
		if ( $update || ! $this->matches(
			array(
				'user_email' => $user->user_email,
				'user_login' => $user->user_login,
			)
		) || empty( $this->registration['started'] ) || 0 !== $this->registration['id']
		) {
			return $meta;
		}
		$this->registration['id']                  = $user->ID;
		$values                                    = $this->registration['values'];
		$meta[ RegistrationSlots::META ]           = $this->registration['slot'];
		$meta['_linker_public_registration_entry'] = $this->registration['core'] ? 'core' : 'woo';
		$meta[ RegistrationNotices::META ]         = wp_slash( $this->registration['notices'] );
		$meta[ RegistrationNotices::PENDING ]      = 'yes';
		$meta[ RegistrationNotices::OWNER ]        = Identity::recipient( $user->user_email );
		foreach ( RegistrationSlots::profile_fields( $values, $user->user_email, $this->registration['locale'] ) as $key => $value ) {
			$meta[ $key ] = wp_slash( $value );
		}
		$meta[ \Linker\Commerce\Registration\Approval::STATUS_META ] = \Linker\Commerce\Registration\Approval::PENDING;
		return $meta;
	}

	/**
	 * Exact native email/login binding prevents unrelated nested created hooks.
	 *
	 * @param array<string,mixed> $data Native sanitized columns.
	 */
	private function matches( array $data ): bool {
		return null !== $this->registration && ! empty( $this->registration['permit']['enforced'] ) && strtolower( (string) ( $data['user_email'] ?? '' ) ) === strtolower( $this->registration['email'] ) && ( '' === $this->registration['username'] || ( $data['user_login'] ?? '' ) === $this->registration['username'] );
	}

	/**
	 * Core public door uses the same two prepared project notices.
	 *
	 * @param int $id Native user.
	 */
	public function core_notices( int $id ): void {
		if ( RegistrationNotices::owns( $id ) && 'core' === get_user_meta( $id, '_linker_public_registration_entry', true ) ) {
			RegistrationNotices::deliver( $id, 'team' );
			RegistrationNotices::deliver( $id, 'received' );
		}
	}

	/**
	 * The optional core door uses the two bounded pending-account notices too.
	 * Existing/admin-created users retain WordPress's native notification behavior.
	 *
	 * @param bool    $send Native notification policy.
	 * @param WP_User $user Native account.
	 */
	public function core_notification( bool $send, WP_User $user ): bool {
		return RegistrationNotices::owns( $user->ID ) && 'core' === get_user_meta( $user->ID, '_linker_public_registration_entry', true ) ? false : $send;
	}

	/**
	 * Known failed native inserts roll back; unknown crashes never time-refund.
	 */
	public function unfinished(): void {
		if ( null === $this->registration || empty( $this->registration['permit']['enforced'] ) ) {
			return;
		}
		$active             = $this->registration;
		$this->registration = null;
		try {
			$active['transaction']->rollback();
			if ( '' !== $active['slot'] ) {
				RegistrationSlots::release( $active['slot'] ); }
		} catch ( \Throwable $error ) {
			// Unknown original connection/commit: never replay or compensate on a new one.
			return;
		} finally {
			foreach ( array( RegistrationSlots::OPTION, IntakeStore::OPTION, 'alloptions', 'notoptions' ) as $key ) {
				wp_cache_delete( $key, 'options' ); }
			if ( $active['id'] > 0 ) {
				clean_user_cache( $active['id'] );
				wp_cache_delete( $active['id'], 'user_meta' ); }
		}
	}

	/**
	 * Core calls this before generating a reset key or dispatching reset mail.
	 *
	 * @param WP_Error      $errors Native errors.
	 * @param WP_User|false $user   Resolved native user, never exposed in public output.
	 */
	public function password_reset( WP_Error $errors, WP_User|false $user ): void {
		if ( ! Business::enabled() || $errors->has_errors() || ! $user instanceof WP_User ) {
			return;
		}
		$post = self::post();
		if ( 'enforce' === Configuration::current()->mode && ! wp_verify_nonce( self::text( $post, 'linker_password_reset_nonce' ), 'linker_password_reset' ) ) {
			$errors->add( 'linker_reset_verification', __( 'Please verify your request and try again.', 'linker-commerce' ) );
			return;
		}
		$result = Operation::begin( 'password_reset', $post, array( 'email' => strtolower( $user->user_email ) ) );
		if ( is_wp_error( $result ) ) {
			$errors->add( $result->get_error_code(), $result->get_error_message() );
		} else {
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
	 * One complete allowlisted field, matching the native registration's value.
	 * Native Fields saves the full sanitized string; fingerprints must do so too.
	 *
	 * @param array<string,mixed> $post Native transport.
	 * @param string              $key  Field name.
	 */
	private static function text( array $post, string $key ): string {
		return isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? sanitize_text_field( $post[ $key ] ) : '';
	}
}
