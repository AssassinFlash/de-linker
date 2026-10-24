<?php
/**
 * Pending public account/profile growth shares the registration byte envelope.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Protection\RegistrationSlots;
use Linker\Commerce\Mail\ConnectionFence;
use WC_Customer;
use WP_Error;
use WP_REST_Request;

/**
 * Native form/REST errors retain input; WordPress/Woo remain the only writers.
 */
final class PendingProfileCapacity {

	/**
	 * Native connection/savepoint, no credentials.
	 *
	 * @var array<string,mixed>|null
	 */
	private ?array $active = null;

	/** This request's refused public account values only.
	 *
	 * @var array<string,string>
	 */
	private static array $account_input = array();

	/** Native authenticated owner of those request-local values.
	 *
	 * @var int
	 */
	private static int $account_owner = 0;

	/**
	 * Retain a refused native account value without persisting credentials.
	 *
	 * @param string $key Native account form field.
	 * @param string $fallback Confirmed native value on ordinary page loads.
	 */
	public static function account_value( string $key, string $fallback ): string {
		return get_current_user_id() === self::$account_owner ? ( self::$account_input[ $key ] ?? $fallback ) : $fallback;
	}

	/**
	 * Only a native authenticated, nonce-verified account form may retain its values.
	 *
	 * @param int                  $id Native self-profile owner.
	 * @param array<string,string> $input Canonical native non-secret fields.
	 */
	private static function remember_account( int $id, array $input ): void {
		// phpcs:ignore WordPress.Security.NonceVerification -- Read only the original native nonce/action; no raw field values are copied.
		$nonce  = isset( $_REQUEST['save-account-details-nonce'] ) && is_string( $_REQUEST['save-account-details-nonce'] ) ? sanitize_text_field( wp_unslash( $_REQUEST['save-account-details-nonce'] ) ) : ( isset( $_REQUEST['_wpnonce'] ) && is_string( $_REQUEST['_wpnonce'] ) ? sanitize_text_field( wp_unslash( $_REQUEST['_wpnonce'] ) ) : '' );
		$action = isset( $_POST['action'] ) && is_string( $_POST['action'] ) ? sanitize_text_field( wp_unslash( $_POST['action'] ) ) : '';
		// phpcs:ignore WordPress.Security.NonceVerification -- Woo has validated this same native request before its errors hook.
		if ( 0 < $id && get_current_user_id() === $id && 'save_account_details' === $action && wp_verify_nonce( $nonce, 'save_account_details' ) ) {
			self::$account_input = $input;
			self::$account_owner = $id;
		}
	}

	/**
	 * Guard only existing pending business data; no password-only rewrite.
	 */
	public function register(): void {
		add_action( 'woocommerce_save_account_details_errors', array( $this, 'account_errors' ), PHP_INT_MAX, 2 );
		add_action( 'woocommerce_after_save_address_validation', array( $this, 'address_errors' ), PHP_INT_MAX, 4 );
		add_action( 'woocommerce_before_customer_object_save', array( $this, 'before_customer' ), PHP_INT_MAX );
		add_action( 'woocommerce_after_customer_object_save', array( $this, 'after_customer' ), PHP_INT_MAX );
		add_action( 'personal_options_update', array( $this, 'before_profile' ), 0 );
		add_action( 'user_profile_update_errors', array( $this, 'profile_errors' ), PHP_INT_MAX, 3 );
		add_filter( 'rest_dispatch_request', array( $this, 'rest_user' ), 30, 4 );
		add_filter( 'rest_request_after_callbacks', array( $this, 'rest_finished' ), PHP_INT_MAX );
		add_action( 'profile_update', array( $this, 'after_profile' ), PHP_INT_MAX );
		register_shutdown_function( array( $this, 'unfinished' ) );
	}

	/**
	 * Woo's address save has no catch around customer->save; use its native notice boundary.
	 *
	 * @param int                 $id Native authenticated account.
	 * @param string              $type Native billing/shipping type.
	 * @param array<string,mixed> $fields Native address field schema.
	 * @param WC_Customer         $customer Native validated customer.
	 */
	public function address_errors( int $id, string $type, array $fields, WC_Customer $customer ): void {
		unset( $id, $type, $fields );
		if ( 0 < wc_notice_count( 'error' ) ) {
			return; }
		try {
			$this->before_customer( $customer );
			if ( null !== $this->active && 'woo' === $this->active['source'] ) {
				$this->active['source'] = 'billing'; }
		} catch ( \WC_Data_Exception $error ) {
			wc_add_notice( $error->getMessage(), 'error' );
		} catch ( \Throwable $error ) {
			$this->unfinished();
			wc_add_notice( self::message( true ), 'error' );
		}
	}

