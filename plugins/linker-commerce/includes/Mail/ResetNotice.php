<?php
/**
 * Reserve native password-reset notification space before a key is changed.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use WP_Error;
use WP_User;

/** Core and Woo retain their key generation, templates and delivery callbacks. */
final class ResetNotice {
	/** Native key writers, retained only until their exact original job is accepted.
	 *
	 * @var array<int,NativeTransaction>
	 */
	private static array $writers = array();
	/** Definite failed reset producers in this request, never reset keys or message bodies.
	 *
	 * @var array<int,true>
	 */
	private static array $failed = array();
	/** Current browser input for a same-request native form re-render.
	 *
	 * @var string
	 */
	private static string $retry_login = '';
	/** Whether the native Woo form is being decorated with its retained input.
	 *
	 * @var bool
	 */
	private static bool $rendering = false;

	/** Current server-native reset operations.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private static array $scopes = array();
	/** Exact core reset message to opaque reservation.
	 *
	 * @var array<string,string>
	 */
	private static array $core = array();

	/**
	 * Native key generation has finished; its database mutation has not started.
	 *
	 * @param string $login Actual native resolved login.
	 * @param string $key Native generated secret, deliberately ignored.
	 */
	public static function begin( string $login, #[\SensitiveParameter] string $key ): void {
		unset( $key );
		$user = get_user_by( 'login', $login );
		if ( ! $user instanceof WP_User || ! isset( self::$scopes[ $user->ID ] ) ) {
			return;
		}
		self::$writers[ $user->ID ] = new NativeTransaction();
		register_shutdown_function(
			static function (): void {
				foreach ( array_reverse( self::$writers, true ) as $id => $writer ) {
					self::finish( (string) ( self::$scopes[ $id ]['key'] ?? '' ), false );
				}
			}
		);
	}

	/**
	 * Only an exact server reservation can acknowledge key plus original job.
	 *
	 * @param string $scope Opaque server reset reservation.
	 * @param bool   $accepted Original durable job and AS were accepted.
	 */
	public static function finish( string $scope, bool $accepted ): bool {
		if ( '' === $scope ) {
			return $accepted;
		}
		foreach ( self::$writers as $id => $writer ) {
			if ( ( self::$scopes[ $id ]['key'] ?? '' ) !== $scope ) {
				continue;
			}
			unset( self::$writers[ $id ] );
			try {
				if ( $accepted ) {
					$writer->commit();
					unset( self::$failed[ $id ] );
					return true;
				}
				$writer->rollback();
				// Only a proven live rollback with no job cancels unused mail space.
				Capacity::cancel_before_side_effect( $scope );
			} catch ( \Throwable $error ) {
				try {
					$writer->rollback();
				} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- Unknown native commit is never compensated or refunded on a new connection.
				}
			}
			self::$failed[ $id ] = true;
			unset( self::$scopes[ $id ] );
			clean_user_cache( $id );
			return false;
		}
		return $accepted;
	}

	/**
	 * Woo's reset action otherwise unconditionally reports success after a false mail result.
	 *
	 * @param bool      $sent Native mail handoff result.
	 * @param string    $id Native email ID.
	 * @param \WC_Email $email Actual native producer.
	 */
	public static function woocommerce_result( bool $sent, string $id, \WC_Email $email ): void {
		unset( $id );
		if ( $sent || Prepared::is_preview() || ! $email instanceof \WC_Email_Customer_Reset_Password || ! isset( self::$failed[ (int) $email->user_id ] ) ) {
			return;
		}
		self::remember( '' !== self::$retry_login ? self::$retry_login : (string) $email->user_login );
		wc_add_notice( __( 'Password reset is temporarily unavailable. Please try again later or email sales@de-linker.com.', 'linker-commerce' ), 'error' );
		wp_safe_redirect( wc_lostpassword_url(), 303 );
		exit;
	}

	/**
	 * Preserve only the existing editable username/email field, never keys/passwords.
	 *
	 * @param string $login Original native form input.
	 */
	public static function remember( string $login ): void {
		self::$retry_login = sanitize_text_field( $login );
		\Linker\Commerce\Protection\FormRecovery::save( 'password_reset', array( 'user_login' => self::$retry_login ) );
	}

	/** Native Woo's existing form markup has no value argument for this one input. */
	public static function render_begin(): void {
		$fields = \Linker\Commerce\Protection\FormRecovery::consume( 'password_reset' );
		$login  = '' !== self::$retry_login ? self::$retry_login : ( $fields['user_login'] ?? '' );
		if ( '' === $login ) {
			return;
		}
		self::$retry_login = $login;
		self::$rendering   = true;
		ob_start();
	}

	/** Add only native input value; the existing template owns every visual/layout choice. */
	public static function render_end(): void {
		if ( ! self::$rendering ) {
			return;
		}
		self::$rendering = false;
		$html            = (string) ob_get_clean();
		$processor       = new \WP_HTML_Tag_Processor( $html );
		while ( $processor->next_tag( array( 'tag_name' => 'INPUT' ) ) ) {
			if ( 'user_login' === $processor->get_attribute( 'name' ) ) {
				$processor->set_attribute( 'value', self::$retry_login );
				break;
			}
		}
		self::$retry_login = '';
		echo $processor->get_updated_html(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Existing native Woo template; WordPress's HTML processor escapes the single restored attribute.
	}

	/**
	 * Preview the configured templates with a native-length alphanumeric key.
	 * Core get_password_reset_key() generates 20 non-special characters: replacing
	 * those characters preserves all URL/JSON lengths in the native templates.
	 *
	 * @param WP_User $user Native resolved account.
	 * @param string  $operation Dispatched server operation, never browser input.
	 * @return array<string,mixed>|WP_Error
	 */
	public static function reserve( WP_User $user, string $operation ): array|WP_Error {
		$key      = str_repeat( 'A', 20 );
		$messages = array( self::core_message( $user, $key ) );
		foreach ( WC()->mailer()->get_emails() as $email ) {
			if ( $email instanceof \WC_Email_Customer_Reset_Password ) {
				$messages[] = Prepared::capture( static fn () => $email->trigger( $user->user_login, $key ) );
			}
		}
		$bytes = 0;
		foreach ( $messages as $message ) {
			if ( $message instanceof Message ) {
				$encoded = wp_json_encode( $message->to_array() );
				$bytes   = max( $bytes, is_string( $encoded ) ? strlen( $encoded ) : 0 );
			}
		}
		$result = Capacity::reserve_critical( 'reset:' . $operation, 1, $bytes );
		if ( is_array( $result ) ) {
			self::$scopes[ $user->ID ] = $result;
		}
		return $result;
	}

	/**
	 * Only the actual native Woo reset instance obtains this account's scope.
	 *
	 * @param int $user Native email's resolved user ID.
	 * @return array<string,mixed>|null
	 */
	public static function scope( int $user ): ?array {
		return self::$scopes[ $user ] ?? null;
	}

	/**
	 * Native policy explicitly skipped this mail before any Outbox dispatch.
	 *
	 * @param string    $id Native email ID.
	 * @param \WC_Email $email Actual native producer instance.
	 */
	public static function disabled( string $id, \WC_Email $email ): void {
		unset( $id );
		if ( $email instanceof \WC_Email_Customer_Reset_Password ) {
			self::cancel( (int) $email->user_id );
		}
	}

	/**
	 * Core's explicit disabled-mail decision is made before generating a key.
	 *
	 * @param bool    $send Existing native decision.
	 * @param string  $login Native account login.
	 * @param WP_User $user Native resolved account.
	 */
	public static function allowed( bool $send, string $login, WP_User $user ): bool {
		unset( $login );
		if ( ! $send ) {
			self::cancel( $user->ID );
		}
		return $send;
	}

	/**
	 * A definite no-send skips only an unused native mail operation.
	 *
	 * @param int $user Native account.
	 */
	private static function cancel( int $user ): void {
		if ( isset( self::$writers[ $user ] ) ) {
			self::finish( (string) self::$scopes[ $user ]['key'], false );
			return;
		}
		if ( isset( self::$scopes[ $user ] ) && Capacity::cancel_before_side_effect( self::$scopes[ $user ] ) ) {
			unset( self::$scopes[ $user ] );
		}
	}

	/**
	 * Bind the actual core reset's final arguments, after its native key was saved.
	 *
	 * @param array<string,mixed> $email Native final mail arguments.
	 * @param WP_User             $user Resolved native account.
	 */
	public static function bind( array $email, WP_User $user ): void {
		$scope = self::scope( $user->ID );
		if ( null !== $scope ) {
			self::$core[ self::signature( $email ) ] = (string) $scope['key'];
		}
	}

	/**
	 * Consume one in-process, exact native core producer binding.
	 *
	 * @param array<string,mixed> $atts Actual wp_mail arguments.
	 */
	public static function take( array $atts ): string {
		$key   = self::signature( $atts );
		$scope = self::$core[ $key ] ?? '';
		unset( self::$core[ $key ] );
		return $scope;
	}

	/**
	 * Core's native reset template, with identical locale and public filters.
	 * WordPress exposes no read-only renderer before get_password_reset_key().
	 * This mirrors wp-includes/user.php::retrieve_password, without generating,
	 * storing or delivering a key; native fixtures compare final encoded sizes.
	 *
	 * @param WP_User $user Native account.
	 * @param string  $key Fixed native-shape preview key.
	 */
	private static function core_message( WP_User $user, string $key ): Message {
		$switched = switch_to_user_locale( $user->ID );
		try {
			$site = wp_specialchars_decode( (string) get_option( 'blogname' ), ENT_QUOTES );
			// phpcs:disable WordPress.WP.I18n.MissingArgDomain, WordPress.WP.I18n.TextDomainMismatch -- Preserve the core WordPress template and its installed translations exactly.
			$body = __( 'Someone has requested a password reset for the following account:' ) . "\r\n\r\n";
			/* translators: %s: Site name. */
			$body .= sprintf( __( 'Site Name: %s' ), $site ) . "\r\n\r\n";
			/* translators: %s: User login. */
			$body .= sprintf( __( 'Username: %s' ), $user->user_login ) . "\r\n\r\n";
			$body .= __( 'If this was a mistake, ignore this email and nothing will happen.' ) . "\r\n\r\n";
			$body .= __( 'To reset your password, visit the following address:' ) . "\r\n\r\n";
			$body .= network_site_url( 'wp-login.php?login=' . rawurlencode( $user->user_login ) . "&key=$key&action=rp", 'login' ) . '&wp_lang=' . get_user_locale( $user ) . "\r\n\r\n";
			$ip    = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? $_SERVER['REMOTE_ADDR'] : ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact native renderer, not authorization or a separately stored field.
			if ( ! is_user_logged_in() && '' !== $ip ) {
				/* translators: %s: IP address of password reset requester. */
				$body .= sprintf( __( 'This password reset request originated from the IP address %s.' ), $ip ) . "\r\n";
			}
			/* translators: %s: Site title. */
			$title = sprintf( __( '[%s] Password Reset' ), $site );
			// phpcs:enable
			// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- The exact native WordPress reset renderer's public filters.
			$title = apply_filters( 'retrieve_password_title', $title, $user->user_login, $user );
			$body  = apply_filters( 'retrieve_password_message', $body, $key, $user->user_login, $user );
			$atts  = apply_filters(
				'retrieve_password_notification_email',
				array(
					'to'      => $user->user_email,
					'subject' => $title,
					'message' => $body,
					'headers' => '',
				),
				$key,
				$user->user_login,
				$user
			);
			$atts  = apply_filters( 'wp_mail', $atts );
			// phpcs:enable
			return Producer::critical( static fn (): Message => Message::from_wp_mail( $atts ) );
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
		}
	}

	/**
	 * Exact arguments, not an email address alone, bind the native producer.
	 *
	 * @param array<string,mixed> $atts Native wp_mail arguments.
	 */
	private static function signature( array $atts ): string {
		return hash( 'sha256', (string) wp_json_encode( array( $atts['to'] ?? '', $atts['subject'] ?? '', $atts['message'] ?? '' ) ) );
	}
}