	/**
	 * Woo writes wp_update_user before its customer object; reserve across both native writers.
	 *
	 * @param WP_Error $errors Native validated form errors.
	 * @param object   $user Canonical native public fields; credentials are never copied.
	 */
	public function account_errors( WP_Error $errors, object $user ): void {
		self::$account_input = array();
		self::$account_owner = 0;
		$id                  = (int) ( $user->ID ?? 0 );
		$input               = array(
			'account_first_name'   => (string) ( $user->first_name ?? '' ),
			'account_last_name'    => (string) ( $user->last_name ?? '' ),
			'account_display_name' => (string) ( $user->display_name ?? '' ),
			'account_email'        => (string) ( $user->user_email ?? '' ),
		);
		try {
			if ( null !== $this->active || $errors->has_errors() || 0 < wc_notice_count( 'error' ) || ! $this->eligible( $id ) ) {
				return; }
			[ $columns, $meta ] = self::prepared( $user );

			$before = RegistrationSlots::native_profile( $id );
			if ( is_wp_error( $before ) ) {
				self::remember_account( $id, $input );
				$errors->add( 'linker_registration_profile_capacity', self::message() );
				return; }
			$changed = false;
			foreach ( $columns as $key => $value ) {
				$changed = $changed || ( $before['columns'][ $key ] ?? '' ) !== $value; }
			foreach ( $meta as $key => $value ) {
				$changed = $changed || ( $before['meta'][ $key ] ?? '' ) !== $value; }
			if ( ! $changed ) {
				return; } // Password-only saves retain their existing native path.
			foreach ( array( 'first_name', 'last_name' ) as $key ) {
				if ( isset( $meta[ $key ] ) && ( $before['meta'][ $key ] ?? '' ) !== $meta[ $key ] ) {
					$meta[ 'billing_' . $key ] = $meta[ $key ]; }
			}
			if ( isset( $columns['user_email'] ) && $before['columns']['user_email'] !== $columns['user_email'] ) {
				$meta['billing_email'] = $columns['user_email']; }
			$context = RegistrationSlots::begin_change( $id, $columns, $meta );
			if ( is_wp_error( $context ) ) {
				self::remember_account( $id, $input );
				$errors->add( 'linker_registration_profile_capacity', self::message() );
				return; }
			$this->active = $context + array(
				'source'          => 'account',
				'armed'           => true,
				'profile_written' => false,
				'account_input'   => $input,
			);
		} catch ( \Throwable $error ) {
			$this->unfinished();
			self::remember_account( $id, $input );
			$errors->add( 'linker_registration_profile_capacity', self::message( true ) );
		}
	}

	/**
	 * Capture only changed native public fields, after native normalization hooks.
	 *
	 * @param  WC_Customer $customer Native customer being saved.
	 * @throws \WC_Data_Exception A refused change must stop the native save.
	 */
	public function before_customer( WC_Customer $customer ): void {
		$id = $customer->get_id();
		if ( null !== $this->active || ! $this->eligible( $id ) ) {
			return;
		}
		$changes = $customer->get_changes();
		$columns = array();
		$meta    = array();
		foreach ( array(
			'email'        => 'user_email',
			'display_name' => 'display_name',
		) as $property => $column ) {
			if ( isset( $changes[ $property ] ) ) {
				$columns[ $column ] = (string) $changes[ $property ];
			}
		}
		foreach ( array( 'first_name', 'last_name' ) as $property ) {
			if ( isset( $changes[ $property ] ) ) {
				$meta[ $property ] = (string) $changes[ $property ];
			}
		}
		foreach ( $changes['billing'] ?? array() as $key => $value ) {
			$meta[ 'billing_' . $key ] = (string) $value;
		}
		foreach ( $customer->get_meta_data() as $datum ) {
			if ( array() !== $datum->get_changes() && self::business_key( $datum->key ) && is_scalar( $datum->value ) ) {
				$meta[ $datum->key ] = (string) $datum->value;
			}
		}
		if ( array() === $columns && array() === $meta ) {
			return;
		}
		$context = RegistrationSlots::begin_change( $id, $columns, $meta );
		if ( is_wp_error( $context ) ) {
			throw new \WC_Data_Exception( 'linker_registration_profile_capacity', esc_html( self::message() ) );
		}
		$this->active = $context + array(
			'source' => 'woo',
			'armed'  => true,
		);
	}

	/**
	 * The actual writer, not a projected value, decides the final native bytes.
	 *
	 * @param  WC_Customer $customer Saved native customer.
	 * @throws \WC_Data_Exception Native changes were rolled back on a failed bound.
	 */
	public function after_customer( WC_Customer $customer ): void {
		if ( null !== $this->active && in_array( $this->active['source'], array( 'woo', 'billing', 'account' ), true ) && $customer->get_id() === $this->active['id'] ) {
			$context      = $this->active;
			$this->active = null;
			$confirmed    = 'account' !== $context['source'] || ! empty( $context['profile_written'] );
			$result       = RegistrationSlots::end_change( $context, $confirmed );
			if ( true !== $result ) {
				if ( 'account' === $context['source'] ) {
					self::remember_account( $context['id'], $context['account_input'] );
				}
				if ( 'billing' === $context['source'] ) {
					wc_add_notice( self::message( is_wp_error( $result ) ), 'error' );
					return; }
				throw new \WC_Data_Exception( 'linker_registration_profile_capacity', esc_html( self::message( is_wp_error( $result ) ) ) );
			}
		}
	}

	/**
	 * Core validated the nonce/capability before native profile extension writers.
	 * Hold their writes until the normal WP_Error boundary can validate the whole form.
	 *
	 * @param int $id Native self-profile target.
	 */
	public function before_profile( int $id ): void {
		if ( null !== $this->active || ! $this->eligible( $id ) ) {
			return;
		}
		$context = RegistrationSlots::begin_change( $id, array(), array(), true );
		if ( is_wp_error( $context ) ) {
			wp_die(
				esc_html( self::message( true ) ),
				'',
				array(
					'response'  => 503,
					'back_link' => true,
				)
			);
		}
		$this->active = $context + array(
			'source' => 'core',
			'armed'  => false,
		);
	}

	/**
	 * Core's canonical public columns/names are already prepared here.
	 *
	 * @param WP_Error $errors Native errors.
	 * @param bool     $update Native update flag.
	 * @param object   $user   Native prepared user, deliberately never copied wholesale.
	 */
	public function profile_errors( WP_Error $errors, bool $update, object $user ): void {
		$id = (int) ( $user->ID ?? 0 );
		if ( ! $update || ! $this->eligible( $id ) ) {
			return;
		}
		if ( null === $this->active ) {
			$this->before_profile( $id );
		}
		if ( $errors->has_errors() || null === $this->active ) {
			$this->unfinished();
			return;
		}
		[ $columns, $meta ] = self::prepared( $user );
		if ( ! empty( $this->active['rejected'] ) || ! RegistrationSlots::check_change( $this->active, $columns, $meta ) ) {
			$this->unfinished();
			$errors->add( 'linker_registration_profile_capacity', esc_html( self::message() ) );
			return;
		}
		$this->active['armed'] = true;
	}

	/**
	 * Native dispatch runs after schema validation and the native permission callback.
	 *
	 * @param  mixed               $response Earlier dispatch result.
	 * @param  WP_REST_Request     $request  Native authenticated request.
	 * @param  string              $route    Native matched route.
	 * @param  array<string,mixed> $handler  Native callback descriptor.
	 * @return mixed Native continuation or normal WP_Error before the writer.
	 */
	public function rest_user( mixed $response, WP_REST_Request $request, string $route, array $handler ): mixed {
		unset( $route );
		$callback = $handler['callback'] ?? null;
		if ( null !== $response || ! is_array( $callback ) || ! ( $callback[0] ?? null ) instanceof \WP_REST_Users_Controller || ! is_string( $callback[1] ?? null ) || ! in_array( strtolower( $callback[1] ), array( 'update_item', 'update_current_item' ), true ) || ! in_array( $request->get_method(), array( 'POST', 'PUT', 'PATCH' ), true ) ) {
			return $response;
		}
		// The native current-user callback overwrites id; update_item reads the
		// parsed request parameter (JSON/body can take precedence over URL params).
		$id = 'update_current_item' === strtolower( $callback[1] ) ? get_current_user_id() : (int) $request->get_param( 'id' );
		if ( ! $this->eligible( $id ) || null !== $this->active ) {
			return $response;
		}
		$user = new \stdClass();
		foreach ( array(
			'name'       => 'display_name',
			'email'      => 'user_email',
			'url'        => 'user_url',
			'slug'       => 'user_nicename',
			'first_name' => 'first_name',
			'last_name'  => 'last_name',
			'locale'     => 'locale',
		) as $argument => $field ) {
			$value = $request->get_param( $argument );
			if ( is_string( $value ) ) {
				$user->$field = $value;
			}
		}
		[ $columns, $meta ] = self::prepared( $user );
		if ( array() === $columns && array() === $meta ) {
			return $response;
		}
		$context = RegistrationSlots::begin_change( $id, $columns, $meta );
		if ( is_wp_error( $context ) ) {
			return new WP_Error( 'linker_registration_profile_capacity', esc_html( self::message() ), array( 'status' => 503 ) );
		}
		$this->active = $context + array(
			'source' => 'rest',
			'armed'  => true,
		);
		return $response;
	}

	/**
	 * A controller validation error must release only our unfinished read/write scope.
	 *
	 * @param  mixed $response Actual native result.
	 * @return mixed Unchanged native response.
	 */
	public function rest_finished( mixed $response ): mixed {
		if ( null !== $this->active && 'rest' === $this->active['source'] ) {
			$this->unfinished();
		}
		return $response;
	}

	/**
	 * Core has written the public columns and metadata; passwords never enter scope data.
	 *
	 * @param  int $id Native saved account.
	 * @throws \RuntimeException An unexpected post-filter expansion is not saved.
	 */
	public function after_profile( int $id ): void {
		if ( null !== $this->active && 'account' === $this->active['source'] && $id === $this->active['id'] ) {
			$this->active['profile_written'] = true;
			return; }
		if ( null !== $this->active && in_array( $this->active['source'], array( 'core', 'rest' ), true ) && ! empty( $this->active['armed'] ) && $id === $this->active['id'] ) {
			$context      = $this->active;
			$this->active = null;
			$result       = RegistrationSlots::end_change( $context, true );
			if ( true !== $result ) {
				throw new \RuntimeException( esc_html( self::message( is_wp_error( $result ) ) ) );
			}
		}
	}

	/**
	 * An interrupted native writer releases only its own uncommitted changes.
	 */
	public function unfinished(): void {
		if ( null !== $this->active ) {
			RegistrationSlots::end_change( $this->active, false );
			$this->active = null;
		}
	}

	/**
	 * Staff maintenance and explicitly decided accounts keep their existing behavior.
	 *
	 * @param int $id Native user.
	 */
	private function eligible( int $id ): bool {
		return ConnectionFence::run( fn (): bool => $this->eligible_owned( $id ) );
	}

	/** Only short native eligibility reads, before a profile scope is created.
	 *
	 * @param int $id Native target account.
	 */
	private function eligible_owned( int $id ): bool {
		if ( 'enforce' !== \Linker\Commerce\Protection\Configuration::active_mode() || $id < 1 || current_user_can( 'edit_users' ) || ( get_current_user_id() > 0 && get_current_user_id() !== $id ) ) {
			return false;
		}
		$user = get_userdata( $id );
		if ( ! $user instanceof \WP_User || ( ! in_array( 'customer', $user->roles, true ) && '' === get_user_meta( $id, RegistrationSlots::META, true ) ) ) {
			return false;
		}
		$status = get_user_meta( $id, Approval::STATUS_META, true );
		return ! ( in_array( $status, array( Approval::APPROVED, Approval::REJECTED ), true ) && (int) get_user_meta( $id, Approval::CHANGED_BY_META, true ) > 0 && (int) get_user_meta( $id, Approval::CHANGED_AT_META, true ) > 0 );
	}

	/**
	 * Allowlisted public profile only, never password/reset/application credentials.
	 *
	 * @param  object $user Native prepared user.
	 * @return array{array<string,string>,array<string,string>} Native changed values.
	 */
	private static function prepared( object $user ): array {
		$columns = array();
		$meta    = array();
		foreach ( array( 'user_login', 'user_nicename', 'user_email', 'user_url', 'display_name' ) as $key ) {
			if ( isset( $user->$key ) && is_string( $user->$key ) ) {
				$columns[ $key ] = $user->$key;
			}
		}
		foreach ( array( 'first_name', 'last_name', 'locale' ) as $key ) {
			if ( isset( $user->$key ) && is_string( $user->$key ) ) {
				$meta[ $key ] = $user->$key;
			}
		}
		return array( $columns, $meta );
	}

	/**
	 * The same native logical business fields as the authoritative byte query.
	 *
	 * @param string $key Native metadata key.
	 */
	private static function business_key( string $key ): bool {
		return str_starts_with( $key, 'billing_' ) || in_array( $key, array( CustomerRole::META, Website::META, 'first_name', 'last_name', 'locale' ), true );
	}

	/**
	 * Preserve input without claiming that an unknown write was successful.
	 *
	 * @param bool $unknown Native transaction outcome cannot be confirmed.
	 */
	private static function message( bool $unknown = false ): string {
		$message = $unknown ? __( 'The status of your changes could not be confirmed. Please check your account before saving again, or email sales@de-linker.com.', 'linker-commerce' ) : __( 'Your changes could not be saved. Your entries are still here. Please try again later or email sales@de-linker.com.', 'linker-commerce' );
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Native form/REST already verified access; only presence selects a password-clearing hint, no secret value is retained.
		if ( ! empty( $_POST['password_1'] ) || ! empty( $_POST['password_2'] ) || ! empty( $_POST['pass1'] ) || ! empty( $_POST['pass2'] ) ) {
			$message .= ' ' . __( 'Please re-enter your passwords.', 'linker-commerce' );
		}
		return $message;
	}
}
